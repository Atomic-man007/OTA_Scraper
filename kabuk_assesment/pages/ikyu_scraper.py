import os
import re
import time
import random
import datetime
import requests
import pandas as pd
import numpy as np
import streamlit as st
import concurrent.futures
from bs4 import BeautifulSoup
from selenium import webdriver
import plotly.express as px
import plotly.graph_objects as go
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException,\
    TimeoutException, NoSuchElementException, StaleElementReferenceException
#import util
from util import get_proxies, test_proxy, create_driver


# Function to scrape the website
def scrape_website(driver, last_page_number):
    hotels = []
    for page in range(1, last_page_number + 1):
        url = f'https://www.ikyu.com/area/ma000000/p{page}/?adc=1&lc=1&per_page=20&ppc=2&rc=1&si=6'
        driver.get(url)
        time.sleep(3)  # Allow the page to load
        
        # Parse page source with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        main_sections = soup.find_all('section', class_='relative')
        
        if main_sections:
            for i, section in enumerate(main_sections):
                # Scroll to the section to ensure it's in view
                try:
                    # Find and click the button to expand the section
                    button = driver.find_element(By.CSS_SELECTOR, f'#__nuxt > div > div.min-h-screen > main > div.w-full.bg-gray-100 > div > div > div.w-\\[950px\\] > div:nth-child(2) > section > div:nth-child({i+1}) > section > div.px-7.pb-7 > div > section > div.relative.box-border.h-14.px-0.pb-14.pt-5 > div > button')
                    button.click()
                except Exception as e:
                    print("An error occurred while clicking the button:", e)

                time.sleep(random.randint(2, 4))
                updated_soup = BeautifulSoup(driver.page_source, 'html.parser')
                updated_section = updated_soup.find_all('section', class_='relative')[i]
                
                # Extract hotel name and address
                name_tag = updated_section.find('h2', itemprop='name', class_='nameText')
                hotel_name = name_tag.text.strip() if name_tag else 'N/A'
                address_tag = updated_section.find('p', class_='mt-3 w-2/3 text-sm leading-6 text-gray-400')
                hotel_address = address_tag.text.strip() if address_tag else 'N/A'

                # Extract room information
                room_list = updated_section.find('div', class_='px-7 pb-7').find('ul')
                li_elements = room_list.find_all('li') if room_list else []
                
                rooms = []
                for room in li_elements:
                    nested_ul = room.find('ul', class_='mr-2.5')
                    if nested_ul:
                        name = nested_ul.find('a').get_text(strip=True)
                        ul_w_3_5 = nested_ul.find_next('ul', class_='w-3/5')
                        if ul_w_3_5:
                            formatted_Detailprices = [li.get_text(strip=True) for li in ul_w_3_5.find_all('li')]
                            rooms.append({
                                'Room type': name,
                                'Room Price Detail': formatted_Detailprices
                            })


                # Store hotel information with its rooms
                for room in rooms:
                    hotels.append({
                        'Hotel Name': hotel_name,
                        'Address': hotel_address,
                        'Room Type': room['Room type'],
                        'Room Price Detail': room['Room Price Detail']
                    })

                try:
                    # Find the button using the CSS selector
                    button = driver.find_element(By.CSS_SELECTOR, f'#__nuxt > div > div.min-h-screen > main > div.w-full.bg-gray-100 > div > div > div.w-\\[950px\\] > div:nth-child(2) > section > div:nth-child({i+1}) > section > div.px-7.pb-7 > div > section > div.relative.box-border.h-14.px-0.pb-14.pt-5 > div > button')

                    # Click the button
                    button.click()
                except Exception as e:
                    print("An error occurred:", e)
                time.sleep(2)

    # Convert the hotel data to a pandas DataFrame
    df = pd.DataFrame(hotels)

    return df

# Function to clean and split the Room Price Detail
def clean_price_detail(detail_str):
    # Remove single quotes and brackets, and then split into a list
    detail_str = detail_str.strip("[]").replace("'", "")
    return detail_str.split(", ")

