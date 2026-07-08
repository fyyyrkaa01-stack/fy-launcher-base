import json
import cloudscraper
from bs4 import BeautifulSoup
import re
import urllib.parse
import requests

def parse_plugins():
    parsed_plugins = []
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    url = "https://vsthouse.ru/"
    headers = {
