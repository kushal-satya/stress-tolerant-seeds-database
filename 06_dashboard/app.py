# Filename: app.py
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-08-01
# Last Modified: 2025-08-01
# Description: Interactive Streamlit dashboard for exploring the stress-tolerant seed variety database.

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import sqlite3
from pathlib import Path
import re
from typing import List, Dict, Optional
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Stress-Tolerant Seed Varieties Database",
    page_icon="seed",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2E8B57;
    }
    .filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .variety-card {
        border: 1px solid #ddd;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

class SeedVarietyDashboard:
    def __init__(self):
        self.data_dir = Path("data/final")
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Load the final database"""
        csv_file = self.data_dir / "stress_tolerant_seed_database.csv"
        sqlite_file = self.data_dir / "stress_tolerant_seed_database.db"
        
        try:
            if sqlite_file.exists():
                # Load from SQLite
                conn = sqlite3.connect(sqlite_file)
                self.df = pd.read_sql_query("SELECT * FROM stress_tolerant_varieties", conn)
                conn.close()
            elif csv_file.exists():
                # Load from CSV
                self.df = pd.read_csv(csv_file)
            else:
                st.error("No database found. Please run the pipeline first.")
                return
            
            # Parse JSON fields
            json_fields = ['stressors_tolerated', 'quality_traits', 'genetic_markers', 
                          'parent_lines', 'adaptation_zones', 'recommended_states', 
                          'agro_climatic_zones', 'special_features', 'data_sources']
            
            for field in json_fields:
                if field in self.df.columns:
                    self.df[field] = self.df[field].apply(self.parse_json_field)
            
            st.success(f"Loaded {len(self.df)} seed varieties")
            
        except Exception as e:
            st.error(f"Error loading data: {e}")
    
    def parse_json_field(self, field_value):
        """Parse JSON field values"""
        if pd.isna(field_value) or field_value == '':
            return []
        
        try:
            if isinstance(field_value, str):
                return json.loads(field_value)
            elif isinstance(field_value, list):
                return field_value
            else:
                return []
        except:
            return []
    
    def render_header(self):
        """Render the main header"""
        st.markdown('<h1 class="main-header">Stress-Tolerant Seed Varieties Database</h1>', 
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <p style="font-size: 1.1rem; color: #666;">
                Comprehensive database of stress-tolerant seed varieties for Indian agriculture
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_summary_metrics(self, filtered_df):
        """Render summary metrics"""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Varieties", len(filtered_df))
        
        with col2:
            unique_crops = filtered_df['crop_type'].nunique()
            st.metric("Crop Types", unique_crops)
        
        with col3:
            unique_institutions = filtered_df['breeding_institution'].nunique()
            st.metric("Institutions", unique_institutions)
        
        with col4:
            stress_tolerant = len(filtered_df[filtered_df['stressors_tolerated'].apply(len) > 0])
            st.metric("Stress Tolerant", stress_tolerant)
        
        with col5:
            avg_completeness = filtered_df['data_completeness_score'].mean()
            st.metric("Avg Data Quality", f"{avg_completeness:.2f}")
    
    def render_filters(self):
        """Render filter controls"""
        st.sidebar.markdown("## Filters")
        
        filters = {}
        
        # Crop type filter
        crop_types = ['All'] + sorted(self.df['crop_type'].dropna().unique().tolist())
        filters['crop_type'] = st.sidebar.selectbox("Crop Type", crop_types)
        
        # Stress tolerance filter
        all_stresses = set()
        for stresses in self.df['stressors_tolerated']:
            if isinstance(stresses, list):
                all_stresses.update(stresses)
        
        stress_options = ['All'] + sorted(list(all_stresses))
        filters['stress_tolerance'] = st.sidebar.selectbox("Stress Tolerance", stress_options)
        
        # State filter
        all_states = set()
        for states in self.df['recommended_states']:
            if isinstance(states, list):
                all_states.update(states)
        
        state_options = ['All'] + sorted(list(all_states))
        filters['state'] = st.sidebar.selectbox("Recommended State", state_options)
        
        # Institution filter
        institutions = ['All'] + sorted(self.df['breeding_institution'].dropna().unique().tolist())
        filters['institution'] = st.sidebar.selectbox("Breeding Institution", institutions)
        
        # Year range filter
        year_min = int(self.df['year_of_release'].min()) if not pd.isna(self.df['year_of_release'].min()) else 1990
        year_max = int(self.df['year_of_release'].max()) if not pd.isna(self.df['year_of_release'].max()) else 2025
        
        filters['year_range'] = st.sidebar.slider(
            "Release Year Range", 
            min_value=year_min, 
            max_value=year_max, 
            value=(year_min, year_max)
        )
        
        # Data quality filter
        quality_options = ['All'] + sorted(self.df['quality_flag'].dropna().unique().tolist())
        filters['quality'] = st.sidebar.selectbox("Data Quality", quality_options)
        
        return filters
    
    def apply_filters(self, filters):
        """Apply filters to the dataframe"""
        filtered_df = self.df.copy()
        
        if filters['crop_type'] != 'All':
            filtered_df = filtered_df[filtered_df['crop_type'] == filters['crop_type']]
        
        if filters['stress_tolerance'] != 'All':
            filtered_df = filtered_df[
                filtered_df['stressors_tolerated'].apply(
                    lambda x: filters['stress_tolerance'] in x if isinstance(x, list) else False
                )
            ]
        
        if filters['state'] != 'All':
            filtered_df = filtered_df[
                filtered_df['recommended_states'].apply(
                    lambda x: filters['state'] in x if isinstance(x, list) else False
                )
            ]
        
        if filters['institution'] != 'All':
            filtered_df = filtered_df[filtered_df['breeding_institution'] == filters['institution']]
        
        # Year range filter
        year_mask = (
            (filtered_df['year_of_release'] >= filters['year_range'][0]) &
            (filtered_df['year_of_release'] <= filters['year_range'][1])
        ) | pd.isna(filtered_df['year_of_release'])
        filtered_df = filtered_df[year_mask]
        
        if filters['quality'] != 'All':
            filtered_df = filtered_df[filtered_df['quality_flag'] == filters['quality']]
        
        return filtered_df
    
    def render_visualizations(self, filtered_df):
        """Render data visualizations"""
        st.markdown("## Data Visualizations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Crop type distribution
            crop_counts = filtered_df['crop_type'].value_counts()
            if not crop_counts.empty:
                fig_crop = px.pie(
                    values=crop_counts.values,
                    names=crop_counts.index,
                    title="Distribution by Crop Type"
                )
                fig_crop.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_crop, use_container_width=True)
        
        with col2:
            # Release year trend
            year_counts = filtered_df['year_of_release'].value_counts().sort_index()
            if not year_counts.empty:
                fig_year = px.line(
                    x=year_counts.index,
                    y=year_counts.values,
                    title="Varieties Released by Year"
                )
                fig_year.update_xaxis(title="Year")
                fig_year.update_yaxis(title="Number of Varieties")
                st.plotly_chart(fig_year, use_container_width=True)
        
        # Stress tolerance analysis
        stress_data = []
        for _, row in filtered_df.iterrows():
            stresses = row['stressors_tolerated']
            if isinstance(stresses, list):
                for stress in stresses:
                    stress_data.append({'Variety': row['variety_name'], 'Stress': stress})
        
        if stress_data:
            stress_df = pd.DataFrame(stress_data)
            stress_counts = stress_df['Stress'].value_counts()
            
            fig_stress = px.bar(
                x=stress_counts.values,
                y=stress_counts.index,
                orientation='h',
                title="Stress Tolerance Distribution",
                labels={'x': 'Number of Varieties', 'y': 'Stress Type'}
            )
            st.plotly_chart(fig_stress, use_container_width=True)
        
        # Institution analysis
        inst_counts = filtered_df['breeding_institution'].value_counts().head(10)
        if not inst_counts.empty:
            fig_inst = px.bar(
                x=inst_counts.index,
                y=inst_counts.values,
                title="Top 10 Breeding Institutions"
            )
            fig_inst.update_xaxis(title="Institution", tickangle=45)
            fig_inst.update_yaxis(title="Number of Varieties")
            st.plotly_chart(fig_inst, use_container_width=True)
    
    def render_data_table(self, filtered_df):
        """Render searchable data table"""
        st.markdown("## Variety Database")
        
        # Search functionality
        search_term = st.text_input("Search varieties by name, institution, or characteristics:")
        
        if search_term:
            search_mask = (
                filtered_df['variety_name'].str.contains(search_term, case=False, na=False) |
                filtered_df['breeding_institution'].str.contains(search_term, case=False, na=False) |
                filtered_df['special_features'].astype(str).str.contains(search_term, case=False, na=False)
            )
            display_df = filtered_df[search_mask]
        else:
            display_df = filtered_df
        
        # Select columns to display
        display_columns = [
            'variety_name', 'crop_type', 'breeding_institution', 
            'year_of_release', 'stressors_tolerated', 'quality_traits',
            'recommended_states', 'confidence_level'
        ]
        
        available_columns = [col for col in display_columns if col in display_df.columns]
        
        # Format the dataframe for display
        display_data = display_df[available_columns].copy()
        
        # Convert list columns to readable strings
        list_columns = ['stressors_tolerated', 'quality_traits', 'recommended_states']
        for col in list_columns:
            if col in display_data.columns:
                display_data[col] = display_data[col].apply(
                    lambda x: ', '.join(x) if isinstance(x, list) else str(x)
                )
        
        st.dataframe(
            display_data,
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown(f"Showing {len(display_data)} of {len(filtered_df)} varieties")
    
    def render_variety_details(self, filtered_df):
        """Render detailed variety information"""
        st.markdown("## Variety Details")
        
        if len(filtered_df) == 0:
            st.warning("No varieties match the current filters.")
            return
        
        # Select variety for detailed view
        variety_names = filtered_df['variety_name'].dropna().unique()
        selected_variety = st.selectbox("Select a variety for detailed information:", variety_names)
        
        if selected_variety:
            variety_data = filtered_df[filtered_df['variety_name'] == selected_variety].iloc[0]
            
            # Display variety details in a card format
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### {variety_data['variety_name']}")
                
                # Basic information
                st.markdown("**Basic Information:**")
                info_items = [
                    ("Crop Type", variety_data.get('crop_type', 'Not specified')),
                    ("Breeding Institution", variety_data.get('breeding_institution', 'Not specified')),
                    ("Year of Release", variety_data.get('year_of_release', 'Not specified')),
                    ("Approval Status", variety_data.get('approval_status', 'Not specified')),
                    ("Maturity Days", variety_data.get('maturity_days', 'Not specified'))
                ]
                
                for label, value in info_items:
                    st.write(f"**{label}:** {value}")
                
                # Stress tolerance
                stresses = variety_data.get('stressors_tolerated', [])
                if isinstance(stresses, list) and stresses:
                    st.markdown("**Stress Tolerances:**")
                    for stress in stresses:
                        st.write(f"• {stress}")
                
                # Quality traits
                quality = variety_data.get('quality_traits', [])
                if isinstance(quality, list) and quality:
                    st.markdown("**Quality Traits:**")
                    for trait in quality:
                        st.write(f"• {trait}")
            
            with col2:
                # Additional information
                st.markdown("**Additional Details:**")
                
                # Recommended states
                states = variety_data.get('recommended_states', [])
                if isinstance(states, list) and states:
                    st.markdown("**Recommended States:**")
                    st.write(', '.join(states))
                
                # Parent lines
                parents = variety_data.get('parent_lines', [])
                if isinstance(parents, list) and parents:
                    st.markdown("**Parent Lines:**")
                    for parent in parents:
                        st.write(f"• {parent}")
                
                # Data quality
                st.markdown("**Data Quality:**")
                st.write(f"Confidence: {variety_data.get('confidence_level', 'Unknown')}")
                st.write(f"Completeness: {variety_data.get('data_completeness_score', 0):.2f}")
    
    def render_export_options(self, filtered_df):
        """Render data export options"""
        st.markdown("## Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Export to CSV"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"seed_varieties_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("Export Summary"):
                summary = self.generate_summary_report(filtered_df)
                st.download_button(
                    label="Download Summary",
                    data=summary,
                    file_name=f"variety_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        
        with col3:
            if st.button("Export JSON"):
                json_data = filtered_df.to_json(orient='records', indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=f"seed_varieties_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    def generate_summary_report(self, df):
        """Generate a summary report"""
        report = f"""
STRESS-TOLERANT SEED VARIETIES SUMMARY REPORT
Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERVIEW:
Total varieties: {len(df)}
Unique crops: {df['crop_type'].nunique()}
Unique institutions: {df['breeding_institution'].nunique()}

CROP DISTRIBUTION:
{df['crop_type'].value_counts().to_string()}

STRESS TOLERANCE SUMMARY:
Varieties with stress tolerance info: {len(df[df['stressors_tolerated'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)])}

TOP INSTITUTIONS:
{df['breeding_institution'].value_counts().head(10).to_string()}

DATA QUALITY:
Average completeness score: {df['data_completeness_score'].mean():.3f}
High quality records: {len(df[df['quality_flag'] == 'GOOD'])}
"""
        return report
    
    def run(self):
        """Main dashboard application"""
        if self.df is None:
            st.error("No data available. Please check if the database exists.")
            return
        
        # Render header
        self.render_header()
        
        # Render filters
        filters = self.render_filters()
        
        # Apply filters
        filtered_df = self.apply_filters(filters)
        
        # Render summary metrics
        self.render_summary_metrics(filtered_df)
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["Visualizations", "Data Table", "Variety Details", "Export"])
        
        with tab1:
            self.render_visualizations(filtered_df)
        
        with tab2:
            self.render_data_table(filtered_df)
        
        with tab3:
            self.render_variety_details(filtered_df)
        
        with tab4:
            self.render_export_options(filtered_df)
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.9rem;">
            <p>Stress-Tolerant Seed Varieties Database | Developed by kd475@cornell.edu</p>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main function to run the dashboard"""
    dashboard = SeedVarietyDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
