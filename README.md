# Stress-Tolerant Seeds Database Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)

> **Complete data engineering pipeline for stress-tolerant seed varieties database with interactive dashboard**

A comprehensive system for collecting, processing, and analyzing stress-tolerant seed variety data from multiple Indian agricultural sources, featuring AI-powered data extraction, fuzzy matching algorithms, and an interactive web dashboard.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/stress-tolerant-seeds-database.git
cd stress-tolerant-seeds-database

# Set up environment
chmod +x 00_setup/setup_environment.sh
./00_setup/setup_environment.sh

# Run the complete pipeline
python -c "
import subprocess
import sys

# Run all pipeline components
components = [
    'python 01_data_acquisition/scrape_seednet_tables.py',
    'python 02_pdf_processing/extract_pdf_to_csv.py', 
    'python 03_data_integration/match_and_merge.py',
    'python 04_data_enrichment/enrich_from_context.py',
    'python 05_structured_synthesis/generate_final_database.py',
    'python 06_dashboard/app.py'
]

for cmd in components:
    print(f'Running: {cmd}')
    subprocess.run(cmd.split())
"

# Launch dashboard
streamlit run 06_dashboard/app.py
```

## Features

- **Automated Data Pipeline**: 6-stage modular architecture
- **AI-Powered Extraction**: LLM-based PDF and web data processing  
- **Smart Data Integration**: Fuzzy matching and deduplication
- **Interactive Dashboard**: Streamlit-based exploration interface
- **Comprehensive Analysis**: Jupyter notebook with detailed EDA
- **Quality Assurance**: Data validation and completeness scoring
- **Multi-Source Integration**: CSC PDFs + SeedNet portal data

## Architecture

```
stress-tolerant-seeds-database/
├── 00_setup/           # Environment setup and configuration
├── 01_data_acquisition/ # Data collection from CSC PDFs and SeedNet
├── 02_pdf_processing/  # PDF extraction and table processing
├── 03_data_integration/ # Fuzzy matching and data merging
├── 04_data_enrichment/ # Research context and data enhancement
├── 05_structured_synthesis/ # Final database generation
├── 06_dashboard/       # Interactive Streamlit application
├── notebooks/          # Exploratory data analysis
├── data/              # Raw, processed, and final datasets
└── config/            # Configuration files
```

## Data Sources

- **CSC Meeting PDFs**: Official Central Seed Committee variety approval documents
- **SeedNet Portal**: Government seed variety database
- **Research Literature**: Scientific context and validation data

## Dashboard Features

The interactive dashboard provides:

- **Search & Filter**: By crop, stress tolerance, institution, region
- **Visualizations**: Distribution charts, stress tolerance heatmaps
- **Detailed Views**: Complete variety information and metadata
- **Export Options**: CSV, Excel data downloads

## Analysis Notebook

Comprehensive exploratory data analysis including:

- Data quality assessment and completeness scoring
- Stress tolerance pattern analysis across crops and regions
- Institutional breeding program insights
- Temporal trends in variety development
- Geographic adaptation patterns

## Installation

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment support

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/stress-tolerant-seeds-database.git
   cd stress-tolerant-seeds-database
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings**:
   ```bash
   cp config/config.ini.example config/config.ini
   # Edit config.ini with your settings
   ```

## Usage

### Running Individual Components

```bash
# Data acquisition
python 01_data_acquisition/scrape_seednet_tables.py

# PDF processing
python 02_pdf_processing/extract_pdf_to_csv.py

# Data integration
python 03_data_integration/match_and_merge.py

# Data enrichment
python 04_data_enrichment/enrich_from_context.py

# Database generation
python 05_structured_synthesis/generate_final_database.py

# Launch dashboard
streamlit run 06_dashboard/app.py
```

### Running Complete Pipeline

Use the automated setup script:
```bash
./setup_github.sh
```

## Configuration

Edit `config/config.ini` to customize:

- Data source URLs and paths
- Processing parameters
- Database connection settings
- Dashboard configuration
- Logging levels

## Data Schema

The final database includes:

- **Variety Information**: Name, crop type, breeding institution
- **Stress Tolerance**: Drought, heat, salt, disease resistance
- **Quality Traits**: Yield, nutritional content, market characteristics
- **Geographic Data**: Recommended states, agro-climatic zones
- **Temporal Data**: Year of release, maturity period
- **Research Context**: Parent lines, genetic markers, publications

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Kushal Kumar**  
Email: kd475@cornell.edu  
Institution: Cornell University

## Acknowledgments

- Central Seed Committee for variety approval data
- SeedNet portal for comprehensive variety information
- Agricultural research institutions for breeding program data

---

**Star this repository if you find it useful!**