# Extract prices function
def extract_prices(price_details):
    price_dict = {
        '2名税込': None,
        '朝食付2名税込': None,
        '夕食付2名税込': None
    }
    
    for detail in price_details:
        if '2名税込' in detail and price_dict['2名税込'] is None:
            match = re.search(r'(\d{1,3}(?:,\d{3})*)円', detail)
            if match:
                price_dict['2名税込'] = float(match.group(1).replace(',', ''))
        
        if '朝食付2名税込' in detail and price_dict['朝食付2名税込'] is None:
            match = re.search(r'(\d{1,3}(?:,\d{3})*)円', detail)
            if match:
                price_dict['朝食付2名税込'] = float(match.group(1).replace(',', ''))
        
        if '夕食付2名税込' in detail and price_dict['夕食付2名税込'] is None:
            match = re.search(r'(\d{1,3}(?:,\d{3})*)円', detail)
            if match:
                price_dict['夕食付2名税込'] = float(match.group(1).replace(',', ''))
    
    return [price_dict['2名税込'], price_dict['朝食付2名税込'], price_dict['夕食付2名税込']]

# Function to perform analytics on the data and display in Streamlit
def perform_analytics(df):
    # Extract numerical prices from 'Room Price Detail'
    df['Extracted Prices'] = df['Room Price Detail'].apply(extract_prices)
    
    # Calculate average price per room type
    df['Average Price'] = df['Extracted Prices'].apply(lambda x: np.mean([p for p in x if p is not None]))
    avg_price_per_room = df.groupby('Room Type')['Average Price'].mean().sort_values(ascending=False)
    
    # Display Average Price per Room Type
    st.subheader("Average Price per Room Type")
    for room_type, avg_price in avg_price_per_room.items():
        st.metric(label=f"Room Type: {room_type}", value=f"{avg_price:,.0f} 円")
    
    # Distribution of Prices
    all_prices = [price for sublist in df['Extracted Prices'].tolist() for price in sublist if price is not None]
    fig = px.histogram(all_prices, nbins=30, title="Price Distribution", labels={'value': 'Price (円)'})
    fig.update_layout(xaxis_title='Price (円)', yaxis_title='Count')
    st.subheader("Price Distribution")
    st.plotly_chart(fig)
    
    # Top 5 Most Expensive Hotels
    df['Max Price'] = df['Extracted Prices'].apply(lambda x: max([p for p in x if p is not None], default=0))
    top_expensive_hotels = df[['Hotel Name', 'Max Price']].sort_values(by='Max Price', ascending=False).head(5)
    
    st.subheader("Top 5 Most Expensive Hotels")
    for _, row in top_expensive_hotels.iterrows():
        st.metric(label=row['Hotel Name'], value=f"{row['Max Price']:,.0f} 円")
    
    # Price Range Analysis
    df['Price Range'] = df['Extracted Prices'].apply(lambda x: max([p for p in x if p is not None], default=0) - min([p for p in x if p is not None], default=0))
    price_range_analysis = df.groupby('Room Type')['Price Range'].mean().sort_values(ascending=False)
    
    st.subheader("Price Range Analysis")
    fig_range = go.Figure()
    fig_range.add_trace(go.Bar(
        x=price_range_analysis.index,
        y=price_range_analysis.values,
        name="Average Price Range by Room Type"
    ))
    fig_range.update_layout(title="Average Price Range by Room Type",
                            xaxis_title="Room Type",
                            yaxis_title="Average Price Range (円)",
                            xaxis_tickangle=-45)
    st.plotly_chart(fig_range)

# Function to save data to CSV
def save_to_csv(df):
    folder_name = "ikyu/scraped_data"
    os.makedirs(folder_name, exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_name, f"hotel_data_{current_time}.csv")
    df.to_csv(file_path, index=False, encoding='utf-8')
    return file_path

# Main function
def main():
    st.title("Ikyu OTA Data Scraper")

    # Option to use proxy or personal IP address
    use_proxy = st.radio("Do you want to use a proxy?", ("No", "Yes"))
    last_page_number = st.number_input("Enter number of pages to scrape", min_value=1, value=1)

    if use_proxy == "Yes":
        st.write("Getting proxies...")
        proxies = get_proxies()  # Implement your proxy retrieval function
        working_proxies = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(test_proxy, proxies)  # Implement your proxy testing function
            for result in results:
                if result is not None:
                    working_proxies.append(result)
        num_working_proxies = len(working_proxies)
        st.write(f"Found {num_working_proxies} working proxies.")
    
    if st.button("Start Scraping"):
        st.write("Scraping started...")
        
        driver = create_driver(use_proxy == "Yes", working_proxies if use_proxy == "Yes" else None)
        df = scrape_website(driver, last_page_number)
        file_path = save_to_csv(df)
        st.write(f"Scraping completed. Data saved to {file_path}.")
        st.dataframe(df)
        
        # Analyze and display data using the function
        perform_analytics(df)

if __name__ == "__main__":
    main()