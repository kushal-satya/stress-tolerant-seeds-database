import pandas as pd
import json
import numpy as np
from pathlib import Path

# Create sample stress-tolerant seed database
def create_sample_database():
    """Create a sample database for the dashboard"""
    
    # Read the scraped ONION data
    onion_df = pd.read_csv('/Users/kushalkumar/Documents/pxd_sts_gujarat/seednet_ONION_20250804_180034.csv')
    
    # Create enhanced sample data
    sample_data = []
    
    # Add ONION varieties with enhanced attributes
    onion_varieties = [
        {
            'variety_name': 'Him Palam Shweta DPWO-1',
            'crop_type': 'ONION',
            'breeding_institution': 'CSIR-IHBT Palampur',
            'year_of_release': 2022,
            'stressors_tolerated': ['Drought', 'Temperature Stress'],
            'quality_traits': ['High Yield', 'Good Storage', 'White Color'],
            'recommended_states': ['Himachal Pradesh', 'Uttarakhand'],
            'confidence_level': 'High',
            'data_completeness_score': 0.85,
            'quality_flag': 'GOOD',
            'approval_status': 'Released',
            'maturity_days': 110,
            'parent_lines': ['Selection from local germplasm'],
            'genetic_markers': [],
            'special_features': ['Cold tolerance', 'High altitude adaptation'],
            'agro_climatic_zones': ['Hill zones'],
            'adaptation_zones': ['Temperate'],
            'data_sources': ['Seednet Portal', 'CSIR-IHBT']
        },
        {
            'variety_name': 'Bhima Shakti',
            'crop_type': 'ONION',
            'breeding_institution': 'NRCOG Pune',
            'year_of_release': 2019,
            'stressors_tolerated': ['Pink Root Rot', 'Thrips', 'Storage Rot'],
            'quality_traits': ['Disease Resistance', 'Export Quality', 'Uniform Bulbs'],
            'recommended_states': ['Maharashtra', 'Karnataka', 'Gujarat'],
            'confidence_level': 'High',
            'data_completeness_score': 0.92,
            'quality_flag': 'EXCELLENT',
            'approval_status': 'Released',
            'maturity_days': 115,
            'parent_lines': ['Bhima Super x Local selection'],
            'genetic_markers': ['SSR markers for disease resistance'],
            'special_features': ['Pink root rot tolerance', 'Export quality'],
            'agro_climatic_zones': ['Semi-arid', 'Sub-humid'],
            'adaptation_zones': ['Central India'],
            'data_sources': ['NRCOG', 'AICRP reports']
        }
    ]
    
    # Add more crop varieties
    additional_varieties = [
        {
            'variety_name': 'PUSA Basmati 1718',
            'crop_type': 'RICE',
            'breeding_institution': 'IARI Delhi',
            'year_of_release': 2018,
            'stressors_tolerated': ['Bacterial Blight', 'Blast', 'Water Stress'],
            'quality_traits': ['Aromatic', 'Long Grain', 'Export Quality'],
            'recommended_states': ['Punjab', 'Haryana', 'Uttar Pradesh'],
            'confidence_level': 'High',
            'data_completeness_score': 0.95,
            'quality_flag': 'EXCELLENT',
            'approval_status': 'Released',
            'maturity_days': 120,
            'parent_lines': ['Pusa 1121 x Local Basmati'],
            'genetic_markers': ['Xa21 gene for bacterial blight'],
            'special_features': ['Disease resistance', 'Premium quality'],
            'agro_climatic_zones': ['Indo-Gangetic Plains'],
            'adaptation_zones': ['Northern India'],
            'data_sources': ['IARI', 'DRR', 'AICRIP']
        },
        {
            'variety_name': 'Gujarat Chickpea 4',
            'crop_type': 'CHICKPEA',
            'breeding_institution': 'AAU Anand',
            'year_of_release': 2020,
            'stressors_tolerated': ['Wilt', 'Dry Root Rot', 'Heat Stress'],
            'quality_traits': ['High Protein', 'Bold Seed', 'Machine Harvestable'],
            'recommended_states': ['Gujarat', 'Rajasthan', 'Madhya Pradesh'],
            'confidence_level': 'High',
            'data_completeness_score': 0.88,
            'quality_flag': 'GOOD',
            'approval_status': 'Released',
            'maturity_days': 95,
            'parent_lines': ['Gujarat Gram 1 x ICCV 2'],
            'genetic_markers': ['QTL for wilt resistance'],
            'special_features': ['Wilt resistance', 'Heat tolerance'],
            'agro_climatic_zones': ['Semi-arid'],
            'adaptation_zones': ['Western India'],
            'data_sources': ['AAU', 'ICRISAT', 'AICRP']
        },
        {
            'variety_name': 'HD 3226',
            'crop_type': 'WHEAT',
            'breeding_institution': 'IARI Delhi',
            'year_of_release': 2017,
            'stressors_tolerated': ['Yellow Rust', 'Brown Rust', 'Heat Stress'],
            'quality_traits': ['High Yield', 'Good Chapati Quality', 'Semi-dwarf'],
            'recommended_states': ['Punjab', 'Haryana', 'Western UP'],
            'confidence_level': 'High',
            'data_completeness_score': 0.90,
            'quality_flag': 'EXCELLENT',
            'approval_status': 'Released',
            'maturity_days': 145,
            'parent_lines': ['HD 2967 x DBW 16'],
            'genetic_markers': ['Yr genes for rust resistance'],
            'special_features': ['Multiple rust resistance', 'Heat tolerance'],
            'agro_climatic_zones': ['Indo-Gangetic Plains'],
            'adaptation_zones': ['Northern India'],
            'data_sources': ['IARI', 'CIMMYT', 'AICWIP']
        },
        {
            'variety_name': 'Gujarat Cotton 27',
            'crop_type': 'COTTON',
            'breeding_institution': 'AAU Anand',
            'year_of_release': 2019,
            'stressors_tolerated': ['Bollworm', 'Jassid', 'Drought'],
            'quality_traits': ['High Lint', 'Medium Staple', 'Bt Technology'],
            'recommended_states': ['Gujarat', 'Maharashtra', 'Rajasthan'],
            'confidence_level': 'Medium',
            'data_completeness_score': 0.82,
            'quality_flag': 'GOOD',
            'approval_status': 'Released',
            'maturity_days': 180,
            'parent_lines': ['G.Cot 23 x Local selection'],
            'genetic_markers': ['Cry genes for bollworm'],
            'special_features': ['Bt technology', 'Drought tolerance'],
            'agro_climatic_zones': ['Semi-arid'],
            'adaptation_zones': ['Western India'],
            'data_sources': ['AAU', 'CICR', 'AICCIP']
        }
    ]
    
    # Combine all varieties
    all_varieties = onion_varieties + additional_varieties
    
    # Convert to DataFrame
    df = pd.DataFrame(all_varieties)
    
    # Convert list columns to JSON strings for storage
    list_columns = ['stressors_tolerated', 'quality_traits', 'recommended_states', 
                   'parent_lines', 'genetic_markers', 'special_features', 
                   'agro_climatic_zones', 'adaptation_zones', 'data_sources']
    
    for col in list_columns:
        df[col] = df[col].apply(json.dumps)
    
    return df

if __name__ == "__main__":
    # Create the database
    df = create_sample_database()
    
    # Save to the dashboard data directory
    output_dir = Path('/Users/kushalkumar/Documents/pxd_sts_gujarat/stress_tolerant_seeds_db/data/final')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as CSV
    df.to_csv(output_dir / 'stress_tolerant_seed_database.csv', index=False)
    
    print(f"Sample database created with {len(df)} varieties")
    print(f"Saved to: {output_dir / 'stress_tolerant_seed_database.csv'}")
    print("\nSample varieties:")
    for i, row in df.iterrows():
        print(f"- {row['variety_name']} ({row['crop_type']})")
