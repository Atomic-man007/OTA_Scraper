# OTA_Scraper

OTA Scraper to scrape ikyu, rakuten and jalan

`streamlit run homepage.py`

# Hotel Price Scraper

## Overview

This Streamlit application scrapes hotel pricing data from a specified Online Travel Agency (OTA) website, handling JavaScript rendering and implementing basic proxy rotation. It generates a CSV report summarizing the captured data.

## Features

- Web scraping of hotel data (name, location, room types, prices)
- JavaScript rendering handling
- Basic proxy rotation
- CSV report generation
- Streamlit-based user interface

## Installation

1. Clone the repository:

2. Install dependencies:
   pip install -r requirements.txt
   Copy

## Usage

1. Run the Streamlit app:
   streamlit run app.py
   Copy
2. Open your web browser and navigate to the URL provided by Streamlit (usually http://localhost:8501).

3. Use the interface to input the OTA website URL and configure scraping parameters.

4. Click the "Start Scraping" button to begin the process.

5. Once complete, download the generated CSV report.

## Project Structure

```
hotel-price-scraper/
│
├── app.py # Main Streamlit application
├── scraper/
│ ├── init.py
│ ├── scraper.py # Web scraping logic
│ └── proxy_manager.py # Proxy rotation mechanism
│
├── utils/
│ ├── init.py
│ └── report_generator.py # CSV report generation
│
├── requirements.txt # Project dependencies
└── README.md # Project documentation
```

## Dependencies

- Python 3.8+
- Streamlit
- Selenium
- BeautifulSoup4
- Requests
- Pandas

## Approach and Challenges

[Briefly explain your approach to the assignment, challenges faced, and how you addressed them.]

## Future Improvements

[List potential improvements or features that could be added with more time.]
