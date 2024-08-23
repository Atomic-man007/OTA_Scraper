import os
import re
import time
import random
import requests
import datetime
import pandas as pd
import streamlit as st
import concurrent.futures
import plotly.express as px
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

#import util
from util import get_proxies, test_proxy, create_driver

# Function to scrape website data
def scrape_website(driver, last_page_number):
    data = []
    for page_number in range(1, last_page_number + 1):
        url = f'https://kw.travel.rakuten.co.jp/keyword/Event.do?f_teikei=groupkw&f_query=&f_max=30&f_area=&f_chu=&f_shou=&f_category=0&f_sort=0&f_flg=&f_cd_application=&f_cd_chain=&f_all_chain=1&f_su=2&f_invoice_qualified=0&f_next={page_number}'
        driver.get(url)
        time.sleep(random.randint(2,7))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        main_section = soup.find('div', id='result')
        if main_section:
            hotel_boxes = main_section.find_all('div', class_='hotelBox')
            for hotel_box in hotel_boxes:
                hotel_name = hotel_box.select_one('.hotelName').get_text(strip=True) if hotel_box.select_one('.hotelName') else 'N/A'
                hotel_address = hotel_box.select_one('.hotelOutline .city').get_text(strip=True) if hotel_box.select_one('.hotelOutline .city') else 'N/A'
                price_details = hotel_box.select_one('.price dd').get_text(strip=True) if hotel_box.select_one('.price dd') else 'N/A'
                plans = hotel_box.select('.planBox')
                for plan in plans:
                    plan_title = plan.select_one('h3').get_text(strip=True) if plan.select_one('h3') else 'N/A'
                    plan_description = plan.select_one('.planOutline').get_text(strip=True) if plan.select_one('.planOutline') else 'N/A'
                    plan_prices_text = [price.get_text(strip=True) for price in plan.select('.rmTypPrc dd.plnPrc')]
                    data.append({
                        'Hotel Name': hotel_name,
                        'Hotel Address': hotel_address,
                        'Price Details': price_details,
                        'Plan Title': plan_title,
                        'Plan Description': plan_description,
                        'Plan Prices': '; '.join(plan_prices_text)
                    })
    driver.quit()
    return pd.DataFrame(data)

def extract_prices(plan_prices):
    base_price_match = re.search(r'(\d{1,3}(?:,\d{3})?円(?:～\d{1,3}(?:,\d{3})?円)?/人)', plan_prices)
    tax_price_match = re.search(r'（消費税込(\d{1,3}(?:,\d{3})?円(?:～\d{1,3}(?:,\d{3})?円)?/人)）', plan_prices)
    
    base_price = base_price_match.group(1) if base_price_match else None
    tax_price = tax_price_match.group(1) if tax_price_match else None
    
    return base_price, tax_price

# Function to convert yen strings to numeric values
def yen_to_float(yen_str):
    if yen_str:
        yen_str = yen_str.replace('円', '').replace(',', '').replace('/人', '')
        return float(yen_str.split('～')[0])  # If it's a range, take the lower bound
    return None

def analyze_rakuten_data(df):
    # Extract base and tax-inclusive prices
    df[['Base Price', 'Tax Price']] = df['Plan Prices'].apply(lambda x: pd.Series(extract_prices(x)))

    # Convert prices to numeric
    df['Base Price'] = df['Base Price'].apply(yen_to_float)
    df['Tax Price'] = df['Tax Price'].apply(yen_to_float)

    # Basic Analytics
    total_hotels = df['Hotel Name'].nunique()
    avg_base_price = df['Base Price'].mean()
    max_base_price = df['Base Price'].max()
    min_base_price = df['Base Price'].min()
    avg_tax_price = df['Tax Price'].mean()

    # Display Analytics
    st.write(f"Total number of unique hotels: {total_hotels}")
    st.write(f"Average Base Price: {avg_base_price}円")
    st.write(f"Maximum Base Price: {max_base_price}円")
    st.write(f"Minimum Base Price: {min_base_price}円")
    st.write(f"Average Tax-inclusive Price: {avg_tax_price}円")

    # Plotly Graphs
    fig_base_price_dist = px.bar(df, x='Hotel Name', y='Base Price', title="Base Price Distribution by Hotel",
                                 labels={'Base Price': 'Base Price (¥)', 'Hotel Name': 'Hotel Name'}, height=400)
    st.plotly_chart(fig_base_price_dist)

    fig_price_comparison = px.scatter(df, x='Base Price', y='Tax Price', color='Hotel Name',
                                      title="Base Price vs Tax-inclusive Price",
                                      labels={'Base Price': 'Base Price (¥)', 'Tax Price': 'Tax Price (¥)'}, height=400)
    st.plotly_chart(fig_price_comparison)

# Function to save data to CSV
def save_to_csv(df):
    folder_name = "rakuten_travel/scraped_data"
    os.makedirs(folder_name, exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_name, f"hotel_data_{current_time}.csv")
    df.to_csv(file_path, index=False, encoding='utf-8')
    return file_path

# Main function
def main():
    st.title("Rakuten Travel OTA Data Scraper")

    # Option to use proxy or personal IP address
    use_proxy = st.radio("Do you want to use a proxy?", ("No", "Yes"))
    last_page_number = st.number_input("Enter number of pages to scrape", min_value=1, value=1)

    if use_proxy == "Yes":
        st.write("Getting proxies...")
        proxies = get_proxies()
        working_proxies = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(test_proxy, proxies)
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

        # Analyze and display results
        analyze_rakuten_data(df)
        

if __name__ == "__main__":
    main()
