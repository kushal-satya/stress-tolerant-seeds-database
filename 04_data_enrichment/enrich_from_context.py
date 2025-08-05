# Filename: enrich_from_context.py
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-08-01
# Last Modified: 2025-08-01
# Description: Enriches seed variety data using compiled context files and LLM analysis.

#!/usr/bin/env python3
"""
Enhancement of data in the and outputs specficic data JSON format
"""

import sys
import os
import json
import time
import logging
import pandas as pd
import google.generativeai as genai
import configparser
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import traceback
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from googleapiclient.discovery import build
import requests
from scholarly import scholarly
import random

class ContextEnricher:
    """

    """
    
    def __init__(self, config_path='../config/config.ini'):
        """Initialize the enhanced pipeline"""
        
        self.session_start = datetime.now()
        self.config = self._load_config(config_path)
        
        self.setup_logging()
        self.setup_gemini_api()
        self.setup_directories()
        
        # Processing statistics
        self.stats = {
            "total_varieties_loaded": 0,
            "varieties_processed": 0,
            "successful_enrichments": 0,
            "failed_enrichments": 0,
            "total_search_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "google_scholar_queries": 0,
            "post_2008_results": 0,
            "total_processing_time": 0,
            "api_calls_made": 0,
            "errors": []
        }
        
        # Rate limiting
        self.last_api_call = 0
        self.min_delay = 1.0  # 1 second between API calls
        self.scholar_delay = 2.0  # 2 seconds between Scholar queries
        
        print(" Enhanced CSC-Seednet pipeline initialized successfully!")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration with error handling"""
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            
            # Convert config to dict format
            config_dict = {}
            for section in config.sections():
                config_dict[section] = dict(config[section])
            
            print(f" Configuration loaded from {config_path}")
            return config_dict
        except Exception as e:
            raise Exception(f"💥 Failed to load config from {config_path}: {e}")

    def setup_logging(self):
        """Setup comprehensive logging system"""
        log_dir = Path(self.config.get('PATHS', {}).get('logs_dir', 'logs'))
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"enhanced_csc_seednet_{self.session_start.strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("EnhancedCSCSeednetPipeline")
        self.logger.info(" Enhanced logging system configured")

    def setup_gemini_api(self):
        """Configure Gemini API for pro mode analysis"""
        try:
            api_key = self.config.get("API_KEYS", {}).get("gemini_api_key")
            if not api_key:
                raise Exception("No Gemini API key found in config")
            
            genai.configure(api_key=api_key)
            # Use pro model for enhanced analysis
            model_name = self.config.get("SETTINGS", {}).get("gemini_model", "gemini-2.5-flash")
            self.model = genai.GenerativeModel(model_name)
            
            self.logger.info(f"🔑 Gemini API configured with pro model: {model_name}")
            print(f"🔑 Gemini Pro API ready: {model_name}")
            
        except Exception as e:
            raise Exception(f"💥 Failed to setup Gemini API: {e}")

    def setup_directories(self):
        """Setup required directories"""
        base_dir = Path(self.config.get('PATHS', {}).get('research_context_dir', 'data/research_context'))
        self.dirs = {
            "logs": Path(self.config.get('PATHS', {}).get('logs_dir', 'logs')),
            "enhanced_data_200": base_dir / "enhanced_data_200",
            "raw_data_200": base_dir / "raw_data_200",
            "processed_batches_200": base_dir / "processed_batches_200",
            "metadata": base_dir / "metadata",
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    def rate_limit(self, delay_type: str = "api"):
        """Rate limiting for API calls"""
        current_time = time.time()
        if delay_type == "scholar":
            delay = self.scholar_delay
        else:
            delay = self.min_delay
        
        time_since_last = current_time - self.last_api_call
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_api_call = time.time()

    def generate_pro_analysis_prompt(self) -> str:
        """Generate enhanced analysis prompt for pro mode Gemini"""
        return """
You are an expert agricultural research analyst with advanced capabilities in stress-tolerant crop variety analysis. You have access to comprehensive search results including Google Scholar publications, government databases, and scientific literature.

MISSION: Analyze ALL search results and extract comprehensive information about this seed variety's stress tolerance, genetic characteristics, and commercial viability.

ENHANCED ANALYSIS REQUIREMENTS:

1. **Stress Tolerance Profile (CRITICAL):**
   - Drought tolerance: Level (high/medium/low/unknown), mechanisms, QTL information
   - Heat tolerance: Temperature thresholds, heat shock proteins, physiological adaptations
   - Salinity tolerance: Salt concentration tolerance, ion exclusion mechanisms
   - Flood tolerance: Waterlogging duration, anaerobic stress response
   - Submergence tolerance: Underwater survival time, SUB1 gene presence
   - Disease resistance: Specific pathogens, resistance genes, field efficacy
   - Pest resistance: Target insects, Bt genes, IPM compatibility

