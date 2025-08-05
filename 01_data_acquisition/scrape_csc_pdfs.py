# Filename: scrape_csc_pdfs.py
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-08-01
# Last Modified: 2025-08-01
# Description: Scrapes PDF documents from the CSC meetings portal and downloads them to the raw_pdfs directory.

import os
import re
import requests
import configparser
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path
import logging
from tqdm import tqdm
import time

class CSCPDFScraper:
    def __init__(self, config_path='../config/config.ini'):
        """Initialize the CSC PDF scraper with configuration."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
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
                logging.FileHandler(f'{log_dir}/csc_pdf_scraping.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_pdf_links(self, url):
        """Extract PDF links from the CSC portal page."""
        try:
            self.logger.info(f"Fetching page: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            pdf_links = []
            
            # Look for PDF links in various formats
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and href.lower().endswith('.pdf'):
                    full_url = urljoin(url, href)
                    pdf_links.append({
                        'url': full_url,
                        'text': link.get_text(strip=True),
                        'title': link.get('title', '')
                    })
            
            # Also look for links that might contain PDFs in onclick or other attributes
            for link in soup.find_all(['a', 'div'], onclick=True):
                onclick = link.get('onclick', '')
                if '.pdf' in onclick.lower():
                    # Extract URL from onclick
                    pdf_match = re.search(r'["\']([^"\']*\.pdf[^"\']*)["\']', onclick)
                    if pdf_match:
                        full_url = urljoin(url, pdf_match.group(1))
                        pdf_links.append({
                            'url': full_url,
                            'text': link.get_text(strip=True),
                            'title': link.get('title', '')
                        })
            
            self.logger.info(f"Found {len(pdf_links)} PDF links")
            return pdf_links
            
        except Exception as e:
            self.logger.error(f"Error fetching PDF links: {e}")
            return []
    
    def download_pdf(self, pdf_info, output_dir):
        """Download a single PDF file."""
        try:
            url = pdf_info['url']
            filename = self._generate_filename(pdf_info)
            filepath = os.path.join(output_dir, filename)
            
            if os.path.exists(filepath):
                self.logger.info(f"PDF already exists: {filename}")
                return filepath
            
            self.logger.info(f"Downloading: {filename}")
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"Successfully downloaded: {filename}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error downloading {pdf_info.get('url', 'unknown')}: {e}")
            return None
    
    def _generate_filename(self, pdf_info):
        """Generate a systematic filename for the PDF."""
        text = pdf_info.get('text', '')
        title = pdf_info.get('title', '')
        
        # Extract date if present
        date_match = re.search(r'(\d{4})[-_](\d{1,2})[-_](\d{1,2})', text + title)
        if date_match:
            date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Clean text for filename
        clean_text = re.sub(r'[^\w\s-]', '', text)
        clean_text = re.sub(r'[-\s]+', '-', clean_text).strip('-')
        
        if clean_text:
            filename = f"CSC-Meeting_{date_str}_{clean_text[:50]}.pdf"
        else:
            filename = f"CSC-Meeting_{date_str}_Document.pdf"
        
        return filename
    
    def scrape_all_pdfs(self):
        """Main method to scrape all PDFs from the CSC portal."""
        try:
            csc_url = self.config.get('URLS', 'csc_portal_url')
            output_dir = self.config.get('PATHS', 'raw_pdfs_dir')
            max_pdfs = int(self.config.get('SETTINGS', 'max_pdfs_to_process', fallback='100'))
            
            os.makedirs(output_dir, exist_ok=True)
            
            self.logger.info("Starting CSC PDF scraping process")
            self.logger.info(f"Target URL: {csc_url}")
            self.logger.info(f"Output directory: {output_dir}")
            
            # Get PDF links
            pdf_links = self.get_pdf_links(csc_url)
            
            if not pdf_links:
                self.logger.warning("No PDF links found on the page")
                return []
            
            # Limit the number of PDFs to process
            pdf_links = pdf_links[:max_pdfs]
            
            # Download PDFs with progress bar
            downloaded_files = []
            for pdf_info in tqdm(pdf_links, desc="Downloading PDFs"):
                filepath = self.download_pdf(pdf_info, output_dir)
                if filepath:
                    downloaded_files.append(filepath)
                
                # Add delay to be respectful to the server
                time.sleep(1)
            
            self.logger.info(f"Scraping completed. Downloaded {len(downloaded_files)} PDFs")
            return downloaded_files
            
        except Exception as e:
            self.logger.error(f"Error in scraping process: {e}")
            return []

def main():
    """Main function to run the CSC PDF scraper."""
    scraper = CSCPDFScraper()
    downloaded_files = scraper.scrape_all_pdfs()
    
    print(f"\nScraping completed!")
    print(f"Downloaded {len(downloaded_files)} PDF files")
    print(f"Files saved to: {scraper.config.get('PATHS', 'raw_pdfs_dir')}")

if __name__ == "__main__":
    main() 