from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
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
    time.sleep(10)  

    driver.get(url)
    time.sleep(5)  

    # Save full HTML for inspection
    html_filename = "full_page_source.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    print(f"✅ Saved full page HTML: {html_filename}")
    
    driver.quit()

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
    time.sleep(15)  # Wait for the page to load

    # Load the first page
    driver.get(url)
    time.sleep(5)

    # **Wait for pagination elements to load**
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//nav | //ul | //div[contains(@class, 'pagination')]"))
        )
        print("✅ Pagination detected.")
    except:
        print("⚠ Pagination not found immediately. Proceeding with available data.")

    # Extract total number of pages from pagination
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # **Find all possible pagination containers**
    pagination_container = soup.find("nav") or soup.find("ul") or soup.find("div", class_="pagination")

    if pagination_container:
        print("🔍 Pagination HTML structure detected:")
        print(pagination_container.prettify())  # Print the full HTML of pagination
    else:
        print("⚠ No pagination container found.")

    page_numbers = []
    if pagination_container:
        for link in pagination_container.find_all("a"):
            if link.text.strip().isdigit():
                page_numbers.append(int(link.text.strip()))

    max_page = max(page_numbers) if page_numbers else 1  # Get the highest page number

    print(f"🔹 Total number of pages detected: {max_page}")

    url_template = url.replace("page=1", "page={}")

    for page in range(1, 3):

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

# if __name__ == "__main__":
#     url = "https://housesigma.com/on/sold/map/?status=sold&lat=43.715564&lon=-79.418602&zoom=10&page=1&view=list"
#     fetch_sold_listings(url)