#!/bin/bash

# Filename: setup_environment.sh
# Author: kd475
# Contact: kd475@cornell.edu
# Date Created: 2025-08-01
# Last Modified: 2025-08-04
# Description: Sets up the Python virtual environment and installs all required dependencies for the stress-tolerant seeds database pipeline.

echo "Setting up Stress-Tolerant Seeds Database Environment"
echo "=================================================="

# Check if Python 3.8+ is installed
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "Python version check passed: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing required packages..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating data directories..."
mkdir -p data/raw_pdfs
mkdir -p data/raw_tables
mkdir -p data/processed
mkdir -p data/final
mkdir -p data/research_context
mkdir -p logs

# Set up configuration
echo "Setting up configuration..."
if [ ! -f config/config.ini ]; then
    echo "Creating config template..."
    cat > config/config.ini << EOF
[API_KEYS]
# Google Gemini API Key
gemini_api_key = YOUR_GEMINI_API_KEY_HERE

# Google Custom Search API
google_search_api_key = YOUR_GOOGLE_SEARCH_API_KEY_HERE
google_search_engine_id = YOUR_SEARCH_ENGINE_ID_HERE

# Serper API (alternative search)
serper_api_key = YOUR_SERPER_API_KEY_HERE

# Semantic Scholar API
semantic_scholar_api_key = YOUR_SEMANTIC_SCHOLAR_API_KEY_HERE

[PATHS]
# Data directories
raw_pdfs_dir = data/raw_pdfs
raw_tables_dir = data/raw_tables
processed_dir = data/processed
final_dir = data/final
research_context_dir = data/research_context
logs_dir = logs

[URLS]
# Target URLs for scraping
csc_portal_url = https://seednet.gov.in/Material/CSC.aspx
seednet_base_url = https://seednet.gov.in

[SETTINGS]
# Processing settings
max_pdfs_to_process = 100
max_searches_per_variety = 30
confidence_threshold = 0.8
batch_size = 10
EOF
    echo "Configuration template created at config/config.ini"
    echo "Please update config/config.ini with your API keys before running the pipeline"
else
    echo "Configuration file already exists"
fi

# Set permissions
chmod +x 00_setup/setup_environment.sh

echo ""
echo "Environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Update config/config.ini with your API keys"
echo "3. Run the pipeline scripts in order (01_data_acquisition, 02_pdf_processing, etc.)"
echo ""
echo "To activate the environment, run:"
echo "source venv/bin/activate" 