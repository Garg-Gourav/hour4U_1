# services/data_parser.py

import pandas as pd
from datetime import datetime

class DataParser:
    """
    Utility class for parsing and normalizing Excel files.
    """
    def parse_excel(self, file_stream, required_fields):
        """
        Parse the Excel file and extract records ensuring required fields are present.
        Additionally, normalize the data to match the desired format.
        
        Args:
            file_stream (BytesIO): File-like object containing Excel data.
            required_fields (list): List of required field names.
        
        Returns:
            list: List of normalized records as dictionaries.
        
        Raises:
            ValueError: If required fields are missing in any sheet.
        """
        try:
            xls = pd.ExcelFile(file_stream)
            data = []
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                
                # Check for required fields
                missing_fields = [field for field in required_fields if field not in df.columns]
                if missing_fields:
                    raise ValueError(f"Missing required fields in sheet '{sheet_name}': {', '.join(missing_fields)}")
                
                # Drop rows where all elements are NaN
                df.dropna(how='all', inplace=True)
                
                # Convert dataframe to list of dictionaries
                records = df.to_dict(orient='records')
                
                for record in records:
                    # Ensure all required fields are present in each record
                    if not all(field in record and pd.notnull(record[field]) for field in required_fields):
                        continue  # Skip incomplete records
                    
                    # Normalize fields
                    normalized_record = self.normalize_record(record, sheet_name)
                    
                    data.append(normalized_record)
            return data
        except Exception as e:
            raise e

    def normalize_record(self, record, sheet_name):
        """
        Normalize individual record fields to match the desired format.
        
        Args:
            record (dict): Original record.
            sheet_name (str): Name of the Excel sheet.
        
        Returns:
            dict: Normalized record.
        """
        normalized = {}
        
        # Name
        normalized['Name'] = str(record.get('Name')).strip()
        
        # Number: Ensure it's a string with '+91' prefix if applicable
        number = str(record.get('Number')).strip()
        normalized['Number'] = self.normalize_number(number)
        
        # Shift Name: Remove ' Shift' suffix if present
        shift_name = str(record.get('Shift Name')).strip()
        if shift_name.endswith(' Shift'):
            shift_name = shift_name.replace(' Shift', '').strip()
        normalized['Shift Name'] = shift_name
        
        # Shift Timings: Remove spaces around '-' and ensure format "HH:MM-HH:MM"
        shift_timings = str(record.get('Shift Timings')).strip().replace(' ', '')
        normalized['Shift Timings'] = shift_timings
        
        # Dress Code
        normalized['Dress Code'] = str(record.get('Dress Code')).strip()
        
        # Work Description
        normalized['Work Description'] = str(record.get('Work Description')).strip()
        
        # Date: Convert to "YYYY-MM-DD" format
        date_str = str(record.get('date')).strip()
        normalized['date'] = self.validate_and_normalize_date(date_str)
        
        # sheet_name
        normalized['sheet_name'] = sheet_name
        
        # Additional Fields
        normalized['Recording SID'] = ""
        normalized['12h follow-up'] = ""
        normalized['2h follow-up'] = ""
        normalized['Dress-update'] = ""
        normalized['future-shift-interest'] = ""
        
        return normalized

    def normalize_number(self, number_str):
        """
        Normalize the phone number based on the following rules:
        
        1. If the number has exactly 10 digits, add '+91' prefix.
           Example: '1234567890' -> '+911234567890'
        
        2. If the number starts with '91' and has exactly 10 digits, add '+' prefix.
           Example: '9123456789' -> '+919123456789'
        
        3. If the number starts with '91' and has exactly 12 digits, add '+' prefix.
           Example: '911287654390' -> '+911287654390'
        
        4. If the number already starts with '+', leave it unchanged.
           Example: '+12365478964' -> '+12365478964'
        
        Args:
            number_str (str): Original phone number as a string.
        
        Returns:
            str: Normalized phone number.
        """
        if number_str.startswith('+'):
            return number_str
        elif number_str.startswith('91') and len(number_str) == 12 and number_str[2:].isdigit():
            return f"+{number_str}"
        elif number_str.startswith('91') and len(number_str) == 10 and number_str.isdigit():
            return f"+{number_str}"
        elif len(number_str) == 10 and number_str.isdigit():
            return f"+91{number_str}"
        else:
            # If the number doesn't match any of the above patterns, return it as is
            return number_str

    def validate_and_normalize_date(self, date_str):
        """
        Validate and normalize the date to "YYYY-MM-DD" format.
        
        Args:
            date_str (str): Original date string.
        
        Returns:
            str: Normalized date string in "YYYY-MM-DD" format.
        
        Raises:
            ValueError: If the date format is invalid.
        """
        try:
            # Attempt to parse the date with dayfirst=True
            date_parsed = pd.to_datetime(date_str, dayfirst=True)
            return date_parsed.strftime('%Y-%m-%d')
        except:
            # If parsing fails, raise an error
            raise ValueError("Invalid date format. Expected format: DD/MM/YYYY or YYYY-MM-DD")
