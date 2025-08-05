# Filename: match_and_merge.py
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-08-01
# Last Modified: 2025-08-01
# Description: Performs fuzzy matching and merging between CSC and SeedNet variety data.

#!/usr/bin/env python3
"""
CSC-SeedNet Variety Matching Pipeline
====================================

Robust fuzzy matching pipeline between CSC and SeedNet variety data with:
- Unique CSC raw IDs for tracking
- Complete data coverage
- Comprehensive analysis and reporting

Requirements:
0.0: Analyze random 100 rows from matches and unmatched sets
0.1: Copy raw data to new folder
0: Add unique raw ID for CSC tracking
1: Organize outputs in folder structure
2: Extract year from CSC data
3: Final CSV with manual review columns + ALL CSC varieties
4: Generate completion report
"""

import pandas as pd
import numpy as np
import shutil
import configparser
from pathlib import Path
from datetime import datetime
import json
import re
from fuzzywuzzy import fuzz, process
import warnings
import logging
import os
warnings.filterwarnings('ignore')

class CSCSeedNetMatcher:
    """Main class for CSC-SeedNet variety matching with unique ID tracking."""
    
    def __init__(self, config_path='../config/config.ini'):
        """Initialize the matcher with configuration and output directory structure."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(self.config.get('PATHS', 'processed_dir')) / f"matching_results_{timestamp}"
        
        # Create organized folder structure
        self.folders = {
            'raw_data': self.output_dir / 'raw_data',
            'analysis': self.output_dir / 'analysis', 
            'final_datasets': self.output_dir / 'final_datasets',
            'manual_review': self.output_dir / 'manual_review',
            'reports': self.output_dir / 'reports'
        }
        
        for folder in self.folders.values():
            folder.mkdir(parents=True, exist_ok=True)
        
        self.timestamp = timestamp
        self.logger.info(f"Initialized CSC-SeedNet Matcher")
        self.logger.info(f"Output directory: {self.output_dir}")
    
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
                logging.FileHandler(f'{log_dir}/matching.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def copy_raw_data(self, csc_file, seednet_file):
        """Requirement 0.1: Copy raw data to new folder."""
        self.logger.info("=== REQUIREMENT 0.1: Copying raw data ===")
        
        # Copy CSC data
        csc_dest = self.folders['raw_data'] / 'csc_master_data.csv'
        shutil.copy2(csc_file, csc_dest)
        self.logger.info(f"Copied CSC data: {csc_dest}")
        
        # Copy SeedNet data  
        seednet_dest = self.folders['raw_data'] / 'seednet_data.csv'
        shutil.copy2(seednet_file, seednet_dest)
        self.logger.info(f"Copied SeedNet data: {seednet_dest}")
        
        return csc_dest, seednet_dest
    
    def load_and_prepare_data(self, csc_file, seednet_file):
        """Load and prepare data with unique CSC raw IDs."""
        self.logger.info("=== Loading and preparing data ===")
        
        # Load CSC data
        csc_df = pd.read_csv(csc_file)
        self.logger.info(f"Loaded CSC data: {len(csc_df)} rows")
        
        # Create truly unique raw IDs - one per row
        csc_df.reset_index(drop=True, inplace=True)
        csc_df['csc_raw_id'] = csc_df.index.map(lambda x: f"CSC_{x+1:06d}")
        
        # Verify uniqueness
        unique_count = csc_df['csc_raw_id'].nunique()
        total_count = len(csc_df)
        
        if unique_count != total_count:
            raise ValueError(f"Raw ID creation failed: {unique_count} unique vs {total_count} total")
        
        self.logger.info(f"Created {unique_count} unique CSC raw IDs")
        
        # Load SeedNet data
        seednet_df = pd.read_csv(seednet_file)
        self.logger.info(f"Loaded SeedNet data: {len(seednet_df)} rows")
        
        # Clean and standardize data
        csc_df = self._clean_csc_data(csc_df)
        seednet_df = self._clean_seednet_data(seednet_df)
        
        return csc_df, seednet_df
    
    def _clean_csc_data(self, df):
        """Clean and standardize CSC data."""
        self.logger.info("Cleaning CSC data...")
        
        # Find variety column
        variety_col = None
        for col in ['variety_standardized', 'crop_variety', 'variety_name']:
            if col in df.columns:
                variety_col = col
                break
        
        if not variety_col:
            raise ValueError(f"No variety column found in CSC data. Columns: {list(df.columns)}")
        
        # Find crop column
        crop_col = None
        for col in ['crop_standardized', 'crop', 'crop_type']:
            if col in df.columns:
                crop_col = col
                break
                
        if not crop_col:
            raise ValueError(f"No crop column found in CSC data. Columns: {list(df.columns)}")
        
        # Clean variety and crop names
        df['variety_clean'] = df[variety_col].astype(str).str.strip().str.lower()
        df['crop_clean'] = df[crop_col].astype(str).str.strip().str.lower()
        df['variety_original'] = df[variety_col]
        df['crop_original'] = df[crop_col]
        
        # Extract year (requirement 2)
        if 'extracted_year' in df.columns:
            df['year_extracted'] = pd.to_numeric(df['extracted_year'], errors='coerce')
        else:
            df['year_extracted'] = self._extract_year_from_text(df)
        
        # Remove invalid entries
        df = df[
            (df['variety_clean'] != 'nan') & 
            (df['variety_clean'] != '') &
            (df['variety_clean'].notna())
        ].copy()
        
        self.logger.info(f"Cleaned CSC data: {len(df)} valid rows")
        return df
    
    def _clean_seednet_data(self, df):
        """Clean and standardize SeedNet data."""
        self.logger.info("Cleaning SeedNet data...")
        
        # Find variety column
        variety_col = None
        for col in ['variety_name', 'variety', 'name']:
            if col in df.columns:
                variety_col = col
                break
        
        if not variety_col:
            raise ValueError(f"No variety column found in SeedNet data. Columns: {list(df.columns)}")
        
        # Find crop column
        crop_col = None
        for col in ['crop_name', 'crop', 'crop_type']:
            if col in df.columns:
                crop_col = col
                break
                
        if not crop_col:
            raise ValueError(f"No crop column found in SeedNet data. Columns: {list(df.columns)}")
        
        # Clean variety and crop names
        df['variety_clean'] = df[variety_col].astype(str).str.strip().str.lower()
        df['crop_clean'] = df[crop_col].astype(str).str.strip().str.lower()
        df['variety_original'] = df[variety_col]
        df['crop_original'] = df[crop_col]
        
        # Remove invalid entries
        df = df[
            (df['variety_clean'] != 'nan') & 
            (df['variety_clean'] != '') &
            (df['variety_clean'].notna())
        ].copy()
        
        self.logger.info(f"Cleaned SeedNet data: {len(df)} valid rows")
        return df
    
    def _extract_year_from_text(self, df):
        """Extract year from text fields in CSC data."""
        years = []
        
        # Look for year patterns in various columns
        text_columns = [col for col in df.columns if df[col].dtype == 'object']
        
        for idx, row in df.iterrows():
            year_found = None
            
            for col in text_columns:
                if pd.notna(row[col]):
                    text = str(row[col])
                    # Look for 4-digit year patterns
                    year_matches = re.findall(r'\b(19|20)\d{2}\b', text)
                    if year_matches:
                        year_found = int(year_matches[0])
                        break
            
            years.append(year_found)
        
        return years
    
    def perform_fuzzy_matching(self, csc_df, seednet_df, threshold=80):
        """Perform fuzzy matching between CSC and SeedNet varieties."""
        self.logger.info(f"=== Performing fuzzy matching (threshold: {threshold}%) ===")
        
        matched_results = []
        unmatched_results = []
        
        for idx, csc_row in csc_df.iterrows():
            csc_variety = csc_row['variety_clean']
            csc_crop = csc_row['crop_clean']
            csc_raw_id = csc_row['csc_raw_id']
            
            # Filter SeedNet by crop if possible
            if 'crop_clean' in seednet_df.columns:
                crop_filtered = seednet_df[seednet_df['crop_clean'] == csc_crop]
                if len(crop_filtered) == 0:
                    crop_filtered = seednet_df  # Fallback to all data
            else:
                crop_filtered = seednet_df
            
            # Find best match
            best_match = process.extractOne(
                csc_variety,
                crop_filtered['variety_clean'].tolist(),
                scorer=fuzz.ratio
            )
            
            if best_match and best_match[1] >= threshold:
                # Found a match
                seednet_match = crop_filtered[
                    crop_filtered['variety_clean'] == best_match[0]
                ].iloc[0]
                
                result = self._create_match_record(
                    csc_row, seednet_match, best_match[1], 'MATCHED'
                )
                matched_results.append(result)
            else:
                # No match found
                result = self._create_match_record(
                    csc_row, None, 0, 'UNMATCHED'
                )
                unmatched_results.append(result)
        
        matched_df = pd.DataFrame(matched_results)
        unmatched_df = pd.DataFrame(unmatched_results)
        
        self.logger.info(f"Matching complete:")
        self.logger.info(f"  Matched: {len(matched_df)} varieties")
        self.logger.info(f"  Unmatched: {len(unmatched_df)} varieties")
        
        return matched_df, unmatched_df
    
    def _create_match_record(self, csc_row, seednet_row, match_score, match_status):
        """Create a standardized match record."""
        record = {
            'csc_raw_id': csc_row['csc_raw_id'],
            'csc_variety_original': csc_row['variety_original'],
            'csc_variety_clean': csc_row['variety_clean'],
            'csc_crop_original': csc_row['crop_original'],
            'csc_crop_clean': csc_row['crop_clean'],
            'csc_year': csc_row.get('year_extracted'),
            'match_status': match_status,
            'similarity_score': match_score,
            'match_confidence': self._categorize_confidence(match_score)
        }
        
        if seednet_row is not None:
            record.update({
                'seednet_variety_original': seednet_row['variety_original'],
                'seednet_variety_clean': seednet_row['variety_clean'],
                'seednet_crop_original': seednet_row['crop_original'],
                'seednet_crop_clean': seednet_row['crop_clean'],
                'manual_review_needed': match_score < 95
            })
        else:
            record.update({
                'seednet_variety_original': None,
                'seednet_variety_clean': None,
                'seednet_crop_original': None,
                'seednet_crop_clean': None,
                'manual_review_needed': True
            })
        
        return record
    
    def _categorize_confidence(self, score):
        """Categorize match confidence based on similarity score."""
        if score >= 95:
            return 'HIGH'
        elif score >= 80:
            return 'MEDIUM'
        elif score >= 60:
            return 'LOW'
        else:
            return 'VERY_LOW'
    
    def analyze_random_samples(self, matched_df, unmatched_df, sample_size=100):
        """Analyze random samples for quality assessment."""
        self.logger.info(f"=== Analyzing random samples (size: {sample_size}) ===")
        
        analysis_results = {
            'matched_sample': matched_df.sample(min(sample_size, len(matched_df))),
            'unmatched_sample': unmatched_df.sample(min(sample_size, len(unmatched_df))),
            'total_matched': len(matched_df),
            'total_unmatched': len(unmatched_df),
            'match_rate': len(matched_df) / (len(matched_df) + len(unmatched_df)) * 100
        }
        
        # Save samples for manual review
        analysis_results['matched_sample'].to_csv(
            self.folders['manual_review'] / 'matched_sample_for_review.csv', 
            index=False
        )
        analysis_results['unmatched_sample'].to_csv(
            self.folders['manual_review'] / 'unmatched_sample_for_review.csv', 
            index=False
        )
        
        self.logger.info(f"Analysis complete:")
        self.logger.info(f"  Total matched: {analysis_results['total_matched']}")
        self.logger.info(f"  Total unmatched: {analysis_results['total_unmatched']}")
        self.logger.info(f"  Match rate: {analysis_results['match_rate']:.1f}%")
        
        return analysis_results
    
    def create_final_dataset(self, matched_df, unmatched_df):
        """Create final dataset with all CSC varieties and manual review flags."""
        self.logger.info("=== Creating final dataset ===")
        
        # Combine matched and unmatched data
        final_df = pd.concat([matched_df, unmatched_df], ignore_index=True)
        
        # Add additional columns for manual review
        final_df['review_priority'] = final_df.apply(self._assign_review_priority, axis=1)
        final_df['data_source'] = 'CSC'
        final_df['processing_timestamp'] = datetime.now().isoformat()
        
        # Save final dataset
        final_file = self.folders['final_datasets'] / 'csc_seednet_matches_final.csv'
        final_df.to_csv(final_file, index=False)
        
        self.logger.info(f"Final dataset created: {final_file}")
        self.logger.info(f"Total records: {len(final_df)}")
        
        return final_df, final_file
    
    def _assign_review_priority(self, row):
        """Assign review priority based on match status and confidence."""
        if row['match_status'] == 'UNMATCHED':
            return 'HIGH'
        elif row['similarity_score'] < 90:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def generate_completion_report(self, final_df, analysis_results, final_file):
        """Generate comprehensive completion report."""
        self.logger.info("=== Generating completion report ===")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_csc_varieties': len(final_df),
            'matched_varieties': analysis_results['total_matched'],
            'unmatched_varieties': analysis_results['total_unmatched'],
            'match_rate': analysis_results['match_rate'],
            'confidence_distribution': final_df['match_confidence'].value_counts().to_dict(),
            'review_priority_distribution': final_df['review_priority'].value_counts().to_dict(),
            'output_files': {
                'final_dataset': str(final_file),
                'matched_sample': str(self.folders['manual_review'] / 'matched_sample_for_review.csv'),
                'unmatched_sample': str(self.folders['manual_review'] / 'unmatched_sample_for_review.csv')
            }
        }
        
        # Save report
        report_file = self.folders['reports'] / 'completion_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Completion report saved: {report_file}")
        return report
    
    def run_complete_pipeline(self, csc_file, seednet_file):
        """Run the complete matching pipeline."""
        self.logger.info("=== STARTING COMPLETE CSC-SEEDNET MATCHING PIPELINE ===")
        
        try:
            # Copy raw data
            csc_dest, seednet_dest = self.copy_raw_data(csc_file, seednet_file)
            
            # Load and prepare data
            csc_df, seednet_df = self.load_and_prepare_data(csc_dest, seednet_dest)
            
            # Perform fuzzy matching
            matched_df, unmatched_df = self.perform_fuzzy_matching(csc_df, seednet_df)
            
            # Analyze samples
            analysis_results = self.analyze_random_samples(matched_df, unmatched_df)
            
            # Create final dataset
            final_df, final_file = self.create_final_dataset(matched_df, unmatched_df)
            
            # Generate completion report
            report = self.generate_completion_report(final_df, analysis_results, final_file)
            
            self.logger.info("=== PIPELINE COMPLETED SUCCESSFULLY ===")
            return final_df, report
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise

def main():
    """Main function to run the matching pipeline."""
    try:
        # Initialize matcher
        matcher = CSCSeedNetMatcher()
        
        # Define input files
        csc_file = "consolidated_data/csc_master_20250704_070304.csv"
        seednet_file = "Seednet_Data_Tables_Scraped_20250726.csv"
        
        # Run complete pipeline
        final_df, report = matcher.run_complete_pipeline(csc_file, seednet_file)
        
        print(f"\nMatching pipeline completed successfully!")
        print(f"Total varieties processed: {len(final_df)}")
        print(f"Matched varieties: {report['matched_varieties']}")
        print(f"Unmatched varieties: {report['unmatched_varieties']}")
        print(f"Match rate: {report['match_rate']:.1f}%")
        
    except Exception as e:
        print(f"Pipeline failed: {e}")

if __name__ == "__main__":
    main() 