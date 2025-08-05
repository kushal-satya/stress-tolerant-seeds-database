# Filename: build_research_context.py
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-08-01
# Last Modified: 2025-08-01
# Description: Builds research context by performing web and academic searches for seed varieties.

#!/usr/bin/env python3
"""
Enhanced CSC-Seednet Integration Pipeline with Scholarly Package
Combines proven CSC pipeline source with new Seednet data
Implements 30+ search queries including Google Scholar via scholarly package
Uses pro mode Gemini for enhanced research results
Processes 200 varieties with post-2008 filtering
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

class ResearchContextBuilder:
    """
    Enhanced pipeline combining CSC source methodology with Seednet data
    Features:
    - aabout 30 comprehensive search queries per variety
    - Google Scholar integration via scholarly package
    - Gemini analysis
    """
    
    def __init__(self, config_path='../config/config.ini'):
        """Initialize the pipeline"""
        print("=" * 100)
        print("Processing 200 Varieties with Post-2008 Filtering")
        print("=" * 100)
        
        self.session_start = datetime.now()
        self.config = self._load_config(config_path)
        
        self.setup_logging()
        self.setup_gemini_api()
        self.setup_google_search_api()
        self.setup_directories()
        self.setup_scholarly()
        
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
        
        print(" Scholar / Gemini API  initialized successfully!")

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
        """Configure Gemini API for analysis"""
        try:
            api_key = self.config.get("API_KEYS", {}).get("gemini_api_key")
            if not api_key:
                raise Exception("No Gemini API key found in config")
            
            genai.configure(api_key=api_key)
            # Use 
            model_name = self.config.get("SETTINGS", {}).get("gemini_model", "gemini-2.5-flash")
            self.model = genai.GenerativeModel(model_name)
            
            self.logger.info(f"Gemini API configured with pro model: {model_name}")
            print(f" Gemini Pro API ready: {model_name}")
            
        except Exception as e:
            raise Exception(f"Failed to setup Gemini API: {e}")

    def setup_google_search_api(self):
        """Setup Google Custom Search API"""
        try:
            api_key = self.config.get("API_KEYS", {}).get("google_search_api_key")
            cse_id = self.config.get("API_KEYS", {}).get("google_search_engine_id")
            
            if not api_key or not cse_id:
                raise Exception("Google Search API credentials not found")
            
            self.search_service = build("customsearch", "v1", developerKey=api_key)
            self.cse_id = cse_id
            
            self.logger.info(" Google Custom Search API configured")
            print(" Google Search API ready")
            
        except Exception as e:
            raise Exception(f"💥 Failed to setup Google Search API: {e}")

    def setup_scholarly(self):
        """Setup scholarly package for Google Scholar access"""
        try:
            # Configure scholarly with rate limiting
            scholarly.use_proxy(None)  # Use default settings
            self.logger.info(" Scholarly package configured for Google Scholar access")
            print(" Scholarly package ready for Google Scholar")
            
        except Exception as e:
            self.logger.warning(f" Scholarly setup warning: {e}")

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

    def generate_30_search_queries(self, variety_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate 30 comprehensive search queries for each variety"""
        variety_name = variety_data.get('variety_name', '')
        crop_name = variety_data.get('crop_name', '')
        
        # State-specific disease/pest mapping
        state_disease_map = {
            'gujarat': ['blast', 'blight', 'rust', 'bollworm'],
            'maharashtra': ['leaf spot', 'stem borer', 'thrips', 'aphids'],
            'punjab': ['yellow rust', 'brown rust', 'pink bollworm', 'whitefly'],
            'haryana': ['karnal bunt', 'loose smut', 'shoot fly', 'stem borer'],
            'uttar pradesh': ['blast', 'sheath blight', 'brown planthopper', 'stem borer']
        }
        
        queries = []
        
        # 1: SINGLE Google Scholar search - Just variety name (1 query)
        queries.append({
            "type": "google_scholar",
            "query": variety_name,  # Just the variety name, no quotes
            "post_2008": True,
            "priority": "high"
        })
        
        # 2-9: Individual stress tolerance searches (Google Custom Search)
        stress_types = [
            'drought tolerance', 'heat tolerance', 'salinity tolerance',
            'flood tolerance', 'submergence tolerance', 'cold tolerance',
            'disease resistance', 'pest resistance'
        ]
        
        for stress in stress_types:
            queries.append({
                "type": "google_search",
                "query": f'"{variety_name}" {crop_name} {stress} after:2008',
                "post_2008": True,
                "priority": "high"
            })
        
        # 10-13: State-specific disease/pest searches
        for state, diseases in list(state_disease_map.items())[:4]:
            disease_terms = ' OR '.join(diseases)
            queries.append({
                "type": "google_search",
                "query": f'"{variety_name}" {crop_name} {state} ({disease_terms}) after:2008',
                "post_2008": True,
                "priority": "medium"
            })
        
        # 14-17: Genetic marker site-specific searches
        genetic_sites = [
            'site:ncbi.nlm.nih.gov',
            'site:gramene.org', 
            'site:plantgdb.org',
            'site:ipk-gatersleben.de'
        ]
        
        for site in genetic_sites:
            queries.append({
                "type": "google_search",
                "query": f'{site} "{variety_name}" {crop_name} QTL molecular markers',
                "post_2008": True,
                "priority": "medium"
            })
        
        # 18-21: Evidence variation searches
        evidence_types = [
            'farmer field trials participatory evaluation',
            'agronomic trials yield performance',
            'comparative studies field evaluation', 
            'stress performance assessment'
        ]
        
        for evidence in evidence_types:
            queries.append({
                "type": "google_search",
                "query": f'"{variety_name}" {crop_name} {evidence} after:2008',
                "post_2008": True,
                "priority": "medium"
            })
        
        # 22-24: Enhanced commercial availability
        commercial_terms = [
            'KVK "Krishi Vigyan Kendra" seed availability',
            'NSC "National Seeds Corporation" commercial',
            '"State Seed Corporation" seed dealers availability'
        ]
        
        for commercial in commercial_terms:
            queries.append({
                "type": "google_search",
                "query": f'"{variety_name}" {crop_name} {commercial}',
                "post_2008": True,
                "priority": "low"
            })
        
        # 25-27: Government portal integration
        govt_queries = [
            f'site:seednet.gov.in "{variety_name}" breeder allocation',
            f'site:icar.org.in "{variety_name}" {crop_name} notification',
            f'"gazette notification" "{variety_name}" {crop_name} after:2008'
        ]
        
        for govt_query in govt_queries:
            queries.append({
                "type": "google_search",
                "query": govt_query,
                "post_2008": True,
                "priority": "medium"
            })
        
        # 28-30: Comprehensive backup searches
        backup_queries = [
            f'"{variety_name}" {crop_name} research development breeding after:2008',
            f'"{variety_name}" genetics genomics molecular breeding after:2008',
            f'"{variety_name}" {crop_name} performance traits characteristics after:2008'
        ]
        
        for backup_query in backup_queries:
            queries.append({
                "type": "google_search",
                "query": backup_query,
                "post_2008": True,
                "priority": "low"
            })
        
        return queries

    def execute_google_scholar_search(self, query_data: Dict[str, str]) -> Dict[str, Any]:
        """Execute Google Scholar search using scholarly package"""
        try:
            self.rate_limit("scholar")
            
            query = query_data["query"]
            search_results = []
            
            # Search using scholarly
            search_query = scholarly.search_pubs(query)
            
            # Get up to 5 results
            for i, pub in enumerate(search_query):
                if i >= 5:  # Limit results
                    break
                    
                try:
                    # Extract publication info
                    result = {
                        'title': pub.get('bib', {}).get('title', ''),
                        'author': pub.get('bib', {}).get('author', ''),
                        'year': pub.get('bib', {}).get('pub_year', ''),
                        'journal': pub.get('bib', {}).get('journal', ''),
                        'abstract': pub.get('bib', {}).get('abstract', ''),
                        'url': pub.get('pub_url', ''),
                        'citations': pub.get('num_citations', 0)
                    }
                    
                    # Filter for post-2008 if required
                    if query_data.get("post_2008", False):
                        year = result.get('year', '')
                        if year and year.isdigit() and int(year) >= 2008:
                            search_results.append(result)
                            self.stats["post_2008_results"] += 1
                    else:
                        search_results.append(result)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing Scholar result: {e}")
                    continue
            
            self.stats["google_scholar_queries"] += 1
            self.stats["successful_queries"] += 1
            
            return {
                "query": query,
                "type": "google_scholar",
                "results": search_results,
                "count": len(search_results),
                "success": True
            }
            
        except Exception as e:
            self.stats["failed_queries"] += 1
            self.logger.error(f"Google Scholar search failed: {e}")
            return {
                "query": query_data["query"],
                "type": "google_scholar",
                "results": [],
                "count": 0,
                "success": False,
                "error": str(e)
            }

    def execute_google_search(self, query_data: Dict[str, str]) -> Dict[str, Any]:
        """Execute Google Custom Search"""
        try:
            self.rate_limit("api")
            
            query = query_data["query"]
            
            # Execute search
            search_results = self.search_service.list(
                q=query,
                cx=self.cse_id,
                num=10  # Get up to 10 results
            ).execute()
            
            results = []
            for item in search_results.get('items', []):
                result = {
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'displayLink': item.get('displayLink', ''),
                    'pagemap': item.get('pagemap', {})
                }
                results.append(result)
            
            self.stats["successful_queries"] += 1
            
            return {
                "query": query,
                "type": "google_search",
                "results": results,
                "count": len(results),
                "success": True
            }
            
        except Exception as e:
            self.stats["failed_queries"] += 1
            self.logger.error(f"Google Search failed: {e}")
            return {
                "query": query_data["query"],
                "type": "google_search",
                "results": [],
                "count": 0,
                "success": False,
                "error": str(e)
            }

    def execute_all_searches(self, variety_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute all search queries for a variety"""
        self.logger.info(f" Processing variety: {variety_data.get('variety_name', 'Unknown')}")
        
        # Generate queries
        queries = self.generate_30_search_queries(variety_data)
        self.logger.info(f" Executing {len(queries)} searches for {variety_data.get('variety_name', 'Unknown')}")
        
        all_results = []
        
        for i, query_data in enumerate(queries):
            try:
                if query_data["type"] == "google_scholar":
                    result = self.execute_google_scholar_search(query_data)
                else:
                    result = self.execute_google_search(query_data)
                
                all_results.append(result)
                self.stats["total_search_queries"] += 1
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    self.logger.info(f"   Completed {i+1}/{len(queries)} searches")
                    
            except Exception as e:
                self.logger.error(f"Search execution failed: {e}")
                self.stats["failed_queries"] += 1
        
        return all_results

    def build_context_for_variety(self, variety_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build research context for a single variety"""
        try:
            # Execute all searches
            search_results = self.execute_all_searches(variety_data)
            
            # Compile context
            context = {
                "variety_info": variety_data,
                "search_results": search_results,
                "search_metadata": {
                    "total_queries": len(search_results),
                    "successful_queries": sum(1 for r in search_results if r.get("success", False)),
                    "failed_queries": sum(1 for r in search_results if not r.get("success", False)),
                    "total_results": sum(r.get("count", 0) for r in search_results),
                    "processing_timestamp": datetime.now().isoformat()
                }
            }
            
            # Save context to file
            context_file = self.dirs["enhanced_data_200"] / f"context_{variety_data.get('variety_name', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(context_file, 'w') as f:
                json.dump(context, f, indent=2)
            
            self.logger.info(f" Successfully processed: {variety_data.get('variety_name', 'Unknown')}")
            self.stats["successful_enrichments"] += 1
            
            return context
            
        except Exception as e:
            self.logger.error(f" Failed to process variety {variety_data.get('variety_name', 'Unknown')}: {e}")
            self.stats["failed_enrichments"] += 1
            self.stats["errors"].append(str(e))
            return None

    def process_varieties_batch(self, varieties: List[Dict[str, Any]], batch_num: int = 1):
        """Process a batch of varieties"""
        self.logger.info(f" Processing batch {batch_num} with {len(varieties)} varieties")
        
        batch_results = []
        
        for variety in varieties:
            try:
                result = self.build_context_for_variety(variety)
                if result:
                    batch_results.append(result)
                
                self.stats["varieties_processed"] += 1
                
            except Exception as e:
                self.logger.error(f"Batch processing error: {e}")
                continue
        
        # Save batch results
        batch_file = self.dirs["processed_batches_200"] / f"batch_{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(batch_file, 'w') as f:
            json.dump(batch_results, f, indent=2)
        
        self.logger.info(f" Batch {batch_num} completed: {len(batch_results)} successful enrichments")
        return batch_results

def main():
    """Main function to run the research context builder"""
    try:
        # Initialize builder
        builder = ResearchContextBuilder()
        
        # Example usage - you would load your variety data here
        sample_varieties = [
            {"variety_name": "PR-124", "crop_name": "Rice"},
            {"variety_name": "Pusa 12", "crop_name": "Wheat"}
        ]
        
        # Process varieties
        results = builder.process_varieties_batch(sample_varieties, batch_num=1)
        
        print(f"\n Research context building completed!")
        print(f" Varieties processed: {builder.stats['varieties_processed']}")
        print(f" Successful enrichments: {builder.stats['successful_enrichments']}")
        print(f" Failed enrichments: {builder.stats['failed_enrichments']}")
        
    except Exception as e:
        print(f" Research context building failed: {e}")

if __name__ == "__main__":
    main() 