2. **Genetic and Molecular Profile:**
   - QTL mapping results and chromosomal locations
   - Molecular markers (SSR, SNP, CAPS) for trait selection
   - Gene sequences and functional analysis
   - Genomic breeding applications
   - DNA fingerprinting data

3. **Agronomic Performance:**
   - Yield performance across environments and stress conditions
   - Maturity duration and growth characteristics
   - Fertilizer response and nutrient use efficiency
   - Water use efficiency and irrigation requirements

4. **Research and Development:**
   - Development institution and breeding program
   - Principal investigators and breeding timeline
   - Testing locations and trial results
   - Publication history and citation analysis

5. **Commercial Availability:**
   - Seed production and distribution networks
   - KVK and NSC availability status
   - State seed corporation partnerships
   - Farmer adoption rates and feedback

6. **Evidence Quality Assessment:**
   - Publication quality (peer-reviewed vs. reports)
   - Sample size and experimental design quality
   - Replication across locations and years
   - Independent validation studies
   - Overall reliability score (1-10)

POST-2008 FILTERING: Prioritize information from 2008 onwards. Clearly mark older references as historical context.

OUTPUT FORMAT:
Return a comprehensive JSON object with this structure:

{
  "variety_analysis": {
    "variety_name": "extracted name",
    "crop_type": "specific crop",
    "overall_assessment": "comprehensive variety assessment"
  },
  "stress_tolerance_profile": {
    "drought_tolerance": {
      "tolerance_level": "high/medium/low/unknown",
      "mechanisms": "physiological and molecular mechanisms",
      "qtl_information": "QTL details if available",
      "evidence_sources": ["list of supporting sources"],
      "technical_details": "detailed technical information"
    },
    "heat_tolerance": { ... similar structure ... },
    "salinity_tolerance": { ... similar structure ... },
    "flood_tolerance": { ... similar structure ... },
    "submergence_tolerance": { ... similar structure ... },
    "disease_resistance": { ... similar structure ... },
    "pest_resistance": { ... similar structure ... },
    "overall_stress_tolerance": "yes/no/partial",
    "key_stress_attributes": ["list of main stress tolerances"]
  },
  "genetic_and_molecular_profile": {
    "qtl_mapping": "QTL information",
    "molecular_markers": "marker information",
    "genetic_markers": "specific genetic markers",
    "genomic_data": "genome-wide analysis results",
    "gene_sequences": "relevant gene information"
  },
  "agronomic_performance": {
    "yield_data": "yield performance information",
    "maturity_days": "days to maturity",
    "growth_characteristics": "plant growth traits",
    "environmental_adaptation": "adaptation information",
    "input_requirements": "fertilizer and water needs"
  },
  "research_and_development": {
    "development_institution": "breeding institution",
    "breeder_information": "principal breeder/scientist",
    "breeding_program": "breeding methodology",
    "testing_locations": "trial locations",
    "development_timeline": "breeding timeline"
  },
  "commercial_availability": {
    "seed_availability": "commercial availability status",
    "distribution_networks": "seed distribution information",
    "kvk_availability": "KVK seed availability",
    "farmer_adoption": "adoption rates and feedback"
  },
  "evidence_quality_assessment": {
    "total_sources": number_of_sources,
    "peer_reviewed_sources": number_of_peer_reviewed,
    "government_sources": number_of_government_sources,
    "reliability_score": score_1_to_10,
    "overall_evidence_quality": "high/medium/low",
    "evidence_gaps": "areas lacking evidence"
  },
  "comprehensive_summary": "detailed paragraph summarizing all findings",
  "reference_links": ["top 10 most relevant links"],
  "post_2008_content_percentage": percentage_of_recent_content
}

CRITICAL REQUIREMENTS:
- Extract ALL relevant information from search results
- Prioritize peer-reviewed scientific publications
- Cross-reference information across multiple sources
- Clearly distinguish between confirmed facts and preliminary findings
- Provide specific technical details rather than general statements
- Include quantitative data wherever available
- Mark uncertainty levels for different claims

