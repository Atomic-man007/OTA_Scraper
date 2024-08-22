
import os
import time
import random
import requests
import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.proxy import Proxy, ProxyType

# Function to get proxies from the proxy website
def get_proxies():
    r = requests.get("https://free-proxy-list.net/")
    soup = BeautifulSoup(r.content, "html.parser")
    table = soup.find("tbody")

    proxies = []
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        if columns[4].text.strip() == "elite proxy":
            proxy = f"{columns[0].text}:{columns[1].text}"
            proxies.append(proxy)
    return proxies

# Function to test proxies
def test_proxy(proxy):
    try:
        r = requests.get(
            "https://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=5
        )
        r.raise_for_status()  # Raises HTTPError if the response status code is >= 400
        return proxy
    except requests.exceptions.RequestException:
        return None

# Function to rotate proxy
def rotate_proxy(working_proxies):
    if not working_proxies:
        st.write("No working proxies found.")
        return None
    
    random_proxy = random.choice(working_proxies)
    st.write(f"Rotating to proxy: {random_proxy}")

    options = Options()
    options.add_argument(f"--proxy-server={random_proxy}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.delete_all_cookies()
    time.sleep(random.randint(2,7))
    return driver

# Function to create a WebDriver with or without proxy
def create_driver(use_proxy, working_proxies):
    if use_proxy:
        return rotate_proxy(working_proxies)
    else:
        options = Options()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.delete_all_cookies()
        time.sleep(random.randint(2,7))
        return driver