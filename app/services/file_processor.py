import io
import pandas as pd
import pdfplumber  # Replace PyPDF2 with pdfplumber
import csv
from fastapi import UploadFile
from typing import Dict, List, Tuple, Union

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
        
        return {
            "success": True,
            "format": file_format,
            "message": f"Successfully processed {file_format} file",
            "data": csv_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "format": file_format,
            "message": f"Error processing file: {str(e)}",
            "data": None
        }