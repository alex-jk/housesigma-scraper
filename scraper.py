from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

# Use the extracted access token
ACCESS_TOKEN = "20241223l8341c1kjjish4povs28u7jn0t"  # Replace this with your actual access_token

def fetch_sold_listings(url):
    options = webdriver.ChromeOptions()
    #options.debugger_address = "127.0.0.1:9222"  # Attach to running Chrome

    # options.add_argument(r"user-data-dir=C:\Users\Lenovo Thinkpad T430\AppData\Local\Google\Chrome\User Data")
    # options.add_argument("--profile-directory=Default")  # Adjust if you use a different profile

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

if __name__ == "__main__":
    url = "https://housesigma.com/on/sold/map/?status=sold&lat=43.715564&lon=-79.418602&zoom=10&page=1&view=list"
    fetch_sold_listings(url)