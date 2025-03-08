import requests
import time
import re
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from sklearn.base import BaseEstimator, TransformerMixin
import pgeocode
from geopy.distance import geodesic
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib.pyplot as plt

import nltk
from nltk.corpus import stopwords

# Download stopwords only if not already present
try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords')

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

                # Log missing values
                if lat is None or lon is None or np.isnan(lat) or np.isnan(lon):
                    print(f"Warning: Missing coordinates for postal code '{pc}' at index {idx}")
               
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

class BedroomSplitter(BaseEstimator, TransformerMixin):
    """
    Scikit-learn transformer that splits the 'Bedrooms' column into 'Main_Bedrooms' and 'Extra_Bedrooms'.
    """
    def __init__(self, bedroom_col='Bedrooms'):
        self.bedroom_col = bedroom_col

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_transformed = X.copy()
        
        def split_bedrooms(bedroom_str):
            parts = bedroom_str.split("+")
            main_bedrooms = int(parts[0])  # First number is main bedrooms
            extra_bedrooms = int(parts[1]) if len(parts) > 1 else 0  # Second number (if exists) is extra space
            return main_bedrooms, extra_bedrooms

        X_transformed[['Main_Bedrooms', 'Extra_Bedrooms']] = X_transformed[self.bedroom_col].astype(str).apply(lambda x: pd.Series(split_bedrooms(x)))
        # X_transformed.drop(columns=[self.bedroom_col], inplace=True)
        
        return X_transformed

def find_best_num_topics(X, text_col, max_topics=10):
    """
    Finds the optimal number of topics by checking reconstruction error.
    """
    tfidf_vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words='english',
        ngram_range=(1,3),
        token_pattern=r"(?u)\b\w[\w']+\b",  # Keeps words + contractions (like don't, can't)
        sublinear_tf=True,
        min_df=2
    )
    tfidf_matrix = tfidf_vectorizer.fit_transform(X[text_col])

    errors = []
    topics_range = range(2, max_topics + 1)  # Try 2 to max_topics

    for num_topics in topics_range:
        nmf_model = NMF(n_components=num_topics, random_state=42)
        nmf_model.fit(tfidf_matrix)
        error = nmf_model.reconstruction_err_
        errors.append(error)

    # Plot error vs. number of topics
    plt.figure(figsize=(8,5))
    plt.plot(topics_range, errors, marker='o', linestyle='-')
    plt.xlabel("Number of Topics")
    plt.ylabel("Reconstruction Error")
    plt.title("Choosing the Best Number of Topics")
    plt.show()

class NMFTopicExtractor(BaseEstimator, TransformerMixin):
    """
    Scikit-learn transformer that extracts topics from text data using NMF.
    """
    def __init__(self, text_col='Unit Description', num_topics=5, max_features=500):
        self.text_col = text_col
        self.num_topics = num_topics
        self.max_features = max_features
        self.tfidf_vectorizer = None
        self.nmf_model = None
        self.custom_stopwords = set(stopwords.words('english')).union({"just"})

    def custom_preprocessor(self, text):
        text = text.lower()  # Convert to lowercase
        text = re.sub(r'\b\d+\b', '', text)  # Remove standalone numbers like "24"
        return text

    def fit(self, X, y=None):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words=list(self.custom_stopwords),  # Use custom stopwords
            ngram_range=(1,3),
            token_pattern=r"(?u)\b\w[\w']+\b",  # Keeps words + contractions (like don't, can't)
            sublinear_tf=True,
            min_df=2,
            preprocessor=self.custom_preprocessor  # Custom function to remove numbers
        )
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(X[self.text_col])
        
        self.nmf_model = NMF(n_components=self.num_topics, random_state=42)
        self.nmf_model.fit(tfidf_matrix)
        
        # Print top words for each topic with weights rounded to 2 decimal places, removing np.float64 formatting
        feature_names = self.tfidf_vectorizer.get_feature_names_out()
        for topic_idx, topic in enumerate(self.nmf_model.components_):
            top_word_indices = topic.argsort()[:-11 - 1:-1]  # Get top 10 words
            top_words = [(feature_names[i], format(topic[i], ".2f")) for i in top_word_indices]  # Format weights
            print(f"Topic {topic_idx + 1}: {top_words}")
        
        return self

    def transform(self, X):
        tfidf_matrix = self.tfidf_vectorizer.transform(X[self.text_col])
        topic_distributions = self.nmf_model.transform(tfidf_matrix)
        
        topic_features = pd.DataFrame(topic_distributions, columns=[f'Topic_{i+1}' for i in range(self.num_topics)], index=X.index)

        X_transformed = pd.concat([X, topic_features], axis=1)
        X_transformed.drop(columns=[self.text_col], inplace=True)

        return X_transformed