import os
import time
import json
import datetime
import numpy as np
import pandas as pd
import streamlit as st
import concurrent.futures
import plotly.express as px
from bs4 import BeautifulSoup
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException,\
    TimeoutException, NoSuchElementException, StaleElementReferenceException

#import util
from util import get_proxies, test_proxy, create_driver


# Function to scrape the website dynamically
def scrape_website(driver, last_page_number):
    hotels = []
    
    # Loop through each page from 1 to last_page_number
    for page in range(1, last_page_number + 1):
        if page == 1:
            url = 'https://www.jalan.net/biz/130000/'  # The first page doesn't have the page number in the URL
        else:
            url = f'https://www.jalan.net/biz/130000/page{page}.html'
        
        driver.get(url)  # Navigate to the dynamic URL
        time.sleep(3)  # Allow the page to load
        
        # Parse page source with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Base URL for constructing full links
        base_url = 'https://www.jalan.net'
        main_sections = soup.find('div', class_='styleguide-scope p-searchResults')

        # List to hold extracted data
        hotel_data = []
        if main_sections:
            # Extract hotel items
            hotel_items = main_sections.find_all('ol')
            for ol in hotel_items:
                li_elements = ol.find_all('li', class_ = 'p-yadoCassette')
                
            
                for item in li_elements:
                    hotel_name_element = item.find('h2', class_='p-searchResultItem__facilityName')
                    location_element = item.find('dd', class_='p-searchResultItem__accessValue')
                    price_element = item.find('span', class_='p-searchResultItem__lowestPriceValue')
                    plans_table = item.find('table', class_='p-planTable p-searchResultItem__planTable')
                    
                    hotel_name = hotel_name_element.get_text(strip=True) if hotel_name_element else 'N/A'
                    hotel_link = base_url + hotel_name_element.find('a')['href'] if hotel_name_element else 'N/A'
                    location = location_element.get_text(strip=True) if location_element else 'N/A'
                    price = price_element.get_text(strip=True) if price_element else 'N/A'
                    
                    # Extract accommodation plans
                    if plans_table:
                        rows = plans_table.find_all('tr')[1:]  # Skip header row
                        for row in rows:
                            plan_name_element = row.find('a', class_='p-searchResultItem__planName')
                            per_person_element = row.find('span', class_='p-searchResultItem__perPerson')
                            total_element = row.find('span', class_='p-searchResultItem__total')
                            
                            plan_name = plan_name_element.get_text(strip=True) if plan_name_element else 'N/A'
                            plan_link = base_url + plan_name_element['href'] if plan_name_element else 'N/A'
                            per_person_price = per_person_element.get_text(strip=True) if per_person_element else 'N/A'
                            total_price = total_element.get_text(strip=True) if total_element else 'N/A'
                            
                            # Append the flattened data for each plan
                            hotel_data.append({
                                'Hotel Name': hotel_name,
                                'Hotel Link': hotel_link,
                                'Location': location,
                                'Price': price,
                                'Plan Name': plan_name,
                                'Plan Link': plan_link,
                                'Per Person Price': per_person_price,
                                'Total Price': total_price
                            })
                    else:
                        # If no plans are found, add the hotel data without plan info
                        hotel_data.append({
                            'Hotel Name': hotel_name,
                            'Hotel Link': hotel_link,
                            'Location': location,
                            'Price': price,
                            'Plan Name': 'N/A',
                            'Plan Link': 'N/A',
                            'Per Person Price': 'N/A',
                            'Total Price': 'N/A'
                        })

    # Convert the flattened hotel data to a pandas DataFrame
    df = pd.DataFrame(hotel_data)
    
    return df

# Function to save data to CSV
def save_to_csv(df):
    folder_name = "jalan/scraped_data"
    os.makedirs(folder_name, exist_ok=True)
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_name, f"hotel_data_{current_time}.csv")
    df.to_csv(file_path, index=False, encoding='utf-8')
    return file_path

def analyze_hotel_data(df):
    # Convert price columns to numeric, handling non-numeric characters
    df['Price'] = df['Price'].str.replace('円', '').str.replace(',', '').str.extract('(\d+)').astype(float)
    df['Per Person Price'] = df['Per Person Price'].str.replace('円', '').str.replace(',', '').str.extract('(\d+)').astype(float)
    df['Total Price'] = df['Total Price'].str.replace('円', '').str.replace(',', '').str.extract('(\d+)').astype(float)

    # Basic Analytics
    total_hotels = df['Hotel Name'].nunique()
    avg_price = df['Price'].mean()
    max_price = df['Price'].max()
    min_price = df['Price'].min()
    avg_per_person_price = df['Per Person Price'].mean()
    avg_total_price = df['Total Price'].mean()

    # Display Analytics
    st.write(f"**Total number of unique hotels:** {total_hotels}")
    st.write(f"**Average Price:** {avg_price:.2f}円")
    st.write(f"**Maximum Price:** {max_price:.2f}円")
    st.write(f"**Minimum Price:** {min_price:.2f}円")
    st.write(f"**Average Per Person Price:** {avg_per_person_price:.2f}円")
    st.write(f"**Average Total Price:** {avg_total_price:.2f}円")

    # Bar Chart: Distribution of Prices
    fig_price_dist = px.bar(df, x='Hotel Name', y='Price', title="Price Distribution by Hotel Name",
                            labels={'Price': 'Price (¥)', 'Hotel Name': 'Hotel Name'}, height=400)
    st.plotly_chart(fig_price_dist)

    # Scatter Plot: Per Person Price vs Total Price
    fig_price_comparison = px.scatter(df, x='Per Person Price', y='Total Price', color='Hotel Name',
                                      title="Per Person Price vs Total Price",
                                      labels={'Per Person Price': 'Per Person Price (¥)', 'Total Price': 'Total Price (¥)'}, height=400)
    st.plotly_chart(fig_price_comparison)

# Main function
def main():
    st.title("Jalan OTA Data Scraper")

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
        analyze_hotel_data(df)

if __name__ == "__main__":
    main()