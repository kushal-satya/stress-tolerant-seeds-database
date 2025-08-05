# Filename: generate_final_database.py
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-08-01
# Last Modified: 2025-08-01
# Description: Generates the final structured database from enriched seed variety data.

import pandas as pd
import json
import os
import glob
import re
import configparser
from collections import Counter
import logging
from datetime import datetime
from pathlib import Path

class FinalDatabaseGenerator:
    """Generates the final structured database from enriched seed variety data."""
    
    def __init__(self, config_path='../config/config.ini'):
        """Initialize the database generator with configuration."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.setup_directories()
        
        # Configuration
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _load_config(self, config_path):
        """Load configuration from config file."""
        config = configparser.ConfigParser()
        config.read(config_path)
        return config
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_dir = self.config.get('PATHS', 'logs_dir', fallback='logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'final_database_generation_{self.timestamp}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_directories(self):
        """Setup required directories."""
        self.data_dir = self.config.get('PATHS', 'research_context_dir', fallback='data/research_context')
        self.output_dir = self.config.get('PATHS', 'final_dir', fallback='data/final')
        
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"Output directory: {self.output_dir}")

    def load_and_consolidate_data(self, data_dir):
        """
        Loads and consolidates all JSON data batches from the specified directory.
        """
        self.logger.info(f"--- Phase I: Data Consolidation and Initial Profiling ---")
        self.logger.info(f"Starting data consolidation from: {data_dir}")
        
        json_files = glob.glob(os.path.join(data_dir, 'batch_*_enriched.json'))
        if not json_files:
            self.logger.error("No batch files found. Please check the DATA_DIR path.")
            return pd.DataFrame()

        self.logger.info(f"Found {len(json_files)} batch files to process.")
        
        all_records = []
        for file_path in json_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Each file contains a list of records; extend the main list
                    all_records.extend(data)
            except json.JSONDecodeError:
                self.logger.warning(f"Could not decode JSON from {file_path}. Skipping.")
            except Exception as e:
                self.logger.error(f"Error reading {file_path}: {e}")

        if not all_records:
            self.logger.error("No records were loaded. Exiting.")
            return pd.DataFrame()

        # Normalize the nested JSON structure into a flat DataFrame
        df = pd.json_normalize(all_records)
        
        self.logger.info(f"Successfully consolidated {len(df)} records into a DataFrame.")
        return df

    def initial_data_profiling(self, df):
        """
        Performs an initial EDA on the DataFrame.
        """
        if df.empty:
            self.logger.warning("DataFrame is empty. Skipping profiling.")
            return

        self.logger.info("--- Initial Data Profiling ---")
        self.logger.info(f"DataFrame shape: {df.shape}")
        
        # Summarize column data types and missing values
        
        # Handle potential unhashable types (like lists) in columns for nunique()
        unique_values = {}
        for col in df.columns:
            try:
                unique_values[col] = df[col].nunique()
            except TypeError:
                unique_values[col] = "unhashable_list" # Mark columns with unhashable types

        profile = pd.DataFrame({
            'Dtype': df.dtypes,
            'Missing Values': df.isnull().sum(),
            'Missing (%)': (df.isnull().sum() / len(df)) * 100,
            'Unique Values': pd.Series(unique_values)
        })
        self.logger.info("Data Profile:\n" + profile.to_string())

        # Identify essential columns for variety identification
        essential_cols = [
            'original_data.variety_name', 'original_data.crop_type', 
            'original_data.approval_status', 'analysis_result.variety_identification.variety_name'
        ]
        self.logger.info(f"\nEssential columns for variety identification: {essential_cols}")
        for col in essential_cols:
            if col not in df.columns:
                self.logger.warning(f"Essential column '{col}' not found in DataFrame.")

        return profile

    def clean_and_standardize_data(self, df):
        """
        Cleans and standardizes the DataFrame.
        """
        self.logger.info(f"\n--- Phase II: Data Cleaning and Standardization ---")
        
        # Standardize Key Fields by applying functions only to string elements
        for col in df.select_dtypes(include=['object']).columns:
            # Use .apply() to handle mixed types gracefully.
            # It operates element-wise, so we can check the type.
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
            
            # Enforce consistent casing for specific fields
            if 'name' in col.lower() or 'crop' in col.lower():
                df[col] = df[col].apply(lambda x: x.title() if isinstance(x, str) else x)

        # Address Missing Data
        # For this analysis, we'll fill key categorical columns with 'Unknown'
        key_cols = [
            'original_data.variety_name', 'original_data.crop_type', 
            'original_data.approval_status', 'analysis_result.variety_identification.variety_name'
        ]
        for col in key_cols:
            if col in df.columns:
                df[col].fillna('Unknown', inplace=True)
                
        self.logger.info("Data cleaning and standardization complete.")
        return df

    def engineer_variety_features(self, df):
        """
        Engineers features from variety names to aid in similarity analysis.
        """
        self.logger.info(f"\n--- Phase III: Sophisticated Similarity Analysis and Deduplication ---")
        self.logger.info("Step 1: Engineering features from variety names...")
        
        # Use a more specific column for variety name if available
        variety_col = 'analysis_result.variety_identification.variety_name'
        if variety_col not in df.columns:
            variety_col = 'original_data.variety_name'

        def parse_variety_name(name):
            if not isinstance(name, str):
                return "Unknown", "Unknown", "Unknown", "Unknown"
            
            # General pattern: Crop Name (optional), Prefix (optional), Numeric ID (optional)
            # Example: Bitter Gourd C.v. DBGS-54
            
            # Extract numeric identifier first, as it's a strong key
            numeric_id_match = re.search(r'(\d+)', name)
            numeric_id = numeric_id_match.group(1) if numeric_id_match else "Unknown"
            
            # Extract prefix (typically uppercase letters followed by a hyphen)
            prefix_match = re.search(r'([A-Z]+)-', name)
            prefix = prefix_match.group(1) if prefix_match else "Unknown"

            # Extract abbreviation (e.g., c.v., var.)
            abbr_match = re.search(r'([cv]\.?[v]?\.?)', name, re.IGNORECASE)
            abbr = abbr_match.group(1) if abbr_match else "Unknown"

            # The crop name is usually at the beginning
            crop_name_match = re.match(r'^[A-Za-z\s]+', name)
            crop_name = crop_name_match.group(0).strip() if crop_name_match else "Unknown"
            
            return crop_name, prefix, numeric_id, abbr

        df[[
            'variety_features.crop_name', 'variety_features.prefix',
            'variety_features.numeric_id', 'variety_features.abbreviation'
        ]] = df[variety_col].apply(lambda x: pd.Series(parse_variety_name(x)))
        
        self.logger.info("Feature engineering complete.")
        return df

    def analyze_duplicates(self, df):
        """
        Analyzes and categorizes duplicates based on agronomic rules.
        """
        self.logger.info("Step 2 & 3: Analyzing duplicates with agronomic intelligence...")
        df['duplicate_analysis.category'] = 'Unique'
        df['duplicate_analysis.match_id'] = -1
        
        # Use a more reliable column for grouping
        grouping_col = 'original_data.variety_standardized'
        if grouping_col not in df.columns:
            grouping_col = 'analysis_result.variety_identification.variety_name'

        grouped = df.groupby(grouping_col)
        
        match_id_counter = 0
        categories = Counter()

        for name, group in grouped:
            if len(group) > 1:
                # All items in this group are at least related.
                indices = group.index
                df.loc[indices, 'duplicate_analysis.match_id'] = match_id_counter

                # Rule-based classification
                # Check for exact matches first
                if group.duplicated(subset=['variety_features.prefix', 'variety_features.numeric_id'], keep=False).all():
                     df.loc[indices, 'duplicate_analysis.category'] = 'Exact Match'
                     categories['Exact Match'] += len(indices)
                else:
                    # If prefixes match but numeric IDs differ, they are related but distinct
                    is_related_distinct = False
                    if len(group['variety_features.prefix'].unique()) == 1 and len(group['variety_features.numeric_id'].unique()) > 1:
                         is_related_distinct = True

                    if is_related_distinct:
                        df.loc[indices, 'duplicate_analysis.category'] = 'Related but Distinct'
                        categories['Related but Distinct'] += len(indices)
                    else:
                        # High similarity but not exact match -> Typo/Formatting
                        df.loc[indices, 'duplicate_analysis.category'] = 'Typo/Formatting Issue'
                        categories['Typo/Formatting Issue'] += len(indices)

                match_id_counter += 1

        unique_count = len(df[df['duplicate_analysis.category'] == 'Unique'])
        categories['Unique'] = unique_count
        
        self.logger.info(f"Duplicate analysis complete. Summary: {categories}")
        return df, dict(categories)

    def consolidate_duplicates(self, df):
        """
        Consolidates duplicate rows based on the analysis.
        """
        self.logger.info("Step 4: Merging and consolidating duplicates...")
        
        # For 'Exact Match' and 'Typo/Formatting Issue', we keep the first entry
        # and discard the others. We are not dropping 'Related but Distinct' as they are unique varieties.
        
        # Get indices of rows to be dropped
        rows_to_drop = df[
            (df['duplicate_analysis.category'].isin(['Exact Match', 'Typo/Formatting Issue'])) &
            (df.duplicated('duplicate_analysis.match_id', keep='first'))
        ].index
        
        df_consolidated = df.drop(rows_to_drop)
        
        self.logger.info(f"Consolidated DataFrame. Original rows: {len(df)}, Final rows: {len(df_consolidated)}")
        return df_consolidated

    def generate_final_schema(self, df):
        """
        Generates the final database schema with standardized column names.
        """
        self.logger.info("--- Phase V: Final Schema Generation ---")
        
        # Define the final schema
        final_schema = {
            'variety_id': 'Unique identifier for each variety',
            'variety_name': 'Standardized variety name',
            'crop_type': 'Type of crop',
            'approval_status': 'Regulatory approval status',
            'stress_tolerance_drought': 'Drought tolerance level (high/medium/low/unknown)',
            'stress_tolerance_heat': 'Heat tolerance level',
            'stress_tolerance_salinity': 'Salinity tolerance level',
            'stress_tolerance_flood': 'Flood tolerance level',
            'stress_tolerance_disease': 'Disease resistance level',
            'stress_tolerance_pest': 'Pest resistance level',
            'genetic_markers': 'Available genetic markers',
            'qtl_information': 'QTL mapping information',
            'yield_potential': 'Yield performance data',
            'maturity_days': 'Days to maturity',
            'development_institution': 'Breeding institution',
            'principal_breeder': 'Principal breeder/scientist',
            'testing_locations': 'Trial locations',
            'commercial_availability': 'Commercial availability status',
            'evidence_quality_score': 'Evidence quality score (1-10)',
            'peer_reviewed_sources': 'Number of peer-reviewed sources',
            'total_sources': 'Total number of sources',
            'processing_timestamp': 'Data processing timestamp'
        }
        
        # Create final DataFrame with standardized columns
        final_df = pd.DataFrame()
        
        # Map existing columns to final schema
        column_mapping = {
            'original_data.variety_name': 'variety_name',
            'original_data.crop_type': 'crop_type',
            'original_data.approval_status': 'approval_status',
            'analysis_result.stress_tolerance_profile.drought_tolerance.tolerance_level': 'stress_tolerance_drought',
            'analysis_result.stress_tolerance_profile.heat_tolerance.tolerance_level': 'stress_tolerance_heat',
            'analysis_result.stress_tolerance_profile.salinity_tolerance.tolerance_level': 'stress_tolerance_salinity',
            'analysis_result.stress_tolerance_profile.flood_tolerance.tolerance_level': 'stress_tolerance_flood',
            'analysis_result.stress_tolerance_profile.disease_resistance.tolerance_level': 'stress_tolerance_disease',
            'analysis_result.stress_tolerance_profile.pest_resistance.tolerance_level': 'stress_tolerance_pest',
            'analysis_result.genetic_and_molecular_profile.molecular_markers': 'genetic_markers',
            'analysis_result.genetic_and_molecular_profile.qtl_mapping': 'qtl_information',
            'analysis_result.agronomic_performance.yield_data': 'yield_potential',
            'analysis_result.agronomic_performance.maturity_days': 'maturity_days',
            'analysis_result.research_and_development.development_institution': 'development_institution',
            'analysis_result.research_and_development.breeder_information': 'principal_breeder',
            'analysis_result.research_and_development.testing_locations': 'testing_locations',
            'analysis_result.commercial_availability.seed_availability': 'commercial_availability',
            'analysis_result.evidence_quality_assessment.reliability_score': 'evidence_quality_score',
            'analysis_result.evidence_quality_assessment.peer_reviewed_sources': 'peer_reviewed_sources',
            'analysis_result.evidence_quality_assessment.total_sources': 'total_sources',
            'enrichment_timestamp': 'processing_timestamp'
        }
        
        # Map columns that exist in the source DataFrame
        for source_col, target_col in column_mapping.items():
            if source_col in df.columns:
                final_df[target_col] = df[source_col]
            else:
                final_df[target_col] = 'Unknown'
        
        # Add variety_id
        final_df['variety_id'] = range(1, len(final_df) + 1)
        final_df['variety_id'] = final_df['variety_id'].apply(lambda x: f"STS_{x:06d}")
        
        # Reorder columns to put variety_id first
        cols = ['variety_id'] + [col for col in final_df.columns if col != 'variety_id']
        final_df = final_df[cols]
        
        self.logger.info(f"Final schema generated with {len(final_df.columns)} columns")
        return final_df, final_schema

    def generate_summary_report(self, original_df, final_df, analysis_summary):
        """
        Generates a summary report of the analysis.
        """
        self.logger.info(f"\n--- Summary Report ---")
        self.logger.info(f"Initial State:")
        self.logger.info(f"  - Total Batches Processed: {len(glob.glob(os.path.join(self.data_dir, 'batch_*_enriched.json')))}")
        self.logger.info(f"  - Initial Row Count: {len(original_df)}")
        
        self.logger.info(f"\nCleaning and Standardization:")
        self.logger.info(f"  - Standardized string columns (whitespace, casing).")
        self.logger.info(f"  - Handled missing data in key identifier columns.")

        self.logger.info(f"\nSimilarity Analysis Logic:")
        self.logger.info(f"  - Engineered features: crop name, prefix, numeric ID from variety names.")
        self.logger.info(f"  - Applied rule-based logic to categorize duplicates.")

        self.logger.info(f"\nDuplicate Analysis Summary:")
        for category, count in analysis_summary.items():
            self.logger.info(f"  - {category}: {count}")

        self.logger.info(f"\nFinal Dataset:")
        self.logger.info(f"  - Final Row Count: {len(final_df)}")
        
        # Save summary report
        report = {
            'timestamp': datetime.now().isoformat(),
            'initial_row_count': len(original_df),
            'final_row_count': len(final_df),
            'duplicate_analysis': analysis_summary,
            'processing_metadata': {
                'data_source': self.data_dir,
                'output_location': self.output_dir,
                'processing_version': '1.0'
            }
        }
        
        report_path = os.path.join(self.output_dir, f'summary_report_{self.timestamp}.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)
        
        self.logger.info(f"Summary report saved to: {report_path}")

    def run_complete_pipeline(self):
        """
        Main function to execute the complete database generation pipeline.
        """
        self.logger.info("=== STARTING FINAL DATABASE GENERATION PIPELINE ===")
        
        try:
            # Phase I: Load and consolidate data
            master_df = self.load_and_consolidate_data(self.data_dir)
            if master_df.empty:
                self.logger.error("No data loaded. Exiting.")
                return None

            initial_profile = self.initial_data_profiling(master_df.copy())
            profile_path = os.path.join(self.output_dir, f'initial_data_profile_{self.timestamp}.csv')
            initial_profile.to_csv(profile_path)
            self.logger.info(f"Initial data profile saved to: {profile_path}")

            # Phase II: Clean and standardize
            cleaned_df = self.clean_and_standardize_data(master_df.copy())

            # Phase III: Feature engineering and duplicate analysis
            featured_df = self.engineer_variety_features(cleaned_df.copy())
            analyzed_df, analysis_summary = self.analyze_duplicates(featured_df.copy())
            
            analysis_report_path = os.path.join(self.output_dir, f'duplicates_analysis_{self.timestamp}.json')
            with open(analysis_report_path, 'w') as f:
                json.dump(analysis_summary, f, indent=4)
            self.logger.info(f"Duplicate analysis summary saved to: {analysis_report_path}")

            # Phase IV: Consolidate duplicates
            final_df = self.consolidate_duplicates(analyzed_df.copy())
            
            # Phase V: Generate final schema
            final_schema_df, final_schema = self.generate_final_schema(final_df)
            
            # Save final database
            final_dataset_path = os.path.join(self.output_dir, f'stress_tolerant_seed_database_{self.timestamp}.csv')
            final_schema_df.to_csv(final_dataset_path, index=False)
            self.logger.info(f"Final database saved to: {final_dataset_path}")
            
            # Save schema documentation
            schema_path = os.path.join(self.output_dir, f'database_schema_{self.timestamp}.json')
            with open(schema_path, 'w') as f:
                json.dump(final_schema, f, indent=4)
            self.logger.info(f"Database schema saved to: {schema_path}")

            # Generate summary report
            self.generate_summary_report(master_df, final_schema_df, analysis_summary)
            
            self.logger.info("=== FINAL DATABASE GENERATION COMPLETED SUCCESSFULLY ===")
            return final_schema_df
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise

def main():
    """Main function to run the final database generation."""
    try:
        # Initialize generator
        generator = FinalDatabaseGenerator()
        
        # Run complete pipeline
        final_df = generator.run_complete_pipeline()
        
        if final_df is not None:
            print(f"\nFinal database generation completed successfully!")
            print(f"Final database contains {len(final_df)} varieties")
            print(f"Database saved to: {generator.output_dir}")
        else:
            print("Database generation failed")
            
    except Exception as e:
        print(f"Database generation failed: {e}")

if __name__ == "__main__":
    main() 