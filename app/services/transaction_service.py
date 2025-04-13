from sqlalchemy.orm import Session
from datetime import datetime
from ..models.transaction import Transaction
from ..schemas.transaction import TransactionCreate
from typing import List, Optional, Dict
import uuid
import pandas as pd
import json
import re
from io import StringIO
from app.services.category_detector import detect_category_for_transaction

def create_transaction(db: Session, transaction_data: TransactionCreate, user_id: uuid.UUID) -> Transaction:
    """Create a new transaction record for a user"""
    db_transaction = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        transaction_id=transaction_data.transaction_id,
        date=transaction_data.date,
        time=transaction_data.time,
        description=transaction_data.description,
        dr=transaction_data.dr,
        cr=transaction_data.cr,
        source=transaction_data.source,
        balance=transaction_data.balance,
        raw_data=transaction_data.raw_data
    )
    
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_transactions(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Transaction]:
    """Get all transactions for a user with pagination"""
    return db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.date.desc(), Transaction.time.desc()).offset(skip).limit(limit).all()

def get_transaction_by_id(db: Session, transaction_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Transaction]:
    """Get a specific transaction by ID for a user"""
    return db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).first()

def create_transactions_batch(db: Session, transactions_data: List[Dict], user_id: uuid.UUID) -> List[Transaction]:
    """
    Create multiple transactions at once from processed file data
    """
    db_transactions = []
    
    for transaction_data in transactions_data:
        try:
            # Convert string date/time to appropriate objects if needed
            from datetime import datetime
            
            # Create transaction object
            db_transaction = Transaction(
                id=uuid.uuid4(),
                user_id=user_id,
                transaction_id=transaction_data.get("transaction_id"),
                transaction_date=transaction_data.get("transaction_date"),
                transaction_time=transaction_data.get("transaction_time"),
                description=transaction_data.get("description"),
                dr=float(transaction_data.get("dr", 0)),
                cr=float(transaction_data.get("cr", 0)),
                source=transaction_data.get("source", "file_upload"),
                balance=float(transaction_data.get("balance", 0)),
                raw_data=transaction_data.get("raw_data")
            )
            
            db_transactions.append(db_transaction)
            
        except Exception as e:
            print(f"Error creating transaction: {str(e)}")
            # Continue with other transactions
            continue
    
    # Bulk insert all transactions
    if db_transactions:
        db.add_all(db_transactions)
        db.commit()
        
    return db_transactions

async def csv_to_transactions(
    csv_data: str, 
    user_id: uuid.UUID, 
    source: str, 
    filename: str
) -> List[Transaction]:
    """
    Convert CSV data to Transaction objects, including category detection.
    """
    transactions = []
    
    # Find the actual header row (bank statements often have metadata before headers)
    csv_lines = csv_data.splitlines()
    header_row = -1
    
    # Look for common transaction table headers
    for idx, line in enumerate(csv_lines):
        line_lower = line.lower()
        if (('date' in line_lower and ('description' in line_lower or 'narration' in line_lower)) or
            ('txn' in line_lower) or  # Transaction
            ('transaction' in line_lower)):
            header_row = idx
            break
    
    if header_row == -1:
        print("Could not find transaction header row")
        return []
    
    # Extract column headers and transaction data
    headers = csv_lines[header_row].split(',')
    transaction_rows = csv_lines[header_row+1:]
    
    # Create a new CSV with just the header and transaction data
    transaction_csv = '\n'.join([csv_lines[header_row]] + transaction_rows)
    
    try:
        # Parse CSV data with pandas
        df = pd.read_csv(
            StringIO(transaction_csv), 
            sep=',',
            engine='python',  # More flexible parsing engine
            on_bad_lines='skip',  # Skip problematic lines
            dtype=str  # Read all data as strings initially to avoid numeric parsing issues
        )
        
        # Remove rows that are all NaN
        df = df.dropna(how='all')
        
        # Find the relevant columns for transaction data
        date_col = next((col for col in df.columns 
                        if any(term in col.lower() for term in ['date', 'txn date', 'transaction date', 'value date'])), None)
        
        desc_col = next((col for col in df.columns 
                        if any(term in col.lower() for term in ['description', 'narration', 'particulars', 'details'])), None)
        
        debit_col = next((col for col in df.columns 
                        if any(term in col.lower() for term in ['dr', 'debit', 'withdrawal', 'amount(-)', 'withdraw'])), None)
        
        credit_col = next((col for col in df.columns 
                          if any(term in col.lower() for term in ['cr', 'credit', 'deposit', 'amount(+)'])), None)
        
        balance_col = next((col for col in df.columns 
                           if any(term in col.lower() for term in ['balance', 'closing balance'])), None)
        
        ref_col = next((col for col in df.columns 
                       if any(term in col.lower() for term in ['reference', 'ref', 'transaction id'])), None)
        
        # Process each row
        for idx, row in df.iterrows():
            try:
                # Parse transaction date
                transaction_date = None
                if date_col:
                    date_str = str(row[date_col]).strip()
                    try:
                        # Try multiple date formats
                        for date_format in [None, '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y']:
                            try:
                                if date_format:
                                    transaction_date = datetime.strptime(date_str, date_format).date()
                                else:
                                    transaction_date = pd.to_datetime(date_str).date()
                                break
                            except:
                                continue
                    except:
                        # If date parsing fails, use today's date
                        transaction_date = datetime.now().date()
                
                if transaction_date is None:
                    transaction_date = datetime.now().date()
                
                # Extract description
                description = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else ""
                
                # Detect category for the transaction
                category = await detect_category_for_transaction(description)
                
                # Extract debit amount (dr)
                dr_amount = 0.0
                if debit_col and pd.notna(row[debit_col]):
                    dr_str = str(row[debit_col])
                    if dr_str and dr_str.strip() and dr_str.strip() not in ['-', 'nan', 'NaN']:
                        try:
                            # Remove commas and currency symbols
                            dr_clean = re.sub(r'[^\d.]', '', dr_str.replace(',', ''))
                            if dr_clean:
                                dr_amount = float(dr_clean)
                        except ValueError:
                            print(f"Could not convert debit value: {dr_str}")
                
                # Extract credit amount (cr)
                cr_amount = 0.0
                if credit_col and pd.notna(row[credit_col]):
                    cr_str = str(row[credit_col])
                    if cr_str and cr_str.strip() and cr_str.strip() != '-':
                        # Remove commas and currency symbols
                        cr_clean = re.sub(r'[^\d.]', '', cr_str.replace(',', ''))
                        if cr_clean:
                            cr_amount = float(cr_clean)
                
                # Extract balance
                balance = 0.0
                if balance_col and pd.notna(row[balance_col]):
                    bal_str = str(row[balance_col])
                    if bal_str and bal_str.strip():
                        # Remove commas and currency symbols
                        bal_clean = re.sub(r'[^\d.]', '', bal_str.replace(',', ''))
                        if bal_clean:
                            balance = float(bal_clean)
                
                # Get transaction reference/ID if available
                transaction_id = str(row[ref_col]) if ref_col and pd.notna(row[ref_col]) else None
                
                # Create Transaction object
                transaction = Transaction(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    transaction_id=transaction_id,
                    transaction_date=transaction_date,
                    transaction_time=datetime.now().time(),  # Default time if not available
                    description=description,
                    category=category,  # Add detected category
                    dr=dr_amount,
                    cr=cr_amount,
                    source=source or filename.split('.')[0],
                    balance=balance,
                    raw_data=json.dumps(row.to_dict())  # Store original row data
                )
                
                transactions.append(transaction)
                
            except Exception as e:
                print(f"Error processing row {idx}: {str(e)}")
                continue
        
        return transactions
        
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        return []

