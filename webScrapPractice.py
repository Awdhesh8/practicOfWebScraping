import ssl
import nltk
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from flask_cors import CORS
from cachetools import TTLCache
from time import sleep
import hashlib
from transformers import pipeline

# Fix SSL certificate issue for nltk
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize the paraphrasing pipeline
nltk.download('punkt')
paraphraser = pipeline("text2text-generation", model="t5-small")

# Cache to store fetched news with a TTL of 10 minutes
cache = TTLCache(maxsize=10, ttl=600)

# Rate limiting function (1 request per second)
def rate_limit():
    sleep(1)

# Function to fetch HTML content from a URL
def fetch_html(url):
    rate_limit()
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return None

# Function to find and verify text content within potential title elements
def find_title(article):
    potential_title_tags = ['h1', 'h2', 'h3', 'a']
    for tag in potential_title_tags:
        title_element = article.find(tag)
        if title_element and title_element.get_text(strip=True):
            return title_element.get_text(strip=True)
    return None

# Function to find and verify text content within potential description elements
def find_description(article):
    potential_description_tags = ['p', 'div']
    for tag in potential_description_tags:
        description_element = article.find(tag)
        if description_element and description_element.get_text(strip=True):
            description = description_element.get_text(strip=True)
            if len(description.split()) > 3:  # Basic check to avoid short, menu-like descriptions
                return description
    return None

# Function to find and verify the image URL within potential image elements
def find_image(article):
    lazy_image_element = article.find('lazy-image')
    if lazy_image_element and lazy_image_element.has_attr('src'):
        return lazy_image_element['src']

    img_element = article.find('img')
    if img_element and 'src' in img_element.attrs:
        return img_element['src']

    return None

# Function to find and verify date within potential date elements
def find_date(article):
    date_element = article.find('time')
    if date_element and 'datetime' in date_element.attrs:
        return date_element['datetime']
    return None

# Function to generate a hash for a given string (for deduplication)
def generate_hash(title, description):
    return hashlib.md5(f"{title}{description}".encode()).hexdigest()

# Function to paraphrase text to avoid copyright issues
def paraphrase_text(text):
    paraphrased_text = paraphraser(text, max_length=50, num_return_sequences=1)[0]['generated_text']
    return paraphrased_text

# Function to parse news dynamically with more flexible logic
def parse_news(html, source_name):
    if html is None:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    articles = soup.find_all(['article', 'div', 'section'])
    
    news_items = []
    seen_hashes = set()
    
    for article in articles:
        title = find_title(article)
        description = find_description(article)
        image = find_image(article)
        date = find_date(article)

        if not title or not description:
            continue
        
        article_hash = generate_hash(title, description)
        if article_hash in seen_hashes:
            continue
        
        seen_hashes.add(article_hash)

        title = paraphrase_text(title)
        description = paraphrase_text(description)

        news_items.append({
            'title': title,
            'description': description,
            'image': image if image else 'No Image Found',
            'date': date,
            'source': source_name
        })

    return news_items

@app.route('/')
def home():
    return "Welcome to the News API! Use /news to get news articles."

@app.route('/news', methods=['GET'])
def get_news():
    if 'news' in cache:
        return jsonify(cache['news'])

    sites = {
        'Healthline': {'url': 'https://www.healthline.com/health-news', 'source_name': 'Healthline'},
        'NBC News': {'url': 'https://www.nbcnews.com/health', 'source_name': 'NBC News'},
        'WebMD': {'url': 'https://www.webmd.com/news/default.htm', 'source_name': 'WebMD'},
        'Mayo Clinic': {'url': 'https://www.mayoclinic.org/healthy-lifestyle', 'source_name': 'Mayo Clinic'},
    }

    all_news_items = []
    
    for site_name, config in sites.items():
        html = fetch_html(config['url'])
        if html:
            news_items = parse_news(html, config['source_name'])
            all_news_items.extend(news_items)

    cache['news'] = all_news_items
    return jsonify(all_news_items)

if __name__ == '__main__':
    app.run(debug=True, port=5001)


# --------- IT FETCH THE DATA CORRECTLY -----------
# import requests
# from bs4 import BeautifulSoup
# from flask import Flask, jsonify
# from flask_cors import CORS
# from cachetools import TTLCache
# from time import sleep
# import hashlib

# app = Flask(__name__)
# CORS(app)
# 87
# # Cache to store fetched news with a TTL of 10 minutes
# cache = TTLCache(maxsize=10, ttl=600)

# # Rate limiting function (1 request per second)
# def rate_limit():
#     sleep(1)

# # Function to fetch HTML content from a URL
# def fetch_html(url):
#     rate_limit()  # Ensure we don't make requests too quickly
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         print(f"Successfully fetched data from {url}")
#         return response.text
#     except requests.exceptions.RequestException as e:
#         print(f"Failed to retrieve {url}: {e}")
#         return None

# # Function to dynamically find and verify potential article elements
# def find_articles(soup):
#     potential_article_tags = ['article', 'div', 'section']
#     for tag in potential_article_tags:
#         articles = soup.find_all(tag)
#         if articles:
#             print(f"Found {len(articles)} articles using tag: {tag}")
#             return articles
#     return []

