import requests
import time
import re
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from sklearn.base import BaseEstimator, TransformerMixin
import pgeocode
from geopy.distance import geodesic

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
    Scikit-learn style transformer that converts Canadian postal codes into latitude, longitude,
    and calculates distances to specific locations using the Haversine formula.
    """
    def __init__(self, postal_code_col='Postal Code Area'):
        self.postal_code_col = postal_code_col
        self.nomi_ = None
        self.locations = [
            (43.77972166228427, -79.41577970909104), # Yonge & Finch
            (43.744946273470774, -79.48573172067134), # Keele & Sheppard
            (43.707544839260656, -79.3967682130005), # Yonge & Eglinton
            (43.69848559097772, -79.43710863540463), # Eglinton & Allen Road
            (43.68639927115253, -79.40213796153654), # Bloor & Avenue
            (43.645576441425234, -79.38164588495839) # Union Station
        ]

    def fit(self, X, y=None):
        self.nomi_ = pgeocode.Nominatim('ca')
        return self

    def transform(self, X):
        X_transformed = X.copy()
        
        lat_list = []
        lon_list = []
        distance_lists = [[] for _ in range(len(self.locations))]
        
        for pc in X_transformed[self.postal_code_col]:
            result = self.nomi_.query_postal_code(pc)
            if result is not None and not result.isnull().all():
                lat, lon = result.latitude, result.longitude
                lat_list.append(lat)
                lon_list.append(lon)
                
                for i, loc in enumerate(self.locations):
                    if lat is not None and lon is not None:
                        distance = geodesic((lat, lon), loc).km
                    else:
                        distance = None
                    distance_lists[i].append(distance)
            else:
                lat_list.append(None)
                lon_list.append(None)
                for i in range(len(self.locations)):
                    distance_lists[i].append(None)
        
        X_transformed['Latitude'] = lat_list
        X_transformed['Longitude'] = lon_list
        
        for i, loc in enumerate(self.locations):
            X_transformed[f'Distance_to_Location_{i+1}'] = distance_lists[i]
        
        return X_transformed

# transformer for Unit Type column
class UnitTypeEncoder(BaseEstimator, TransformerMixin):
    """
    Scikit-learn transformer that converts categorical 'Unit Type' column into dummy variables (one-hot encoding).
    """
    def __init__(self, unit_type_col='Unit Type'):
        self.unit_type_col = unit_type_col

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_transformed = X.copy()
        dummies = pd.get_dummies(X_transformed[self.unit_type_col], prefix=self.unit_type_col)
        X_transformed = pd.concat([X_transformed, dummies], axis=1)
        X_transformed.drop(columns=[self.unit_type_col], inplace=True)
        return X_transformed