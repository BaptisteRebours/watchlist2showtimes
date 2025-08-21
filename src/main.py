### --- Imports ---
print("Imports...")
import requests
from bs4 import BeautifulSoup
import urllib
from pprint import pprint
import json
from collections import defaultdict
import random
import time
from datetime import datetime, timedelta
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from dotenv import load_dotenv
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils import (
    build_index, 
    find_closest_id, 
    google_maps_link,
    safe_get
)
from utils import (
    ALLOCINE_CITIES_PATH, 
    ALLOCINE_FILMS_PATH, 
    USERS_INFO_PATH,
    WATCHLIST_PATH,
    WATCHLIST_FILENAME,
    PROGRAMME_PATH,
    PROGRAMME_FILENAME,
    URL_LETTERBOXD,
    URL_ALLOCINE_SHOWTIMES,
)


### --- Settings scraping ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
})
retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)


### --- Loading data ---
print("Loading data...")
with open(ALLOCINE_FILMS_PATH, "r", encoding='utf-8') as file:
    allocine_films = json.load(file)

with open(ALLOCINE_CITIES_PATH, "r", encoding='utf-8') as file:
    allocine_cities_id = json.load(file)

with open(USERS_INFO_PATH, "r", encoding='utf-8') as file:
    users_info = json.load(file)


### --- Parameters ---
print("Parameters...")

## Secret parameters
load_dotenv()
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_PWD = os.getenv("EMAIL_PWD")

## User parameters
user = users_info[0]
user_name = user['lb_profile_id']
user_email = user['email_address']
user_city_id = allocine_cities_id[user['city']]
user_departments_subset = user['departments_subset']

## Date parameters
date_today = datetime.today().strftime('%Y-%m-%d')
date_max = (datetime.today() + timedelta(days=30)).strftime('%Y-%m-%d')


### --- Scraping watchlist movies showtimes ---
print("Scraping watchlist movies showtimes...")

## Watchlist's number of pages
print("Finding watchlist's number of pages...")
link_user_watchlist = f"{user_name}/watchlist/"
url_watchlist = urllib.parse.urljoin(URL_LETTERBOXD, link_user_watchlist)
r = session.get(url_watchlist)
soup = BeautifulSoup(r.content, 'html.parser')
div_pages = soup.find("div", class_="paginate-pages")
if div_pages:
    nb_pages = int(div_pages.find_all("a")[-1].get_text())
else:
    nb_pages = 1
print(f"Pages total: {nb_pages}")

## Watchlist movies
print("Retrieving watchlist movies...")
watchlist_movies = {}
for page_num in range(1, nb_pages):

    # Avoid blocking
    print(f"Page {page_num}")
    time.sleep(random.uniform(10, 30))

    # Retrieve watchlist page x movies
    link_page = f"page/{page_num}"
    url_watchlist_page = urllib.parse.urljoin(url_watchlist, link_page)
    r_page = safe_get(url_watchlist_page, session)
    if not r_page:
        print(f"[SKIP] Impossible to retrieve {url_watchlist_page}")
        continue
    soup_page = BeautifulSoup(r_page.content, 'html.parser')
    div_movies = soup_page.find_all("li", class_="poster-container")

    # Retrieve movie info
    for m, mov in enumerate(div_movies):

        # Avoid blocking
        print(f"Movie {m+1}")
        time.sleep(random.uniform(10, 30))

        # Retrieve movie url
        slug_movie = mov.find("div").get("data-film-slug")
        link_movie = f"film/{slug_movie}"
        url_movie = urllib.parse.urljoin(URL_LETTERBOXD, link_movie)

        # Retrieve movie info: title, original title if available, year and poster
        r_movie = safe_get(url_movie, session)
        if not r_movie:
            print(f"[SKIP] Impossible to retrieve {url_movie}")
            continue
        soup_movie = BeautifulSoup(r_movie.content, 'html.parser')
        div_details = soup_movie.find("div", class_="details")
        # titles
        movie_title = div_details.find("h1", class_="headline-1").find('span').get_text()
        original_bool = div_details.find("h2", class_="originalname")
        movie_original_title = original_bool.find("em").get_text() if original_bool else None
        # year
        movie_year = div_details.find('span', class_="releasedate").get_text().strip() if div_details.find('span', class_="releasedate") else None
        
        # Append movie to watchlist dict
        watchlist_movies[slug_movie] = {
            "lb_title": movie_title,
            "lb_url": url_movie,
            "lb_year": movie_year,
            "lb_original_title": movie_original_title,
        } 

# Export watchlist movies
print("Exporting watchlist movies...")
user_watchlist_path = WATCHLIST_PATH + user_name + WATCHLIST_FILENAME
with open(user_watchlist_path, "w", encoding="utf-8") as f:
    json.dump(watchlist_movies, f, ensure_ascii=False, indent=2)


## Allocine movie info
print("Retrieving Allocine movie info...")
allocine_title_to_id_year = build_index(allocine_films)

for lb_id, lb_movie in watchlist_movies.items():
    lb_title_request = lb_movie.get("lb_original_title") or lb_movie.get("lb_title")
    lb_year = lb_movie.get("lb_year")
    ac_id = find_closest_id(lb_title_request, allocine_title_to_id_year, lb_year)
    lb_movie.update({'ac_id': ac_id})


## Look for movies showtimes
print("Looking for movies showtimes...")
all_films_showtimes = {}

for lb_id, lb_movie in watchlist_movies.items():
    film_id = lb_movie["ac_id"]
    if film_id:
        link_movie_near = f"movie-{film_id}/near-{user_city_id}/d-"
        url_film = urllib.parse.urljoin(URL_ALLOCINE_SHOWTIMES, link_movie_near)
        next_date = date_today
        film_showtimes = []
        while next_date and next_date <= date_max:
            url_film_date = url_film + next_date
            res = session.get(url_film_date)
            if res.status_code == 200:
                results = res.json()['results']
                if results:
                    film_showtimes.extend(
                        [
                            {
                                'theater_name': elem['theater']['name'],
                                'theater_full_address': ' '.join(
                                    [
                                        elem['theater']['location']['address'],
                                        elem['theater']['location']['zip'],
                                        elem['theater']['location']['city']
                                    ]
                                ),
                                'theater_maps': google_maps_link(elem['theater']['location']['address'] + elem['theater']['location']['zip'] + elem['theater']['location']['city']),
                                'theater_showtimes': [
                                    (showtime['startsAt'], showtime['diffusionVersion'])
                                    for showtime in sum(elem['showtimes'].values(), [])
                                ],
                                'theater_tickets': elem['theater']['loyaltyCards']
                            }
                            for elem in results if
                            any(elem['theater']['location']['zip'].startswith(dept_ok) for dept_ok in user_departments_subset)
                        ]
                    )
                    next_date = (datetime.strptime(next_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    next_date = res.json()['nextDate']
    else:
        film_showtimes = []

    all_films_showtimes[lb_id] = {
        'ac_id': film_id,
        'showtimes': film_showtimes,
    }


# Export movies showtimes
print("Exporting movies showtimes...")
user_programme_path = PROGRAMME_PATH + user_name + "_" + date_today + PROGRAMME_FILENAME
with open(user_programme_path, "w", encoding="utf-8") as f:
    json.dump(all_films_showtimes, f, ensure_ascii=False, indent=2)




### --- Process output for email ---
print("Processing output for email...")
all_films_showtimes_by_day = {}
for lb_id, showtimes_info in all_films_showtimes.items():
    daily_info = defaultdict(list)
    for theater in showtimes_info['showtimes']:
        theater_name = theater['theater_name']
        theater_address = theater['theater_full_address']
        theater_maps = theater['theater_maps']
        theater_tickets = theater['theater_tickets']
        for showtime in theater['theater_showtimes']:
            showtime_day_date = datetime.strptime(showtime[0].split('T')[0], '%Y-%m-%d')
            showtime_day_number = datetime.strftime(showtime_day_date,'%d')
            showtime_day_name = datetime.strftime(showtime_day_date,'%A')
            showtime_month_name = datetime.strftime(showtime_day_date,'%B')
            showtime_year = datetime.strftime(showtime_day_date,'%Y')
            showtime_date_name = ' '.join([showtime_day_name, showtime_day_number, showtime_month_name, showtime_year])
            showtime_hour = showtime[0].split('T')[1][:5].replace(':','h')
            if (showtime_hour >= "18h00") | (showtime_day_name in ['Saturday', 'Sunday']):
                daily_info[showtime_date_name].append(
                    {
                        'theater_name': theater_name,
                        'theater_address': theater_address,
                        'theater_maps': theater_maps,
                        'showtime_hour': showtime_hour,
                        'theater_tickets': theater_tickets,
                    }
                )
    all_films_showtimes_by_day[lb_id] = dict(daily_info)



### --- Send email ---
print("Sending email...")
if all_films_showtimes_by_day:   
    
    context = ssl.create_default_context()
    message = MIMEMultipart("alternative")
    message["Subject"] = "Films au cinema - " + date_today
    message["From"] = EMAIL_SENDER
    
    missing_allocine = []
    
    # Email body
    html = """\
    <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">        
        </head>
        <body>
            <div class="container">
    """
    
    for lb_id, film_showtimes in all_films_showtimes_by_day.items():
        if not film_showtimes:
            # no showtime, checking if ac_id problem
            if not (all_films_showtimes.get(lb_id, {}).get("ac_id")):
                missing_allocine.append({
                    "lb_title": watchlist_movies[lb_id]["lb_title"],
                    "lb_url": watchlist_movies[lb_id]["lb_url"],
                })
            continue

        ac_id = (all_films_showtimes.get(lb_id) or {}).get("ac_id")
        if not ac_id or ac_id not in allocine_films:
            # no ac_id: add to missing_allocine to alert user
            missing_allocine.append({
                "lb_title": watchlist_movies[lb_id]["lb_title"],
                "lb_url": watchlist_movies[lb_id]["lb_url"],
            })
            continue

        film_name  = allocine_films[ac_id].get("ac_title") or "Titre inconnu"
        film_poster = allocine_films[ac_id].get("ac_poster") or "https://via.placeholder.com/120x180?text=No+Poster"

        # Movie card
        html += f"""\
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
            style="margin-bottom:30px; background:#ffffff; border:1px solid #ddd; border-radius:10px; overflow:hidden;">
        <tr>
            <!-- colonne affiche -->
            <td width="120" valign="top" style="padding:12px;">
            <img src="{escape(film_poster)}" alt="Affiche de {escape(film_name)}" width="120" height="180"
                style="display:block; width:120px; height:180px; border-radius:6px; border:0; outline:none;">
            </td>

            <!-- colonne texte -->
            <td valign="top" style="padding:12px 16px; font-family:Arial,Helvetica,sans-serif;">
            <h2 style="margin:0 0 8px 0; font-size:20px; font-weight:bold; color:#EF0107;">
                {escape(film_name)}
            </h2>
        """

        # Showtimes per day
        for showtime_day, showtime_infos in film_showtimes.items():
            html += f"""\
            <div style="margin:10px 0;">
                <div style="background:#f9f2dc; color:#9C824A; font-size:15px; font-weight:bold;
                            padding:6px 10px; border-radius:4px; display:inline-block; margin-bottom:6px;">
                {escape(str(showtime_day))}
                </div>
                <ul style="margin:0; padding-left:20px; font-size:14px; line-height:1.5; color:#333;">
            """
            for info in showtime_infos:
                hour = escape(info["showtime_hour"])
                t_name = escape(info["theater_name"])
                t_maps = escape(info["theater_maps"])
                html += f"""\
                <li style="margin:0 0 6px 0;">
                    {hour} :
                    <a href="{t_maps}" target="_blank" style="color:#1a73e8; text-decoration:none;">
                    Cinéma {t_name}
                    </a>
                </li>
                """
            html += "</ul></div>"

        html += """\
            </td>
        </tr>
        </table>
        """

    # Missing movies card
    if missing_allocine:
        html += """\
        <div style="background:#fff3cd; border:1px solid #ffeeba; color:#654d03;
                    border-radius:8px; padding:16px; margin:28px 0; font-family:Arial,Helvetica,sans-serif;">
        <div style="font-weight:700; font-size:18px; margin-bottom:8px;">
            Info non trouvée via Allociné
        </div>
        <div style="font-size:14px; margin-bottom:8px;">
            Erreur pour faire le pont entre Letterboxd et Allociné pour ces films :
        </div>
        <ul style="margin:0 0 0 18px; padding:0; font-size:14px; line-height:1.5;">
        """
        for missing_movie in missing_allocine:
            html += f"""\
            <li>
            <a href="{escape(missing_movie['lb_url'])}" target="_blank" style="color:#1a73e8; text-decoration:underline;">
                {escape(missing_movie['lb_title'])}
            </a>
            </li>
            """
        html += """\
        </ul>
        </div>
        """

    html += """\
        </div>
        </body>
    </html>
    """
    
    corps_mail = MIMEText(html, "html")
    message.attach(corps_mail)
    
    with smtplib.SMTP_SSL("smtp.gmail.com", port=EMAIL_PORT, context=context) as server:
        server.login(user=EMAIL_SENDER, password=EMAIL_PWD)
        server.sendmail(from_addr=EMAIL_SENDER, to_addrs=user_email, msg=message.as_string())


else:
    print("Aucun film de votre watchlist n'est programmé au cinéma actuellement !")




