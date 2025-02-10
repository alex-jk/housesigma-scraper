from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
from bs4 import BeautifulSoup
import time
import re
import json
import pandas as pd
import matplotlib.pyplot as plt

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
        bathroom_count = "N/A"
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
        listing_url = "N/A"
        script_tag = listing.find_next("script", class_="hs-script-home-struct")

        if script_tag:
            try:
                json_data = json.loads(script_tag.string)
                if "address" in json_data and "postalCode" in json_data["address"]:
                    postal_code = json_data["address"]["postalCode"]
                if "url" in json_data:  # ✅ Extracting the URL
                    listing_url = json_data["url"]
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
            "Postal Code": postal_code,
            "Listing URL": listing_url
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

# Function to categorize bedrooms
def categorize_bedrooms(bedroom):
    if pd.isna(bedroom) or bedroom in ["N/A", ""]:
        return bedroom  # Keep as-is for missing data
    
    # Extract the first number from the bedroom string
    numbers = re.findall(r'\d+', str(bedroom))
    if numbers:
        first_number = int(numbers[0])  # Only consider the first number
        return "3+" if first_number >= 3 else bedroom  # Change only if 3 or greater

    return bedroom  # Keep original if no valid number is found

def save_table_as_image(df, filename, col_widths=None, font_size=12, header_font_size=13, fig_width=14):
    """
    Save a pandas DataFrame as a formatted image.

    Args:
        df (DataFrame): The DataFrame to display.
        filename (str): The output image filename (e.g., 'table.png').
        col_widths (list, optional): List of custom column widths. If None, auto-calculated.
        font_size (int): Font size for table content.
        header_font_size (int): Font size for header row.
        fig_width (int): Width of the figure for the table.
    """
    num_columns = len(df.columns)

    # Auto-calculate column widths if not provided
    if col_widths is None:
        col_widths = [1 / num_columns] * num_columns  # Equal width for all columns

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(fig_width, len(df) * 0.6))
    ax.axis('off')  # Hide axes

    # Create the table
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc='center',
        cellLoc='center',
        colLoc='center'
    )

    # Adjust font sizes
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    table.scale(1.3, 1.4)  # Adjust scaling for better fit

    # Apply column widths dynamically
    for key, cell in table.get_celld().items():
        cell.set_text_props(ha='center', va='center')
        if key[0] == 0:  # Header row
            cell.set_fontsize(header_font_size)
        if key[1] < len(col_widths):
            cell.set_width(col_widths[key[1]])

    # Save as a high-resolution image
    plt.savefig(filename, bbox_inches='tight', dpi=300)
    plt.close()  # Close the figure to free up memory

# function to extract data from listing URL
def save_listing_url_html(driver, url, unit_type):
    """
    Access a HouseSigma listing URL using an active Selenium session
    and save the full HTML content to a file for inspection.

    Args:
        driver: Selenium WebDriver instance (with an active logged-in session).
        url: Listing URL to extract data from.
    """
    try:
        driver.get(url)
        # print(f"\n🚀 Accessing: {url}")
        time.sleep(5)  # Wait for the page to fully load

        soup = BeautifulSoup(driver.page_source, "html.parser")

        days_sold_ago = "N/A"
        dom_tag = soup.find("p", class_="dom")  # Looking for <p class="dom">
        if dom_tag:
            text = dom_tag.text.strip()
            if " day ago" in text:
                days_sold_ago = "1"
            elif " days ago" in text:
                days_sold_ago = text.replace("Sold ", "").replace(" days ago", "").strip()

        # ✅ Extract Maintenance Fees (Only for Condos)
        maintenance_fees = "N/A"
        if "Condo" in unit_type:  # Only extract maintenance fees for condos
            maintenance_label = soup.find("span", string="Maintenance:")
            if maintenance_label:
                maintenance_value = maintenance_label.find_next("span")  # Get the value after "Maintenance:"
                if maintenance_value:
                    maintenance_fees = maintenance_value.text.strip()
    
        # ✅ Extract Unit Description from JSON inside <script class="hs-script">
        unit_description = "N/A"
        script_tag = soup.find("script", class_="hs-script")
        if script_tag:
            try:
                json_data = json.loads(script_tag.string)
                if "description" in json_data:
                    unit_description = json_data["description"].strip()
            except json.JSONDecodeError:
                print("❌ Error decoding JSON from hs-script tag")

        # print(f"Unit {unit_type}   - Sold Days Ago: {days_sold_ago}")
        # print(f"   - Maintenance Fees: {maintenance_fees}")
        # print(f"   - Unit Description: {unit_description[:100]}...") # Display only the first 100 characters

        return {
            "Sold Days Ago": days_sold_ago,
            "Maintenance Fees": maintenance_fees,
            "Unit Description": unit_description
        }

    except Exception as e:
        print(f"❌ Error accessing {url}: {e}")