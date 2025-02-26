import requests
import time
import re
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from sklearn.base import BaseEstimator, TransformerMixin
import pgeocode

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

class PostalCodeGeocoder(BaseEstimator, TransformerMixin):
    """
    Minimal scikit-learn style transformer that uses pgeocode to convert
    Canadian postal codes into latitude, longitude, place name, and province,
    by replicating the exact simple loop approach you provided.
    """
    def __init__(self, postal_code_col='Postal Code Area'):
        self.postal_code_col = postal_code_col
        self.nomi_ = None

    def fit(self, X, y=None):
        # Just initialize pgeocode for Canada once.
        self.nomi_ = pgeocode.Nominatim('ca')
        return self

    def transform(self, X):
        # Make a copy so as not to modify the original DataFrame
        X_transformed = X.copy()
        
        # Prepare lists to hold the new column values
        lat_list = []
        lon_list = []
        place_list = []
        province_list = []
        
        # Exactly like your working loop
        for pc in X_transformed[self.postal_code_col]:
            result = self.nomi_.query_postal_code(pc)
            # If pgeocode returns a valid Series, extract its fields;
            # otherwise, store None for that row.
            if result is not None and not result.isnull().all():
                lat_list.append(result.latitude)
                lon_list.append(result.longitude)
                place_list.append(result.place_name)
                province_list.append(result.state_name)
            else:
                lat_list.append(None)
                lon_list.append(None)
                place_list.append(None)
                province_list.append(None)
        
        # Add the new columns to the DataFrame
        X_transformed['Latitude'] = lat_list
        X_transformed['Longitude'] = lon_list
        X_transformed['Place'] = place_list
        X_transformed['Province'] = province_list
        
        return X_transformed