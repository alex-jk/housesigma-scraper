from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
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

    print(f"\n✅ Saved full page HTML: {html_filename}")

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

        # Extract type
        type_tag = listing.find_next("p", class_="type")  # Adjust the class name as needed
        type_text = type_tag.get_text(strip=True) if type_tag else "N/A"

        # Extract bedroom count
        bedroom_count = "N/A"
        listing_spec_mini = listing.find_next("div", class_="listing-spec-mini")
        
        if listing_spec_mini:
            p_tags = listing_spec_mini.find_all("p")  # Get all <p> tags in listing-spec-mini
            
            if len(p_tags) > 0:  # First <p> is bedrooms
                text_parts = p_tags[0].get_text(strip=True).split("bedroom -")
                if len(text_parts) > 1:
                    bedroom_count = text_parts[1].strip()
            
            if len(p_tags) > 1:  # Second <p> is bathrooms
                text_parts = p_tags[1].get_text(strip=True).split("bathroom -")
                if len(text_parts) > 1:
                    bathroom_count = text_parts[1].strip()
        
        # Extract postal code for each specific listing
        postal_code = "N/A"
        script_tag = listing.find_next("script", class_="hs-script-home-struct")

        if script_tag:
            try:
                json_data = json.loads(script_tag.string)
                if "address" in json_data and "postalCode" in json_data["address"]:
                    postal_code = json_data["address"]["postalCode"]
            except json.JSONDecodeError:
                print("Error decoding JSON from script tag")

        # Store the extracted data
        data.append({
            "Asking Price": asking_price,
            "Sold Price": sold_price,
            "Address": address,
            "Unit Type": type_text,
            "Bedrooms": bedroom_count,
            "Bathrooms": bathroom_count,
            "Postal Code": postal_code
        })

    # Convert data to DataFrame
    df = pd.DataFrame(data)
    return df

def fetch_sold_listings(url, num_pages=3):
    options = webdriver.ChromeOptions()

    # Add debugging options to avoid detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    print("Opening HouseSigma...")
    driver.get(url)

    input("Press Enter after verifying that you are logged in...")
    time.sleep(10)  # Wait for the page to load

    # Extract total number of pages from pagination
    soup = BeautifulSoup(driver.page_source, "html.parser")

    url_template = url.replace("page=1", "page={}")
    all_pages_df = []

    for page in range(1, num_pages + 1):

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

        all_pages_df.append(page_df)  # Append the DataFrame to the list

    driver.quit()
    print("✅ Scraping completed.")

    # Combine all DataFrames into a single DataFrame
    combined_df = pd.concat(all_pages_df, ignore_index=True)
    return combined_df

def clean_price(price):
    return float(str(price).replace('$', '').replace(',', ''))