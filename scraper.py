from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json
import pandas as pd

# Use the extracted access token
ACCESS_TOKEN = "20241223l8341c1kjjish4povs28u7jn0t"  # Replace this with your actual access_token

def fetch_sold_listings(url):
    options = webdriver.ChromeOptions()

    # Add debugging options to avoid detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    
    # driver = webdriver.Chrome(options=options)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    print("Opening HouseSigma...")
    driver.get("https://housesigma.com")

    input("Press Enter after verifying that you are logged in...")
    time.sleep(20)  # Wait for the page to load

    # Reload the page to apply the token
    driver.get(url)
    print("Reloaded the url, waiting for the page to load")

    time.sleep(15)  # Wait for the page to load

    html = driver.page_source
    with open("logged_in_page_source.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("Logged-in page source saved.")
    driver.quit()
    
    return []

def get_listing_details(input_html_filename):
    # Load the saved HTML file
    with open(input_html_filename, "r", encoding="utf-8") as f:
        html = f.read()
    print("Reading html file")

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Find all listings (each listing contains price and address)
    listings = soup.find_all("p", class_="price")

    # Extract data
    data = []
    for listing in listings:
        # Extract asking price (crossed-out)
        asking_price_tag = listing.find("span", class_="line-through")
        asking_price = asking_price_tag.text.strip() if asking_price_tag else "N/A"

        # Extract sold price
        sold_price_tag = listing.find("span", class_="special")
        sold_price = sold_price_tag.text.strip() if sold_price_tag else "N/A"

        # Find the closest address (next "h3.address" tag in the HTML)
        address_tag = listing.find_next("h3", class_="address")
        address = address_tag.text.strip() if address_tag else "N/A"

        # Store the extracted data
        data.append({"Asking Price": asking_price, "Sold Price": sold_price, "Address": address})

    # Convert data to DataFrame
    df = pd.DataFrame(data)
    return df

# if __name__ == "__main__":
#     url = "https://housesigma.com/on/sold/map/?status=sold&lat=43.715564&lon=-79.418602&zoom=10&page=1&view=list"
#     fetch_sold_listings(url)