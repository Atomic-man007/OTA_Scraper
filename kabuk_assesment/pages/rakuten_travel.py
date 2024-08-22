import streamlit as st
import time
import datetime
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import concurrent.futures
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

if __name__ == "__main__":
    main()
