# Filename: extract_pdf_to_csv.py
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-01-27
# Last Modified: 2025-01-27
# Description: Extracts structured data from PDF documents using Gemini API and saves to CSV format.

#!/usr/bin/env python3
"""
Optimized Batch Gemini PDF Extractor for Agricultural Gazette Documents

This script has been optimized based on Gemini API best practices including:
- Proper API request structure with safety settings
- Enhanced prompt engineering with structured instructions
- Robust error handling with retry logic and exponential backoff
- Input validation and file size checks
- Improved JSON parsing with proper cleanup
- Type hints and comprehensive documentation
- Configuration validation and better logging

Author: AI Assistant
Version: 2.0 (Optimized)
Date: 2025-07-03
"""

import os
import json
import csv
import datetime
import traceback
import base64
import time
import configparser
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import google-genai instead of requests
from google import genai
from google.genai import types

class PDFExtractor:
    def __init__(self, config_path='../config/config.ini'):
        """Initialize the PDF extractor with configuration."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.setup_gemini_api()
        
        # API Configuration Constants
        self.MAX_FILE_SIZE_MB = 20
        self.REQUEST_TIMEOUT = 60
        self.RETRY_DELAY_BASE = 2
        self.INTER_REQUEST_DELAY = 1
        
        self.SCHEMA = [
            # Document & Meeting Metadata
            'source_document_filename', 'document_id', 'document_date', 'document_publication_date', 'meeting_number', 'meeting_title', 'chairman_name', 'member_secretary', 'meeting_location',
            # Administrative & Process Metadata
            'extraction_timestamp', 'item_number', 'table_source', 'entry_sequence', 'approval_status', 'decision_date', 'effective_date', 'gazette_notification_reference',
            # Variety/Hybrid Core Information
            'crop_category', 'crop_type', 'variety_name', 'variety_code', 'alternate_names', 'hybrid_indicator', 'release_type', 'maturity_group', 'special_traits', 'breeding_method',
            # Geographic & Ecological Data
            'recommended_states', 'agro_climatic_zones', 'excluded_areas', 'soil_type_suitability', 'rainfall_requirements', 'temperature_tolerance',
            # Institutional & Sponsorship Data
            'sponsoring_institution', 'institution_type', 'institution_location', 'principal_investigator', 'collaborating_institutions', 'funding_source', 'development_period', 'testing_locations',
            # Technical & Scientific Data
            'parent_material', 'breeding_program', 'testing_duration', 'yield_performance', 'quality_parameters', 'disease_resistance', 'pest_tolerance',
            # Regulatory & Compliance Data
            'notification_requirements', 'seed_sample_submission', 'dna_fingerprinting', 'morphological_characterization', 'package_of_practices', 'intellectual_property_status',
            # Status & Action Items
            'deferment_reason', 'rejection_reason', 'missing_documents', 'follow_up_action', 'responsible_party',
            # Contextual & Reference Data
            'preceding_context', 'table_caption', 'additional_notes', 'page_reference', 'cross_references', 'historical_context',
        ]
    
    def _load_config(self, config_path):
        """Load configuration from config file."""
        config = configparser.ConfigParser()
        config.read(config_path)
        return config
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_dir = self.config.get('PATHS', 'logs_dir', fallback='logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/pdf_extraction.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_gemini_api(self):
        """Setup Gemini API with configuration."""
        api_key = self.config.get('API_KEYS', 'gemini_api_key')
        if not api_key or api_key == 'YOUR_GEMINI_API_KEY_HERE':
            raise ValueError("Please configure a valid Gemini API key in config.ini")
        
        genai.configure(api_key=api_key)
        self.model_name = self.config.get('SETTINGS', 'gemini_model', fallback='gemini-2.5-flash')
        self.logger.info(f"Gemini API configured with model: {self.model_name}")
    
    def log(self, msg: str) -> None:
        """Enhanced logging function with timestamp and console output."""
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f'{timestamp} - {msg}'
        
        # Write to log file
        try:
            log_file = Path(self.config.get('PATHS', 'logs_dir')) / 'pdf_extraction.log'
            with open(log_file, 'a', encoding='utf-8') as logf:
                logf.write(log_entry + '\n')
        except Exception as e:
            print(f"Failed to write to log file: {e}")
        
        # Also print to console
        print(log_entry)
    
    def get_pdf_files(self, folder: str) -> List[str]:
        """Get list of PDF files in the specified folder."""
        try:
            all_files = os.listdir(folder)
            pdf_files = [f for f in all_files if f.lower().endswith('.pdf')]
            return sorted(pdf_files)
        except Exception as e:
            self.log(f"Error reading PDF directory {folder}: {e}")
            return []
    
    def fix_incomplete_json(self, text: str) -> str:
        """
        Attempt to fix incomplete JSON by adding missing closing brackets.
        """
        text = text.strip()
        
        # Count opening and closing brackets
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        
        # Add missing closing brackets
        if open_brackets > close_brackets:
            text += ']' * (open_brackets - close_brackets)
        
        # Add missing closing braces
        if open_braces > close_braces:
            text += '}' * (open_braces - close_braces)
        
        return text
    
    def call_gemini_api(self, pdf_path: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Call Gemini API with optimized prompt and proper error handling using google-genai client.
        
        Args:
            pdf_path: Path to the PDF file
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of extracted data rows
        """
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # Highly optimized minimal prompt to avoid token limits
        extraction_prompt = f"""Extract all agricultural variety data from this PDF. Return JSON array with these fields for each variety:

{json.dumps(self.SCHEMA[:30], indent=1)}

Use "Not Specified" for missing data. Extract from ALL tables. Return only JSON array."""

        # Initialize the model
        model = genai.GenerativeModel(self.model_name)
        
        # Configure generation settings
        generation_config = types.GenerationConfig(
            temperature=0.1,
            top_k=40,
            top_p=0.95,
            max_output_tokens=65536
        )
        
        # Configure safety settings
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            )
        ]
        
        # Implement retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                # Generate content using the proper google-genai format
                response = model.generate_content(
                    [
                        types.Part.from_bytes(
                            mime_type="application/pdf",
                            data=pdf_bytes
                        ),
                        types.Part.from_text(text=extraction_prompt)
                    ],
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # Extract text content using the new simplified API
                text = response.text
                
                # Basic validation - if text is empty, something went wrong
                if not text:
                    raise RuntimeError("Empty response from Gemini API")
                
                # Clean and parse JSON response
                text = text.strip()
                if text.startswith('```json'):
                    text = text[7:]
                if text.endswith('```'):
                    text = text[:-3]
                text = text.strip()
                
                try:
                    data = json.loads(text)
                    if not isinstance(data, list):
                        raise ValueError("Response is not a JSON array")
                    return data
                except json.JSONDecodeError as e:
                    self.log(f"JSON parsing error on attempt {attempt + 1}: {e}")
                    self.log(f"Raw response text: {text[:500]}...")
                    
                    # Try to fix incomplete JSON (in case of MAX_TOKENS truncation)
                    try:
                        fixed_text = self.fix_incomplete_json(text)
                        data = json.loads(fixed_text)
                        if isinstance(data, list):
                            self.log(f"Successfully parsed after JSON fix, got {len(data)} items")
                            return data
                    except:
                        pass
                    
                    if attempt == max_retries - 1:
                        raise RuntimeError(f'Failed to parse JSON response after {max_retries} attempts')
                    
            except Exception as e:
                self.log(f"Error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                # Exponential backoff
                time.sleep(self.RETRY_DELAY_BASE ** attempt)
        
        raise RuntimeError(f'Failed to get valid response after {max_retries} attempts')
    
    def get_csv_filename(self, pdf_filename: str, doc_metadata: Dict[str, Any]) -> str:
        """Generate CSV filename based on document metadata."""
        # Try to extract meeting number and date from metadata, else fallback
        meeting_number = doc_metadata.get('meeting_number', 'Unknown')
        doc_date = doc_metadata.get('document_date', datetime.datetime.now().strftime('%Y%m%d'))
        
        # Clean up the meeting number and date for filename
        if meeting_number and meeting_number != 'Unknown' and meeting_number != 'Not Specified':
            # Remove special characters that might cause issues in filenames
            meeting_number = ''.join(c for c in str(meeting_number) if c.isalnum() or c in '-_')
            return f'AgriRegulatory_{meeting_number}_{doc_date}_ExtractedData.csv'
        else:
            # Use PDF filename as fallback
            base_name = os.path.splitext(pdf_filename)[0]
            base_name = ''.join(c for c in base_name if c.isalnum() or c in '-_')
            return f'AgriRegulatory_{base_name}_{doc_date}_ExtractedData.csv'
    
    def process_pdf(self, pdf_filename: str) -> bool:
        """
        Process a single PDF file and extract data to CSV.
        
        Args:
            pdf_filename: Name of the PDF file to process
            
        Returns:
            True if processing succeeded, False otherwise
        """
        pdf_dir = self.config.get('PATHS', 'raw_pdfs_dir')
        output_dir = self.config.get('PATHS', 'processed_dir')
        
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        try:
            self.log(f'Processing {pdf_filename}...')
            
            # Check file size (Gemini has limits)
            file_size = os.path.getsize(pdf_path)
            max_size_bytes = self.MAX_FILE_SIZE_MB * 1024 * 1024
            if file_size > max_size_bytes:
                self.log(f'WARNING: {pdf_filename} is {file_size/1024/1024:.1f}MB, may exceed API limits')
            
            # Call Gemini API with retry logic
            rows = self.call_gemini_api(pdf_path)
            
            if not rows or not isinstance(rows, list):
                raise ValueError('No data rows returned from API.')
            
            self.log(f'Extracted {len(rows)} rows from {pdf_filename}')
            
            # Use first row for metadata, or empty dict if no rows
            metadata = rows[0] if rows else {}
            csv_filename = self.get_csv_filename(pdf_filename, metadata)
            csv_path = os.path.join(output_dir, csv_filename)
            
            # Write to CSV with proper validation
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.SCHEMA, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                
                for i, row in enumerate(rows):
                    # Ensure row is a dictionary
                    if not isinstance(row, dict):
                        self.log(f'WARNING: Row {i} is not a dictionary, skipping')
                        continue
                    
                    # Ensure all schema fields are present
                    for col in self.SCHEMA:
                        if col not in row or row[col] is None or row[col] == '':
                            row[col] = 'Not Specified'
                        # Convert to string and clean up
                        row[col] = str(row[col]).strip()
                    
                    # Add extraction metadata
                    row['source_document_filename'] = pdf_filename
                    row['extraction_timestamp'] = datetime.datetime.now().isoformat()
                    
                    writer.writerow(row)
            
            self.log(f'SUCCESS: {pdf_filename} -> {csv_filename} ({len(rows)} rows)')
            return True
            
        except Exception as e:
            error_msg = f'ERROR: {pdf_filename}: {str(e)}'
            self.log(error_msg)
            self.log(f'Full traceback:\n{traceback.format_exc()}')
            return False
    
    def process_all_pdfs(self):
        """Process all PDF files in the raw_pdfs directory."""
        pdf_dir = self.config.get('PATHS', 'raw_pdfs_dir')
        output_dir = self.config.get('PATHS', 'processed_dir')
        
        # Ensure directories exist
        os.makedirs(pdf_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_files = self.get_pdf_files(pdf_dir)
        
        if not pdf_files:
            self.log("No PDF files found in the specified directory.")
            return
        
        self.log(f'Starting batch processing of {len(pdf_files)} PDF files.')
        self.log(f'Output directory: {output_dir}')
        self.log(f'Using Gemini model: {self.model_name}')
        
        success_count = 0
        failed_files = []
        
        start_time = datetime.datetime.now()
        
        for i, pdf_filename in enumerate(pdf_files):
            self.log(f'Processing file {i+1}/{len(pdf_files)}: {pdf_filename}')
            
            if self.process_pdf(pdf_filename):
                success_count += 1
            else:
                failed_files.append(pdf_filename)
            
            # Add small delay between requests to be respectful to the API
            if i < len(pdf_files) - 1:  # Don't delay after the last file
                time.sleep(self.INTER_REQUEST_DELAY)
        
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        
        self.log(f'Batch processing complete.')
        self.log(f'Results: {success_count}/{len(pdf_files)} files processed successfully')
        self.log(f'Total time: {duration}')
        self.log(f'Average time per file: {duration.total_seconds() / len(pdf_files):.1f} seconds')
        
        if failed_files:
            self.log(f'Failed files: {", ".join(failed_files)}')

def main():
    """Main execution function with improved error handling and logging."""
    try:
        extractor = PDFExtractor()
        extractor.process_all_pdfs()
        
    except Exception as e:
        print(f'FATAL ERROR in main(): {e}\n{traceback.format_exc()}')

if __name__ == '__main__':
    main() 