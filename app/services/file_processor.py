import io
import pandas as pd
import pdfplumber
import csv
from fastapi import UploadFile
from typing import Dict, List, Tuple, Union

# Import the ask_groq function
from .groq_service import ask_groq

def detect_format(file: UploadFile) -> str:
    """
    Detect if file is PDF or Excel, return "unsupported" for other formats
    """
    filename = file.filename.lower()
    content_type = file.content_type
    
    # Check by content type first
    if (content_type == "application/pdf"):
        return "pdf"
    elif content_type in ["application/vnd.ms-excel", 
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        return "excel"
    #
    # Fallback to extension check
    if filename.endswith(".pdf"):
        return "pdf"
    elif filename.endswith((".xls", ".xlsx")):
        return "excel"
    
    return "unsupported"

async def process_pdf(file_content: bytes) -> str:
    """
    Process PDF file and extract tables using pdfplumber
    """
    all_tables = []
    
    with io.BytesIO(file_content) as f:
        # Open PDF with pdfplumber
        with pdfplumber.open(f) as pdf:
            # Process each page
            for page in pdf.pages:
                # Extract tables from the page
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        all_tables.append(table)
                
                # If no tables found, try to extract text and parse it
                if not tables:
                    text = page.extract_text()
                    if text:
                        # Split text into lines and try to extract structured data
                        lines = text.split('\n')
                        for line in lines:
                            if line.strip():
                                # Basic parsing - customize based on your statement format
                                parts = line.split()
                                if len(parts) >= 4:  # Assuming transaction lines have at least 4 parts
                                    all_tables.append(parts)
    
    # Convert extracted data to CSV
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    
    # Write tables to CSV
    for table in all_tables:
        if isinstance(table, list) and all(isinstance(row, list) for row in table):
            # Handle full table
            for row in table:
                csv_writer.writerow(row)
        else:
            # Handle row
            csv_writer.writerow(table)
    
    # Print preview of CSV for debugging
    csv_data = csv_buffer.getvalue()
    print(f"CSV Preview: {csv_data[:500]}...")
    
    return csv_data

async def process_excel(file_content: bytes, filename: str) -> str:
    """
    Process Excel file and convert to CSV string
    """
    # Determine engine based on file extension
    engine = 'xlrd' if filename.lower().endswith('.xls') else 'openpyxl'
    print(f"Processing Excel file with engine: {engine}")
    
    # Read Excel file into pandas DataFrame
    with io.BytesIO(file_content) as f:
        df = pd.read_excel(f, engine=engine)
    
    # Convert DataFrame to CSV string
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_string = csv_buffer.getvalue()
    
    # Print preview for debugging
    print(f"Excel CSV Preview: {csv_string[:500]}...")
    
    return csv_string

async def process_file(file: UploadFile) -> Dict:
    """
    Main function to process file and return CSV data
    """
    # Read file content
    file_content = await file.read()
    
    # Detect format
    file_format = detect_format(file)
    
    if file_format == "unsupported":
        return {
            "success": False,
            "format": file_format,
            "message": "Unsupported file format. Please upload PDF or Excel file.",
            "data": None
        }
    
    try:
        # Process based on format
        if file_format == "pdf":
            csv_data = await process_pdf(file_content)
        elif file_format == "excel":
            csv_data = await process_excel(file_content, file.filename)
        
        # Use Groq to analyze the CSV data
        system_prompt = """
You are a financial data analysis expert. Your job is to determine the *source* of CSV transaction data files extracted from banks or financial platforms in Nepal. 

You will receive a raw CSV preview as text. Based on its structure (column headers, formatting, terminology), identify which platform the data most likely belongs to.

Common sources include (but are not limited to):
- Khalti
- eSewa
- Global IME Bank

You should identify patterns like:
- Transaction formats
- Common field names (e.g., Dr./Cr., Reference Code)
- Keywords (e.g., Fonepay, Statement Report, MOS:NTC)
- Column styles and header naming

Respond ONLY with a valid JSON in the following format:
```json
{"source": "<detected source>"}
```
Do not add any explanation or additional data. If uncertain, guess the **most likely** source.

---

Examples:

---

Example 1: **Khalti**
```
Transaction ID,Transaction Type,Transaction State,Transaction Date,Transaction Time,Service,Description,From,To,Purpose,Remarks,Reference,Amount(-) Rs,Amount(+) Rs,Balance
U94yr4RKnbnJfpdk5u6GSY,Scan and Pay,Completed,2025-04-07,18:06:40,,Scan and Transfer of Rs 500.0 to Fonepay .,Ukran Tandukar (9847344775),Fonepay ,Personal use,ttt,,500,,0
```
→
```json
{"source": "Khalti"}
```

---

Example 2: **eSewa**
```
Statement Report,Unnamed: 1,Unnamed: 2,Unnamed: 3,Unnamed: 4
From Date,Wed Mar 12 00:00:00 NPT 2025
Generated by,9819492581
Reference Code,Date Time,Description,Dr.,Cr.,Status,Balance (NPR),Channel
0VOJMBI,2025-04-11 10:15:13.0,Fund Transferred to Prithivi Rawal,30.0,0.0,COMPLETE,290.14,App
```
→
```json
{"source": "eSewa"}
```

---

Example 3: **Global IME Bank**
```
Electronic,Account,Statement,From,01-04-2025,To,12-04-2025
Account,Name,BIPLOV,GAUTAM,Opening,Balance,"1,370.24"
Account,Number,32207010040691,Closing,Balance,"5,005.72"
Account,Currency,NPR,Accrued,Interest,11.22
TXN,Date,Value,Date,Description,Remarks,Withdraw,Deposit,Balance
2025-04-12,2025-04-12,MOS:NTC,QCD9V9JN8NO:97,10.00,-,"5,005.72"
2025-04-11,2025-04-11,ASBA,CHARGE,PURE,5.00,-,"5,015.72"
```
→
```json
{"source": "Global IME"}
```

---

Now, detect the source from the following CSV:
```
{{CSV_PREVIEW_INPUT_HERE}}
```
"""
        
        user_prompt = f"""Analyze this CSV data and tell me which bank or financial platform it's from:
        ```
        {csv_data[:2000]}
        ```
        
        Return your answer in JSON format: {{"source": "SOURCE_NAME", "confidence": "HIGH/MEDIUM/LOW"}}
        """
        
        # Call Groq API
        groq_response = await ask_groq(system_prompt, user_prompt)
        print(f"\n----- GROQ ANALYSIS RESULT -----\n{groq_response}\n-------------------------------\n")
        
        try:
            # Parse JSON from Groq
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', groq_response)
            if json_match:
                analysis_data = json.loads(json_match.group(0))
                source = analysis_data.get("source", "Unknown")
            else:
                source = "Unknown"
        except Exception as e:
            print(f"Error parsing Groq response: {e}")
            source = "Unknown"
        
        return {
            "success": True,
            "format": file_format,
            "message": f"Successfully processed {file_format} file",
            "data": csv_data,
            "analysis": groq_response,
            "source": source
        }
        
    except Exception as e:
        return {
            "success": False,
            "format": file_format,
            "message": f"Error processing file: {str(e)}",
            "data": None
        }