def is_valid_transaction(row, date_col, debit_col, credit_col, desc_col=None):
    """
    Determines if a row represents a valid transaction by checking:
    1. It has a proper date
    2. It has either a debit or credit amount (not both empty/zero)
    3. It's not a summary row, total, or metadata
    """
    # Skip rows that appear to be summaries, totals, or metadata
    if desc_col and pd.notna(row[desc_col]):
        desc_lower = str(row[desc_col]).lower()
        # Skip summary rows and metadata
        if any(term in desc_lower for term in [
            'total', 'subtotal', 'opening balance', 'closing balance', 
            'sum', 'average', 'balance b/f', 'balance c/f',
            'statement', 'summary', 'period end', 'period start'
        ]):
            return False
    
    # For any column, check if it contains summary indicators
    for col_name, value in row.items():
        if pd.notna(value):
            str_val = str(value).lower()
            if any(term in str_val for term in [
                'total', 'balance b/f', 'opening', 'closing', 
                'statement period', 'summary'
            ]):
                return False
    
    # Check if it has a valid date
    has_date = date_col is not None and pd.notna(row[date_col])
    
    # Check if it has either a debit or credit amount
    has_amount = False
    if debit_col and pd.notna(row[debit_col]) and str(row[debit_col]).strip() not in ['', '-', '0', '0.0']:
        has_amount = True
    elif credit_col and pd.notna(row[credit_col]) and str(row[credit_col]).strip() not in ['', '-', '0', '0.0']:
        has_amount = True
    
    # Special handling for particular sources
    if 'Reference Code' in row and str(row['Reference Code']).lower() in ['pending', 'complete', 'canceled', 'time out']:
        # Only status value, not a transaction
        if not has_amount:
            return False
    
    # Must have both a date and a non-zero amount to be a valid transaction
    return has_date and has_amount

async def process_and_save_transactions(csv_data: str, user_id: uuid.UUID, source: str, db: Session) -> Dict:
    """
    Process CSV data, convert to transactions, and save to database
    """
    try:
        # Step 1: Convert to standard format 
        std_df = convert_to_standard_format(csv_data, source)
        
        if std_df.empty:
            return {
                "success": False,
                "message": "No valid transactions found in file",
                "count": 0
            }
        
        # Step 2: Convert to Transaction objects with categories
        transactions = await standard_format_to_transactions(std_df, user_id)
        
        if not transactions:
            return {
                "success": False,
                "message": "No valid financial transactions found in file",
                "count": 0
            }
        
        # Step 3: Save to database
        db.add_all(transactions)
        db.commit()
        
        return {
            "success": True,
            "message": f"Successfully saved {len(transactions)} transactions",
            "count": len(transactions),
            "source": source
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error processing transactions: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "count": 0
        }

