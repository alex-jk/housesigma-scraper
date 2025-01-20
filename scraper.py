from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def fetch_sold_listings(url):
    options = webdriver.ChromeOptions()

    # Use your existing Chrome profile
    options.add_argument("user-data-dir=C:/Users/Lenovo Thinkpad T430/AppData/Local/Google/Chrome/User Data")

    # Fix issues with DevToolsActivePort
    options.add_argument("--remote-debugging-port=9222")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")  
    options.add_argument("--headless=new")  # If you want to run without opening Chrome
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    driver.get(url)

    # Wait for the page to load
    time.sleep(10)

    # Save the page source for inspection
    html = driver.page_source
    with open("logged_in_page_source.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("Logged-in page source saved. Open 'logged_in_page_source.html' to verify.")

    driver.quit()
    
    return []

if __name__ == "__main__":
    url = "https://housesigma.com/on/sold/map/?status=sold&lat=43.715564&lon=-79.418602&zoom=10&page=1&view=list"
    fetch_sold_listings(url)