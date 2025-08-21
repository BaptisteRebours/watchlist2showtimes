### --- Imports ---
print("Imports...")
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import urllib

from utils import (
    URL_ALLOCINE,
    ALLOCINE_FILMS_PATH
)


### --- Settings scraping ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
})


### --- Parameters ---
print("Parameters...")
pages_total = 5000


### --- Scraping Allocine films ---
print("Scraping Allocine films...")
start = time.time()

all_films = {}
for page_num in range(1, pages_total):
    if page_num % 100 == 0:
        print(page_num)

    # Retrieve page films
    link_page = f"films/?page={page_num}"
    url = urllib.parse.urljoin(URL_ALLOCINE, link_page)
    resp = session.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    page_films = soup.find_all("li", class_="mdl")

    # Retrieve film info for page films
    for film in page_films:

        # title, url and id
        a_tag = film.find("a", class_="meta-title-link")
        if not a_tag:
            continue
        film_title = a_tag.get_text(strip=True)
        film_url = URL_ALLOCINE + a_tag["href"]
        film_id = re.search(r'\d+', film_url).group()

        # poster
        img_tag = film.find("img", class_="thumbnail-img")
        film_poster = None
        if img_tag:
            film_poster = img_tag.get("data-src") or img_tag.get("src")
        
        # year
        year = None
        info_year_div = film.find("div", class_="meta-body-item meta-body-info")
        if info_year_div:
            info_year_text = info_year_div.get_text(" ", strip=True)
            year_match = re.search(r"\b(19|20)\d{2}\b", info_year_text)
            if year_match:
                year = year_match.group()

        # original title
        original_title = None
        info_orig_span = film.find("span", string=lambda t: t and t.strip() == "Titre original")
        if info_orig_span:
            info_orig_text = info_orig_span.find_next_sibling("span")
            if info_orig_text:
                original_title = info_orig_text.get_text(strip=True)

        # Append movie to films dict
        all_films[film_id] = {
            "ac_title": film_title,
            "ac_url": film_url,
            "ac_poster": film_poster,
            "ac_year": year,
            "ac_original_title": original_title,
        }

# Exporting Allocine films
with open(ALLOCINE_FILMS_PATH, "w", encoding="utf-8") as f:
    json.dump(all_films, f, ensure_ascii=False, indent=2)

print(time.time() - start)
