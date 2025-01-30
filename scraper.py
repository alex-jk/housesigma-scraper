from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
import json
import pandas as pd

def debug_pagination(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    print("Opening HouseSigma...")
    driver.get("https://housesigma.com")

    input("🔹 Press Enter after verifying that you are logged in...")  
    time.sleep(5)

    driver.get(url)

    time.sleep(5)  # Additional wait to ensure JavaScript has fully loaded

    # Save full HTML for inspection
    html_filename = "full_page_source.html"
    page_source = driver.page_source  # Get the full HTML as a string

    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(page_source)

    print(f"✅ Saved full page HTML: {html_filename}")

    driver.quit()

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

def fetch_sold_listings(url):
    options = webdriver.ChromeOptions()

    # Add debugging options to avoid detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    print("Opening HouseSigma...")
    driver.get(url)

    input("Press Enter after verifying that you are logged in...")
    time.sleep(15)  # Wait for the page to load

    # Extract total number of pages from pagination
    soup = BeautifulSoup(driver.page_source, "html.parser")

    url_template = url.replace("page=1", "page={}")

    for page in range(1, 4):

        paginated_url = url_template.format(page)
        print(f"Scraping: {paginated_url}")

        # Reload the page to apply the token
        driver.get(paginated_url)
        print("Reloaded the url, waiting for the page to load")

        time.sleep(10)  # Wait for the page to load

        html_filename = f"housesigma_page_{page}.html"
        html = driver.page_source
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✅ Saved HTML: {html_filename}")
        print("\nRetrieving data from the page")

        page_df = get_listing_details(html_filename)
        print(page_df.head())

    driver.quit()
    print("✅ Scraping completed.")

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

def fetch_sold_listings_test(url):
    options = webdriver.ChromeOptions()

    # Add debugging options to avoid detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    print("Opening HouseSigma...")
    driver.get("https://housesigma.com")

    input("Press Enter after verifying that you are logged in...")
    time.sleep(15)  # Wait for the page to load

    # Load the first page
    driver.get(url)
    time.sleep(5)

    page = 1
    previous_content = None  # Store the previous page content to detect changes

    while True:
        print(f"Scraping page {page}...")

        # Save the HTML content
        html_filename = f"housesigma_page_{page}.html"
        current_content = driver.page_source

        # Check if the content has changed
        if current_content == previous_content:
            print("No new content found. Exiting loop.")
            break

        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(current_content)

        print(f"✅ Saved HTML: {html_filename}")

        # Update the previous content
        previous_content = current_content

        # Scroll down to trigger lazy loading (if applicable)
        print("Scrolling down to load more content...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)  # Wait for new content to load

        page += 1

    driver.quit()
    print("✅ Scraping completed.")