def convert_to_standard_format(raw_csv: str, source: str) -> pd.DataFrame:
    """
    Converts raw CSV from any financial source to standardized DataFrame format
    that works with any statement type (eSewa, Khalti, etc.)
    
    Args:
        raw_csv: Raw CSV string
        source: Source name (e.g., "eSewa", "Khalti")
        
    Returns:
        Standardized pandas DataFrame with consistent column names
    """
    # Find the header row
    csv_lines = raw_csv.splitlines()
    header_row = -1
    
    # Detect header row
    for idx, line in enumerate(csv_lines):
        line_lower = line.lower()
        if (('date' in line_lower and ('description' in line_lower or 'narration' in line_lower)) or
            ('txn' in line_lower) or ('transaction' in line_lower)):
            header_row = idx
            break
    
    if header_row == -1:
        print("Could not find transaction header row")
        # Create empty DataFrame with standard columns
        return pd.DataFrame(columns=[
            "transaction_id", "transaction_date", "transaction_time", 
            "description", "dr", "cr", "balance", "source", "raw_data"
        ])
    
    # Create a CSV with just the transaction data
    transaction_csv = '\n'.join([csv_lines[header_row]] + csv_lines[header_row+1:])
    
    try:
        # Parse with pandas
        df = pd.read_csv(
            StringIO(transaction_csv), 
            sep=',',
            engine='python',
            on_bad_lines='skip',
            dtype=str
        )
        
        # Clean data
        df = df.dropna(how='all')
        
        # Find columns based on source
        if source.lower() == "esewa":
            date_col = next((col for col in df.columns if 'date time' in col.lower()), None)
            desc_col = next((col for col in df.columns if 'description' in col.lower()), None)
            debit_col = next((col for col in df.columns if 'dr.' in col.lower()), None)
            credit_col = next((col for col in df.columns if 'cr.' in col.lower()), None)
            balance_col = next((col for col in df.columns if 'balance' in col.lower()), None)
            ref_col = next((col for col in df.columns if 'reference code' in col.lower()), None)
        
        elif source.lower() == "khalti":
            date_col = next((col for col in df.columns if 'transaction date' in col.lower()), None)
            time_col = next((col for col in df.columns if 'transaction time' in col.lower()), None)
            desc_col = next((col for col in df.columns if 'description' in col.lower()), None)
            debit_col = next((col for col in df.columns if 'amount(-)' in col.lower()), None)
            credit_col = next((col for col in df.columns if 'amount(+)' in col.lower()), None)
            balance_col = next((col for col in df.columns if 'balance' in col.lower()), None)
            ref_col = next((col for col in df.columns if 'transaction id' in col.lower()), None)
            
        else:
            # Generic mapping
            date_col = next((col for col in df.columns 
                           if any(term in col.lower() for term in ['date', 'txn date', 'transaction date'])), None)
            desc_col = next((col for col in df.columns 
                           if any(term in col.lower() for term in ['description', 'narration', 'particulars'])), None)
            debit_col = next((col for col in df.columns 
                            if any(term in col.lower() for term in ['dr', 'debit', 'withdrawal', 'withdraw'])), None)
            credit_col = next((col for col in df.columns 
                             if any(term in col.lower() for term in ['cr', 'credit', 'deposit'])), None)
            balance_col = next((col for col in df.columns 
                              if 'balance' in col.lower()), None)
            ref_col = next((col for col in df.columns 
                          if any(term in col.lower() for term in ['reference', 'ref', 'transaction id'])), None)
        
        # Create standardized DataFrame
        standard_data = []
        
        # Process rows
        for _, row in df.iterrows():
            # Additional checks for non-transaction rows
            
            # 1. Skip rows with too many NaN values (likely headers or separators)
            if row.isna().sum() > len(row) * 0.7:  # If more than 70% of fields are empty
                continue
                
            # 2. Skip rows that appear to be duplicated headers
            if date_col and pd.notna(row[date_col]) and any(
                str(row[date_col]).lower() == header.lower() for header in ['date', 'transaction date', 'txn date']
            ):
                continue
            
            # 3. Use enhanced is_valid_transaction with description column
            if not is_valid_transaction(row, date_col, debit_col, credit_col, desc_col):
                continue
            
            # 4. Skip if both debit and credit are zero or empty (informational rows)
            dr_amount = 0.0
            cr_amount = 0.0
            
            if debit_col and pd.notna(row[debit_col]):
                dr_str = str(row[debit_col])
                if dr_str and dr_str.strip() and dr_str.strip() not in ['-', 'nan', 'NaN']:
                    try:
                        dr_clean = re.sub(r'[^\d.]', '', dr_str.replace(',', ''))
                        if dr_clean:
                            dr_amount = float(dr_clean)
                    except:
                        pass
            
            if credit_col and pd.notna(row[credit_col]):
                cr_str = str(row[credit_col])
                if cr_str and cr_str.strip() and cr_str.strip() not in ['-', 'nan', 'NaN']:
                    try:
                        cr_clean = re.sub(r'[^\d.]', '', cr_str.replace(',', ''))
                        if cr_clean:
                            cr_amount = float(cr_clean)
                    except:
                        pass
            
            if dr_amount == 0.0 and cr_amount == 0.0:
                continue
            
            # 5. Get description for further filtering
            description = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else ""
            
            # 6. Skip rows with descriptions that indicate they're not transactions
            if any(term in description.lower() for term in [
                'total', 'balance b/f', 'balance c/f', 'opening', 'closing',
                'statement generated', 'beginning', 'ending', 'subtotal'
            ]):
                continue
                
            # Now extract all the transaction fields as before...
            
            # 1. Extract transaction_date and transaction_time
            transaction_date = datetime.now().date() 
            transaction_time = datetime.now().time()
            
            if date_col and pd.notna(row[date_col]):
                date_str = str(row[date_col]).strip()
                try:
                    # Handle datetime field (eSewa)
                    if ":" in date_str:
                        dt = pd.to_datetime(date_str)
                        transaction_date = dt.date()
                        transaction_time = dt.time()
                    else:
                        # Try multiple formats
                        for fmt in [None, '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                            try:
                                if fmt:
                                    transaction_date = datetime.strptime(date_str, fmt).date()
                                else:
                                    transaction_date = pd.to_datetime(date_str).date()
                                break
                            except:
                                continue
                except:
                    pass
            
            # 2. description
            description = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else ""
            
            # 3. dr
            dr = 0.0
            if debit_col and pd.notna(row[debit_col]):
                dr_str = str(row[debit_col])
                if dr_str and dr_str.strip() and dr_str.strip() not in ['-', 'nan', 'NaN']:
                    try:
                        dr_clean = re.sub(r'[^\d.]', '', dr_str.replace(',', ''))
                        if dr_clean:
                            dr = float(dr_clean)
                    except:
                        pass
            
            # 4. cr
            cr = 0.0
            if credit_col and pd.notna(row[credit_col]):
                cr_str = str(row[credit_col])
                if cr_str and cr_str.strip() and cr_str.strip() not in ['-', 'nan', 'NaN']:
                    try:
                        cr_clean = re.sub(r'[^\d.]', '', cr_str.replace(',', ''))
                        if cr_clean:
                            cr = float(cr_clean)
                    except:
                        pass
            
            # Skip if no transaction amount
            if dr == 0.0 and cr == 0.0:
                continue
            
            # 5. balance
            balance = 0.0
            if balance_col and pd.notna(row[balance_col]):
                bal_str = str(row[balance_col])
                if bal_str and bal_str.strip():
                    try:
                        bal_clean = re.sub(r'[^\d.]', '', bal_str.replace(',', ''))
                        if bal_clean:
                            balance = float(bal_clean)
                    except:
                        pass
            
            # 6. transaction_id
            transaction_id = None
            if ref_col and pd.notna(row[ref_col]):
                transaction_id = str(row[ref_col]).strip()
                # Skip status indicators with no amounts
                if transaction_id.lower() in ['pending', 'complete', 'canceled', 'time out'] and dr == 0.0 and cr == 0.0:
                    continue
            
            # Add to standardized data list
            standard_data.append({
                "transaction_id": transaction_id,
                "transaction_date": transaction_date,
                "transaction_time": transaction_time, 
                "description": description,
                "dr": dr,
                "cr": cr,
                "balance": balance,
                "source": source,
                "raw_data": json.dumps(row.to_dict())
            })
        
        # Create DataFrame from records
        standard_df = pd.DataFrame(standard_data)
        return standard_df
        
    except Exception as e:
        print(f"Error converting to standard format: {str(e)}")
        # Return empty DataFrame with standard columns
        return pd.DataFrame(columns=[
            "transaction_id", "transaction_date", "transaction_time", 
            "description", "dr", "cr", "balance", "source", "raw_data"
        ])


async def standard_format_to_transactions(df: pd.DataFrame, user_id: uuid.UUID) -> List[Transaction]:
    """
    Converts standardized DataFrame to Transaction objects with categories
    """
    transactions = []
    
    if df.empty:
        return []
    
    for _, row in df.iterrows():
        try:
            # Get the description for category detection
            description = str(row.get("description", ""))
            
            # Detect category based only on the description
            category = await detect_category_for_transaction(description)
            
            # Create Transaction object with category field
            transaction = Transaction(
                id=uuid.uuid4(),
                user_id=user_id,
                transaction_id=row.get("transaction_id"),
                transaction_date=row.get("transaction_date"),
                transaction_time=row.get("transaction_time"),
                description=description,
                category=category,  # Add category here
                dr=float(row.get("dr", 0.0)),
                cr=float(row.get("cr", 0.0)),
                source=row.get("source", "Unknown"),
                balance=float(row.get("balance", 0.0)),
                raw_data=row.get("raw_data", "{}")
            )
            
            transactions.append(transaction)
            
        except Exception as e:
            print(f"Error creating transaction: {str(e)}")
            continue
            
    return transactions