Analyze the provided search results comprehensively and return the complete structured analysis.
"""

    def analyze_with_pro_gemini(self, variety_data: Dict[str, Any], search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze variety using pro mode Gemini with comprehensive search results"""
        try:
            self.rate_limit("api")
            
            # Prepare comprehensive context
            search_context = {
                "variety_information": variety_data,
                "search_results": search_results,
                "total_queries": len(search_results),
                "successful_queries": len([r for r in search_results if 'error' not in r]),
                "google_scholar_results": [r for r in search_results if r.get('search_type') == 'google_scholar'],
                "google_search_results": [r for r in search_results if r.get('search_type') == 'google_search']
            }
            
            prompt = self.generate_pro_analysis_prompt()
            
            # Create comprehensive input for Gemini Pro
            full_prompt = f"""
{prompt}

VARIETY TO ANALYZE:
{json.dumps(variety_data, indent=2)}

COMPREHENSIVE SEARCH RESULTS:
{json.dumps(search_context, indent=2)}

Please analyze this variety comprehensively using all available search results and return the structured JSON analysis.
"""
            
            response = self.model.generate_content(full_prompt)
            self.stats["api_calls_made"] += 1
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            analysis_result = json.loads(response_text)
            
            # Add metadata
            analysis_result["processing_metadata"] = {
                "analysis_timestamp": datetime.now().isoformat(),
                "gemini_model": self.config.get("SETTINGS", {}).get("gemini_model", "gemini-2.5-flash"),
                "total_search_queries": len(search_results),
                "successful_queries": len([r for r in search_results if 'error' not in r]),
                "processing_version": "enhanced_csc_seednet_v1.0"
            }
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Pro Gemini analysis failed: {e}")
            return {
                "error": str(e),
                "variety_name": variety_data.get('variety_name', 'Unknown'),
                "processing_timestamp": datetime.now().isoformat()
            }

    def load_context_files(self, context_dir: str) -> List[Dict[str, Any]]:
        """Load context files from the research context directory"""
        context_files = []
        context_path = Path(context_dir)
        
        if not context_path.exists():
            self.logger.warning(f"Context directory not found: {context_dir}")
            return context_files
        
        # Find all JSON context files
        json_files = list(context_path.glob("*.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    context_data = json.load(f)
                    context_files.append(context_data)
                self.logger.info(f"Loaded context file: {json_file.name}")
            except Exception as e:
                self.logger.error(f"Failed to load context file {json_file}: {e}")
        
        self.logger.info(f"Loaded {len(context_files)} context files")
        return context_files

    def enrich_variety_from_context(self, variety_data: Dict[str, Any], context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single variety using its context data"""
        try:
            variety_name = variety_data.get('variety_name', 'Unknown')
            self.logger.info(f" Enriching variety: {variety_name}")
            
            # Extract search results from context
            search_results = context_data.get('search_results', [])
            
            # Perform analysis using Gemini
            analysis_result = self.analyze_with_pro_gemini(variety_data, search_results)
            
            # Combine original data with analysis
            enriched_data = {
                "original_data": variety_data,
                "context_data": context_data,
                "analysis_result": analysis_result,
                "enrichment_timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f" Successfully enriched: {variety_name}")
            self.stats["successful_enrichments"] += 1
            
            return enriched_data
            
        except Exception as e:
            self.logger.error(f" Failed to enrich variety {variety_data.get('variety_name', 'Unknown')}: {e}")
            self.stats["failed_enrichments"] += 1
            self.stats["errors"].append(str(e))
            return None

    def process_enrichment_batch(self, varieties: List[Dict[str, Any]], context_dir: str, batch_num: int = 1):
        """Process a batch of varieties for enrichment"""
        self.logger.info(f" Processing enrichment batch {batch_num} with {len(varieties)} varieties")
        
        # Load context files
        context_files = self.load_context_files(context_dir)
        
        if not context_files:
            self.logger.error("No context files found for enrichment")
            return []
        
        batch_results = []
        
        for variety in varieties:
            try:
                # Find matching context for this variety
                variety_name = variety.get('variety_name', '')
                matching_context = None
                
                for context in context_files:
                    context_variety = context.get('variety_info', {}).get('variety_name', '')
                    if context_variety.lower() == variety_name.lower():
                        matching_context = context
                        break
                
                if matching_context:
                    result = self.enrich_variety_from_context(variety, matching_context)
                    if result:
                        batch_results.append(result)
                else:
                    self.logger.warning(f"No context found for variety: {variety_name}")
                
                self.stats["varieties_processed"] += 1
                
            except Exception as e:
                self.logger.error(f"Batch enrichment error: {e}")
                continue
        
        # Save batch results
        batch_file = self.dirs["processed_batches_200"] / f"enriched_batch_{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(batch_file, 'w') as f:
            json.dump(batch_results, f, indent=2)
        
        self.logger.info(f" Enrichment batch {batch_num} completed: {len(batch_results)} successful enrichments")
        return batch_results

def main():
    """Main function to run the context enricher"""
    try:
        # Initialize enricher
        enricher = ContextEnricher()
        
        # Example usage - you would load your variety data here
        sample_varieties = [
            {"variety_name": "PR-124", "crop_name": "Rice"},
            {"variety_name": "Pusa 12", "crop_name": "Wheat"}
        ]
        
        # Process enrichment
        context_dir = "data/research_context/enhanced_data_200"
        results = enricher.process_enrichment_batch(sample_varieties, context_dir, batch_num=1)
        
        print(f"\n Context enrichment completed!")
        print(f" Varieties processed: {enricher.stats['varieties_processed']}")
        print(f" Successful enrichments: {enricher.stats['successful_enrichments']}")
        print(f" Failed enrichments: {enricher.stats['failed_enrichments']}")
        
    except Exception as e:
        print(f" Context enrichment failed: {e}")

if __name__ == "__main__":
    main() 