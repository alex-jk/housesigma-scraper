import requests
from bs4 import BeautifulSoup
import time
import re

def get_lat_lon_from_geonames(postal_code_area):
    """
    Scrapes the GeoNames postal code search page for the given postal code (CA)
    and returns (latitude, longitude) from the first result found.
    Returns (None, None) if no lat/lon is found.
    """
    base_url = "https://www.geonames.org/postalcode-search.html"
    params = {
        'q': postal_code_area,
        'country': 'CA'
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request error for {postal_code_area}: {e}")
        return None, None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Approach 1: Look for an <a> tag with a specific pattern in its href, then find <small> inside it
    # Example: <a href="/maps/browse_43.779_-79.445.html" rel="nofollow"><small>43.779/-79.445</small></a>
    link_tag = soup.find('a', href=re.compile(r'^/maps/browse_'))
    if not link_tag:
        # If we can't find that link, lat/lon might not exist
        return None, None
    
    small_tag = link_tag.find('small')
    if not small_tag:
        return None, None
    
    latlon_text = small_tag.get_text(strip=True)  # e.g. "43.779/-79.445"
    latlon_text = latlon_text.replace(' ', '')     # remove any spaces "43.779/-79.445"
    parts = latlon_text.split('/')
    if len(parts) != 2:
        return None, None
    
    try:
        lat = float(parts[0])
        lon = float(parts[1])
        return lat, lon
    except ValueError:
        return None, None