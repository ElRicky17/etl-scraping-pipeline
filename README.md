# Sports Data Warehouse

A data engineering project with two independent modules: a MercadoLibre web scraper with MongoDB persistence, and a multi-sport ETL pipeline that loads data from a REST API into a PostgreSQL star schema via MongoDB as a staging layer.

---

## Repository Structure

```
sports-data-warehouse/
├── Punto1/          # MercadoLibre scraper + MongoDB queries
└── Punto2/          # Sports API ETL → MongoDB → PostgreSQL
```

---

## Module 1 — MercadoLibre Scraper

### What it does

- Scrapes MercadoLibre Colombia product listings using Selenium + BeautifulSoup.
- Supports pagination up to page X via a configurable parameter.
- Extracts product title, price, URL, and category for each result.
- Stores all results in MongoDB.
- Runs extractions for at least 2 different search keywords.
- Runs analytical queries on the collected data using PyMongo aggregations.

### Keywords used

- `computador`
- `bicicleta`

### Analytical Queries

| # | Question |
|---|----------|
| 1 | How many products were extracted per category? *(aggregation)* |
| 2 | What is the cheapest product in each category? |
| 3 | What is the average price per category? |
| 4 | Which products have a price above 1,000,000 COP? |

### Tech Stack

- Python 3
- Selenium + ChromeDriver
- BeautifulSoup 4
- PyMongo
- MongoDB

### Setup

1. Install dependencies:
   ```bash
   pip install selenium beautifulsoup4 pymongo
   ```

2. Make sure ChromeDriver is installed and matches your Chrome version.

3. Set your MongoDB connection string in a `.env` file or environment variable:
   ```env
   MONGO_URI=mongodb://localhost:27017
   ```

4. Run the scraper:
   ```bash
   python scraper.py
   ```

---

## Module 2 — Sports Data Warehouse (ETL)

### What it does

- Pulls game data for 3 sports (**basketball**, **handball**, **volleyball**) from [API-Sports](https://dashboard.api-football.com/).
- Loads raw responses into MongoDB (one collection per sport).
- Transforms and loads the data into a PostgreSQL **star schema**.

### Star Schema

```
                    ┌─────────────┐
                    │  dim_date   │
                    └──────┬──────┘
                           │
┌──────────────┐    ┌──────┴──────┐    ┌───────────────┐
│  dim_league  ├────┤  fact_game  ├────┤   dim_team    │
└──────────────┘    └──────┬──────┘    └───────────────┘
                           │
              ┌────────────┼────────────┐
       ┌──────┴──────┐           ┌──────┴──────┐
       │ dim_country │           │  dim_status │
       └─────────────┘           └─────────────┘
```

#### Dimension Tables

| Table | Key Columns |
|-------|-------------|
| `dim_date` | `date_id`, `full_date`, `year`, `month`, `day`, `week` |
| `dim_team` | `team_id`, `team_name`, `team_logo` |
| `dim_league` | `league_id`, `league_name`, `league_type`, `season`, `league_logo` |
| `dim_country` | `country_id`, `country_name`, `country_code`, `country_flag` |
| `dim_status` | `status_id`, `status_long`, `status_short` |

#### Fact Table

| Table | Key Columns |
|-------|-------------|
| `fact_game` | `game_id`, `sport`, `date_id`, `league_id`, `country_id`, `status_id`, `home_team_id`, `away_team_id`, `venue`, `home_total`, `away_total`, `period1–5 home/away` |

### Tech Stack

- Python 3
- Requests
- PyMongo
- Psycopg2
- MongoDB
- PostgreSQL

### Setup

1. Install dependencies:
   ```bash
   pip install requests pymongo psycopg2-python
   ```

2. Configure your environment variables:
   ```env
   MONGO_URI=mongodb://localhost:27017
   PG_HOST=localhost
   PG_DB=sports_dw
   PG_USER=postgres
   PG_PASSWORD=your_password
   API_SPORTS_KEY=your_api_key
   ```

3. Create the PostgreSQL schema:
   ```bash
   psql -U postgres -d sports_dw -f schema.sql
   ```

4. Run the extract phase (loads raw data into MongoDB):
   ```bash
   python pipeline.py --extract
   ```

5. Run the load phase (transforms MongoDB → PostgreSQL):
   ```bash
   python pipeline.py --load
   ```

### Sports & Period Mapping

| Sport | Score Fields | Period Fields |
|-------|-------------|---------------|
| Basketball | `scores.home.total` / `scores.away.total` | `quarter_1` to `over_time` |
| Handball | `scores.home` / `scores.away` | `periods.first` to `periods.fifth` |
| Volleyball | `scores.home` / `scores.away` | `periods.first` to `periods.fifth` |

---

## Environment Variables

Never commit secrets to the repository. Use a `.env` file locally:

```env
# MongoDB
MONGO_URI=mongodb://localhost:27017

# PostgreSQL
PG_HOST=localhost
PG_DB=sports_dw
PG_USER=postgres
PG_PASSWORD=your_password

# API-Sports
API_SPORTS_KEY=your_api_key
```

Add `.env` to your `.gitignore`:
```bash
echo ".env" >> .gitignore
```

---

## Requirements

- Python 3.10+
- MongoDB
- PostgreSQL 14+
- Chrome + ChromeDriver (Module 1 only)
- API-Sports account (Module 2 only)