# # Function to find and verify text content within potential title elements
# def find_title(article):
#     potential_title_tags = ['h1', 'h2', 'h3', 'a']
#     for tag in potential_title_tags:
#         title_element = article.find(tag)
#         if title_element and title_element.get_text(strip=True):
#             return title_element.get_text(strip=True)
#     return 'No Title Found'

# # Function to find and verify text content within potential description elements
# def find_description(article):
#     potential_description_tags = ['p', 'div']
#     for tag in potential_description_tags:
#         description_element = article.find(tag)
#         if description_element and description_element.get_text(strip=True):
#             description = description_element.get_text(strip=True)
#             # Ensure that the description is not just a repeated title or menu
#             if len(description.split()) > 3:  # Basic check to avoid short, menu-like descriptions
#                 return description
#     return 'No Description Found'

# # Function to find and verify the image URL within potential image elements
# def find_image(article):
#     # First, look for the 'lazy-image' tag, which may contain the image
#     lazy_image_element = article.find('lazy-image')
#     if lazy_image_element:
#         print("Found lazy-image tag")

#         # Check if it has a 'src' attribute directly
#         if lazy_image_element.has_attr('src'):
#             print(f"Image found directly in lazy-image: {lazy_image_element['src']}")
#             return lazy_image_element['src']
        
#         # Look inside the <picture> tag within 'lazy-image'
#         picture_element = lazy_image_element.find('picture')
#         if picture_element:
#             img_element = picture_element.find('img')
#             if img_element and img_element.has_attr('src'):
#                 print(f"Image found in picture tag: {img_element['src']}")
#                 return img_element['src']

#     # Fallback to a standard <img> tag anywhere in the article
#     img_element = article.find('img')
#     if img_element and 'src' in img_element.attrs:
#         print(f"Fallback image found: {img_element['src']}")
#         return img_element['src']

#     print("No image found")
#     return 'No Image Found'

# def find_date(article):
#     # First, try to find a <time> tag, which is standard for dates
#     date_element = article.find('time')
#     if date_element and 'datetime' in date_element.attrs:
#         print(f"Date found in <time> tag: {date_element['datetime']}")
#         return date_element['datetime']

#     # If no <time> tag, look for a <div> with the specific date class
#     date_div = article.find('div', class_='css-5ry8xk')
#     if date_div:
#         date_text = date_div.get_text(strip=True)
#         print(f"Date found in <div> tag: {date_text}")
#         return date_text
    
#     # Return a default message if no date is found
#     print("No date found")
#     return 'No Date Found'


# # # Function to find and verify date within potential date elements
# # def find_date(article):
# #     date_element = article.find('time')
# #     if date_element and 'datetime' in date_element.attrs:
# #         return date_element['datetime']
# #     return 'No Date Found'

# # Function to generate a hash for a given string (for deduplication)
# def generate_hash(title, description):
#     return hashlib.md5(f"{title}{description}".encode()).hexdigest()

# # Function to parse news dynamically with more flexible logic
# def parse_news(html, source_name):
#     if html is None:
#         print("No HTML data to parse")
#         return []

#     soup = BeautifulSoup(html, 'html.parser')
#     articles = find_articles(soup)
    
#     news_items = []
#     seen_titles = set()
#     seen_hashes = set()
    
#     for article in articles:
#         title = find_title(article)
#         description = find_description(article)
#         image = find_image(article)
#         date = find_date(article)

#         # Skip if title has been seen before
#         if title in seen_titles:
#             continue
        
#         # Generate a hash based on the title and description
#         article_hash = generate_hash(title, description)

#         # Skip duplicates where the title is the same but description differs
#         if article_hash in seen_hashes:
#             continue
        
#         # Add the title to the set of seen titles and hash to seen hashes
#         seen_titles.add(title)
#         seen_hashes.add(article_hash)

#         # Append valid news item
#         if title != 'No Title Found' and description != 'No Description Found':
#             news_items.append({
#                 'title': title,
#                 'description': description,
#                 'image': image if image else 'No Image Found',
#                 'date': date,
#                 'source': source_name
#             })

#     if not news_items:
#         print(f"No valid news items found for source: {source_name}")
    
#     return news_items

# @app.route('/')
# def home():
#     return "Welcome to the News API! Use /news to get news articles."

# @app.route('/news', methods=['GET'])
# def get_news():
#     if 'news' in cache:
#         print("Returning cached news data")
#         return jsonify(cache['news'])

#     sites = {
#         'Healthline': {
#             'url': 'https://www.healthline.com/health-news',
#             'source_name': 'Healthline'
#         },
#         'NBC News': {
#             'url': 'https://www.nbcnews.com/health',
#             'source_name': 'NBC News'
#         }
#     }

#     all_news_items = []
    
#     for site_name, config in sites.items():
#         print(f"Fetching news from {site_name} ({config['url']})")
#         html = fetch_html(config['url'])
#         if html:
#             news_items = parse_news(html, source_name=config['source_name'])
#             all_news_items.extend(news_items)
#             print(f"Found {len(news_items)} news items from {site_name}")
#         else:
#             print(f"Failed to fetch HTML for {site_name}")

#     if all_news_items:
#         print(f"Total news items fetched: {len(all_news_items)}")
#     else:
#         print("No news items fetched from any source")

#     cache['news'] = all_news_items  # Cache the result
#     return jsonify(all_news_items)

# if __name__ == '__main__':
#     app.run(debug=True, port=5001)


