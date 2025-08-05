# Filename: scrape_seednet_tables.py
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-08-01
# Last Modified: 2025-08-01
# Description: Scrapes tabular data from the SeedNet portal for seed variety information.

import time
import pandas as pd
import configparser
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import logging
from pathlib import Path
import os

class SeedNetTableScraper:
    def __init__(self, config_path='../config/config.ini'):
        """Initialize the SeedNet table scraper with configuration."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.driver = None
        self.main_window = None
        self.home_url = "https://seednet.gov.in/"
        
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
                logging.FileHandler(f'{log_dir}/seednet_scraping.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_driver(self, headless=False):
        """Set up Chrome driver with anti-detection measures."""
        options = Options()
        
        if headless:
            options.add_argument("--headless")
        
        # Anti-bot detection
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Execute script to remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.logger.info("Chrome driver initialized successfully")
    
    def navigate_to_varieties_page(self):
        """Navigate to the varieties page using JavaScript method."""
        self.logger.info(f"Navigating to homepage: {self.home_url}")
        self.driver.get(self.home_url)
        time.sleep(3)
        
        # Use JavaScript to navigate directly
        self.logger.info("Using JavaScript navigation to varieties page...")
        js_navigate = """
        // Try to find and click the varieties link using JavaScript
        var links = document.querySelectorAll('a[href*="CentralVariety.aspx"]');
        if (links.length > 0) {
            window.location.href = links[0].href;
            return true;
        }
        // If link not found, navigate directly
        window.location.href = 'https://seednet.gov.in/SeedVarieties/CentralVariety.aspx';
        return false;
        """
        
        result = self.driver.execute_script(js_navigate)
        time.sleep(5)
        
        self.logger.info(f"Successfully navigated to varieties page: {self.driver.current_url}")
        self.main_window = self.driver.current_window_handle
    
    def search_varieties(self, crop_name="GARLIC"):
        """Search for varieties of a specific crop."""
        self.logger.info(f"Searching for {crop_name} varieties...")
        
        # Mapping of crops to their groups
        crop_to_group = {
            "GARLIC": "BULB VEGETABLES",
            "ONION": "BULB VEGETABLES", 
            "MAIZE": "CEREALS",
            "WHEAT": "CEREALS",
            "RICE": "CEREALS",
            "CAULIFLOWER": "COLE CROPS",
            "CABBAGE": "COLE CROPS",
            "BROCOLLI": "COLE CROPS",
            "CUCUMBER": "CUCURBITS",
            "PUMPKIN": "CUCURBITS",
            "BOTTLE GOURD": "CUCURBITS",
            "BITTER GOURD": "CUCURBITS"
        }
        
        try:
            # First, select the crop group
            self.logger.info("Selecting crop group...")
            group_dropdown = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "_ctl0_ContentPlaceHolder1_ddlCropGroup"))
            )
            group_select = Select(group_dropdown)
            
            crop_group = crop_to_group.get(crop_name.upper(), "CEREALS")
            group_select.select_by_visible_text(crop_group)
            time.sleep(2)
            
            # Then select the specific crop
            self.logger.info("Selecting specific crop...")
            crop_dropdown = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "_ctl0_ContentPlaceHolder1_ddlCrop"))
            )
            crop_select = Select(crop_dropdown)
            crop_select.select_by_visible_text(crop_name.upper())
            time.sleep(2)
            
            # Click search button
            self.logger.info("Clicking search button...")
            search_button = self.driver.find_element(By.ID, "_ctl0_ContentPlaceHolder1_btnSearch")
            search_button.click()
            time.sleep(5)
            
            self.logger.info(f"Successfully searched for {crop_name} varieties")
            return True
            
        except Exception as e:
            self.logger.error(f"Error searching for {crop_name}: {e}")
            return False
    
    def scrape_varieties_data(self, max_varieties=None):
        """Scrape varieties data from the results table."""
        self.logger.info("Scraping varieties data...")
        
        try:
            # Wait for the correct table to be present
            table = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "_ctl0_ContentPlaceHolder1_grddata"))
            )
            self.logger.info("Found results table")
            
            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            self.logger.info(f"Found {len(rows)} rows in table")
            
            data = []
            
            # Each row contains: SlNo, Crop Name, Notified Year (No. of Variety), State/UT, Variety Name
            for i, row in enumerate(rows):
                try:
                    # Skip header row
                    if i == 0:
                        continue
                        
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        # Extract data from each cell
                        sl_no = cells[0].text.strip()
                        crop_name = cells[1].text.strip()
                        year_info = cells[2].text.strip()
                        state = cells[3].text.strip()
                        varieties_text = cells[4].text.strip()
                        
                        # Parse year and count
                        year = ""
                        count = ""
                        if year_info:
                            lines = year_info.split('\n')
                            if lines:
                                year = lines[0].strip()
                            if len(lines) > 1:
                                import re
                                count_match = re.search(r'\((\d+)\)', lines[1])
                                if count_match:
                                    count = count_match.group(1)
                        
                        # Parse individual varieties
                        varieties = []
                        if varieties_text:
                            # Split by common delimiters
                            variety_list = re.split(r'[,;\n]', varieties_text)
                            for variety in variety_list:
                                variety = variety.strip()
                                if variety and len(variety) > 2:  # Filter out very short entries
                                    varieties.append(variety)
                        
                        # Create record for each variety
                        for variety in varieties:
                            data.append({
                                'sl_no': sl_no,
                                'crop_name': crop_name,
                                'year': year,
                                'variety_count': count,
                                'state': state,
                                'variety_name': variety,
                                'scrape_timestamp': datetime.now().isoformat(),
                                'source_url': self.driver.current_url
                            })
                        
                        if max_varieties and len(data) >= max_varieties:
                            break
                            
                except Exception as e:
                    self.logger.warning(f"Error processing row {i}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(data)} variety records")
            return data
            
        except Exception as e:
            self.logger.error(f"Error scraping varieties data: {e}")
            return []
    
    def scrape_all_crops(self, crop_list=None, max_varieties_per_crop=None):
        """Scrape data for multiple crops."""
        if crop_list is None:
            crop_list = ["GARLIC", "ONION", "MAIZE", "WHEAT", "RICE"]
        
        all_data = []
        
        for crop in crop_list:
            self.logger.info(f"Processing crop: {crop}")
            
            # Navigate to varieties page for each crop
            self.navigate_to_varieties_page()
            
            # Search for the crop
            if self.search_varieties(crop):
                # Scrape the data
                crop_data = self.scrape_varieties_data(max_varieties_per_crop)
                all_data.extend(crop_data)
                
                self.logger.info(f"Completed {crop}: {len(crop_data)} varieties")
            else:
                self.logger.warning(f"Failed to search for {crop}")
            
            # Add delay between crops
            time.sleep(3)
        
        return all_data
    
    def save_data(self, data, output_dir=None):
        """Save scraped data to CSV file."""
        if output_dir is None:
            output_dir = self.config.get('PATHS', 'raw_tables_dir')
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"seednet_data_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        self.logger.info(f"Data saved to: {filepath}")
        self.logger.info(f"Total records: {len(df)}")
        
        return filepath
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            self.logger.info("WebDriver closed")

def main():
    """Main function to run the SeedNet scraper."""
    scraper = SeedNetTableScraper()
    
    try:
        # Setup driver
        scraper.setup_driver(headless=False)
        
        # Define crops to scrape
        crops_to_scrape = ["GARLIC", "ONION", "MAIZE", "WHEAT", "RICE"]
        
        # Scrape all crops
        all_data = scraper.scrape_all_crops(crops_to_scrape, max_varieties_per_crop=100)
        
        # Save data
        if all_data:
            output_file = scraper.save_data(all_data)
            print(f"\nScraping completed!")
            print(f"Scraped {len(all_data)} variety records")
            print(f"Data saved to: {output_file}")
        else:
            print("No data was scraped")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main() 