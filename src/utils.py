### --- Imports ---
import urllib
import difflib
from collections import defaultdict


### --- Parameters ---

# Scraping parameters
URL_LETTERBOXD = "https://letterboxd.com/"
URL_ALLOCINE = "https://www.allocine.fr"
URL_ALLOCINE_SHOWTIMES = "https://www.allocine.fr/_/showtimes/"

# Input / output parameters
ALLOCINE_CITIES_PATH = "./data/input/allocine_cities_id.json"
ALLOCINE_FILMS_PATH = "./data/input/allocine_films.json"
USERS_INFO_PATH = "./data/input/users_info.json"
WATCHLIST_PATH = "./data/output/watchlist_films/"
WATCHLIST_FILENAME = "_watchlist_films.json"
PROGRAMME_PATH = "./data/output/cinema_programme/"
PROGRAMME_FILENAME = "_programme.json"




### --- Functions ---
def build_index(films: dict) -> dict[str, list[str]]:
    """Creates title_to_id_year = {title: [{id, year}]}
    
    """
    title_to_id_year = defaultdict(list)
    for film_id, film in films.items():
        candidate_title = film.get("ac_original_title") or film.get("ac_title")
        candidate_year = film.get("ac_year")
        if candidate_title:
            title_to_id_year[candidate_title].append({'ac_id':film_id, 'ac_year':candidate_year})
    return title_to_id_year

def find_closest_id(target: str, title_to_id_year: dict, year: str = None) -> str | None:
    """Finds closest movie to target, based on movie title, and filtered on movie year
    
    """
    possible_years = [str(int(year) + offset) for offset in range(-5, 6)]
    candidates = list(title_to_id_year.keys())
    matches = difflib.get_close_matches(target, candidates, n=10, cutoff=0.0)
    match_year = None
    if matches:
        if year:
            match_year = [elem for sublist in [title_to_id_year[match] for match in matches] for elem in sublist if elem['ac_year'] in possible_years]
        else:
            match_year = title_to_id_year[matches[0]]
    match_id = match_year[0]['ac_id'] if match_year else None
    return match_id 

def google_maps_link(address: str) -> str:
    """Transforms an address to its Google Maps URL
    
    """
    query = urllib.parse.quote(address)
    return f"https://www.google.com/maps/search/?api=1&query={query}"