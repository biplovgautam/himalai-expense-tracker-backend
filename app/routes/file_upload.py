from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
import pandas as pd
from io import StringIO
import uuid

from ..core.database import get_db
from ..models.user import User
from ..models.transaction import Transaction
from ..services.file_processor import detect_format, process_file

router = APIRouter(
    prefix="/files",
    tags=["file processing"]
)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    """
    Comprehensive endpoint that:
    1. Accepts file upload
    2. Processes file content 
    3. Creates transaction records
    4. Returns summary statistics
    """
    # Verify the user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    try:
        # Use the existing process_file function that handles both formats
        # This function already handles file content reading and format detection
        result = await process_file(file)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result["message"]
            )
        
        # Process CSV data into transactions
        csv_data = result["data"]
        file_format = result["format"]
        
        # Parse CSV data
        df = pd.read_csv(StringIO(csv_data))
        
        # Basic data cleaning
        df = df.dropna(how='all')  # Drop empty rows
        
        # Process each row and create transaction records
        transactions = []
        
        for _, row in df.iterrows():
            try:
                # Try to extract date and amount information
                transaction_date = None
                description = ""
                dr_amount = 0.0
                cr_amount = 0.0
                balance = 0.0
                
                # Example mapping logic - customize based on your data
                for col in row.index:
                    col_lower = str(col).lower()
                    if any(date_term in col_lower for date_term in ['date', 'transaction date', 'value date']):
                        # Try to extract and parse date
                        try:
                            transaction_date = pd.to_datetime(row[col]).date()
                        except:
                            pass
                    
                    elif any(desc_term in col_lower for desc_term in ['description', 'narration', 'particulars', 'details']):
                        description = str(row[col]) if pd.notna(row[col]) else ""
                    
                    elif any(debit_term in col_lower for debit_term in ['debit', 'withdrawal', 'dr', 'outflow']):
                        dr_value = row[col]
                        if pd.notna(dr_value) and dr_value != '':
                            # Handle formatting issues with currencies
                            dr_str = str(dr_value).replace(',', '').replace('₹', '').strip()
                            try:
                                dr_amount = float(dr_str) if dr_str else 0.0
                            except:
                                dr_amount = 0.0
                    
                    elif any(credit_term in col_lower for credit_term in ['credit', 'deposit', 'cr', 'inflow']):
                        cr_value = row[col]
                        if pd.notna(cr_value) and cr_value != '':
                            # Handle formatting issues with currencies
                            cr_str = str(cr_value).replace(',', '').replace('₹', '').strip()
                            try:
                                cr_amount = float(cr_str) if cr_str else 0.0
                            except:
                                cr_amount = 0.0
                    
                    elif 'balance' in col_lower:
                        bal_value = row[col]
                        if pd.notna(bal_value) and bal_value != '':
                            # Handle formatting issues with currencies
                            bal_str = str(bal_value).replace(',', '').replace('₹', '').strip()
                            try:
                                balance = float(bal_str) if bal_str else 0.0
                            except:
                                balance = 0.0
                
                # Skip rows that don't have valid transaction data
                if transaction_date is None:
                    continue
                
                # Create transaction record
                transaction = Transaction(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    transaction_id=None,  # Generate or extract from data if available
                    transaction_date=transaction_date,
                    transaction_time=datetime.now().time(),  # Default if not available
                    description=description,
                    dr=dr_amount,
                    cr=cr_amount,
                    source=file.filename.split('.')[0] if '.' in file.filename else file.filename,  # Use filename as source
                    balance=balance,
                    raw_data=str(row.to_dict())  # Store the original row data
                )
                
                transactions.append(transaction)
                
            except Exception as e:
                # Log error but continue processing other rows
                print(f"Error processing row: {str(e)}")
                continue
        
        # Save all valid transactions to database
        if transactions:
            db.add_all(transactions)
            db.commit()
            
            # Calculate basic statistics for response
            total_transactions = len(transactions)
            total_debit = sum(t.dr for t in transactions)
            total_credit = sum(t.cr for t in transactions)
            net_flow = total_credit - total_debit
            
            # Get date range
            start_date = min(t.transaction_date for t in transactions)
            end_date = max(t.transaction_date for t in transactions)
            
            return {
                "success": True,
                "message": f"Successfully processed {total_transactions} transactions",
                "file_format": file_format,
                "user_id": str(user_id),
                "summary": {
                    "total_transactions": total_transactions,
                    "date_range": f"{start_date} to {end_date}",
                    "total_debits": total_debit,
                    "total_credits": total_credit,
                    "net_flow": net_flow
                }
            }
        else:
            return {
                "success": False,
                "message": "No valid transactions found in the file",
                "file_format": file_format
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )