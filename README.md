# watchlist2showtimes

An automated system that monitors your Letterboxd watchlist and sends weekly email notifications about upcoming cinema showtimes for the films you want to watch.

## Overview

watchlist2showtimes bridges the gap between your Letterboxd watchlist and real-world cinema programming. The project was initially created because I wanted to know when and where classic films that I haven't seen and would like to discover on the big screen are being shown.

## Features

- Automated weekly monitoring of Letterboxd watchlists
- Cinema showtime detection via Allocine API
- Email notifications with detailed screening information
- Support for multiple users with personalized location filters
- Smart film matching between Letterboxd, TMDB, and Allocine databases
- Caching system to minimize API calls and improve performance
- Flexible department/region filtering for relevant theaters

## Technologies & Libraries

### Core Technologies
- **Python 3.9+** - Primary programming language
- **Web Scraping** - Letterboxd watchlist extraction
- **REST APIs** - Integration with Allocine and TMDB
- **Email Automation** - HTML email generation and delivery

### Key Libraries
- **Requests** - HTTP client for API calls and web scraping
- **BeautifulSoup4** - HTML parsing for Letterboxd pages
- **urllib** - URL manipulation and encoding
- **smtplib** - Email sending via SMTP
- **python-dotenv** - Environment variable management
- **json** - Data serialization and caching

### External APIs
- **Letterboxd** - Watchlist and film metadata scraping
- **TMDB (The Movie Database)** - Film information, posters, and original titles
- **Allocine** - French cinema showtimes and theater locations

### Methodology

The application follows a weekly automated workflow:

1. **Watchlist Retrieval** - Scrapes Letterboxd profiles to extract all watchlist films with pagination handling
2. **Data Enrichment** - Queries TMDB API for additional metadata (original titles, poster URLs)
3. **Film Matching** - Maps Letterboxd films to Allocine database using fuzzy matching on titles and release years
4. **Showtime Lookup** - Queries Allocine API for upcoming showtimes filtered by user location
5. **Schedule Processing** - Organizes showtimes by date, filters by time preferences (evenings, weekends)
6. **Caching** - Stores film metadata to reduce redundant API calls
7. **Email Generation** - Creates HTML emails with film cards, posters, and theater information
8. **Notification** - Sends personalized emails to each configured user

## Requirements

Python 3.9 or higher is required. Dependencies are listed in `requirements.txt`.

### API Keys Required
- TMDB API token (Bearer token)
- Gmail SMTP credentials for email sending

## Installation

1. Clone the repository:
```bash
git clone https://github.com/BaptisteRebours/watchlist2showtimes.git
cd watchlist2showtimes
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:
```bash
EMAIL_SENDER=your-email@gmail.com
EMAIL_PWD=your-app-password
EMAIL_PORT=465
IMDB_TOKEN=your-tmdb-bearer-token
ONLY_USER=optional-filter-single-user
```

4. Configure user information in `data/input/users_info.json`:
```json
[
  {
    "lb_profile_id": "username",
    "email_address": "user@example.com",
    "city": "Paris",
    "departments_subset": ["75", "92", "93", "94"]
  }
]
```

## Usage

Run the script manually:

```bash
python src/main.py
```

Or use the GitHub Actions workflow for automated weekly execution (configured in `.github/workflows/weekly.yml`).

## Configuration

### User Settings (`users_info.json`)
- `lb_profile_id` - Letterboxd username
- `email_address` - Email recipient
- `city` - City name (must match Allocine database)
- `departments_subset` - French department codes for theater filtering

### Input Data Files
- `allocine_cities_id.json` - Mapping of city names to Allocine city IDs
- `allocine_films.json` - Allocine film database for matching

### Filtering Rules
- Showtimes on weekdays: only evenings (after 18h00)
- Showtimes on weekends: all day
- Date range: today to 30 days ahead
- Theaters: filtered by specified department codes

## Project Structure

```
watchlist2showtimes/
├── .github/
│   └── workflows/
│       └── weekly.yml           # Automated weekly execution schedule
├── data/
│   ├── input/
│   │   ├── allocine_cities_id.json  # City name to Allocine ID mapping
│   │   ├── allocine_films.json      # Allocine film database
│   │   └── users_info.json          # User configuration
│   └── output/
│       ├── cinema_programme/        # Generated showtime schedules per user
│       └── watchlist_films.json     # Cached TMDB film metadata
├── src/
│   ├── main.py                  # Main orchestration and execution logic
│   ├── scraping_all_films.py    # Utility to scrape Allocine film database
│   └── utils.py                 # Helper functions and utilities
├── .env                         # Environment variables (API keys, credentials)
├── .gitignore                   # Git ignore rules
├── README.md                    # Project documentation
└── requirements.txt             # Python dependencies
```

### Key Files Description

- **main.py** - Main entry point that orchestrates the entire workflow: watchlist scraping, API calls, showtime matching, and email sending
- **utils.py** - Helper functions including:
  - `build_index()` - Creates searchable film index from Allocine database
  - `find_closest_id()` - Fuzzy matching algorithm for film identification
  - `google_maps_link()` - Generates Google Maps URLs for theater addresses
  - `safe_get()` - Robust HTTP request wrapper with error handling
  - `tmdb_search_movie()` - TMDB API query wrapper
  - `load_tmdb_cache()` / `save_tmdb_cache()` - Cache management for film metadata
- **scraping_all_films.py** - Standalone script to rebuild the Allocine film database
- **watchlist_films.json** - Cache file storing TMDB metadata to minimize API calls
- **cinema_programme/** - Output directory containing per-user showtime schedules in JSON format

## Automation

The project includes a GitHub Actions workflow (`weekly.yml`) that automatically executes the script on a weekly schedule to keep users informed about new cinema programming.

## Email Notifications

The system generates HTML emails featuring:
- Film cards with posters from TMDB/Allocine
- Organized showtimes by date and theater
- Google Maps links for theater locations
- Warning section for films that couldn't be matched in the Allocine database

## Error Handling

- Retry strategy with exponential backoff for HTTP requests
- Graceful handling of missing film matches
- User-level error isolation (one user failure doesn't block others)
- Detailed logging for debugging

## Limitations

- Limited to French theaters via Allocine API
- Letterboxd scraping depends on site structure stability
- TMDB API rate limits apply
- Email sending requires Gmail SMTP or alternative configuration

## Contributing

Contributions are welcome. Please ensure code follows the existing style and includes appropriate error handling.

## Disclaimer

This tool is intended for personal use only. Users are responsible for ensuring their usage complies with Letterboxd, Allocine, and TMDB terms of service.