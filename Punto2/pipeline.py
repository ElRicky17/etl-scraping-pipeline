import requests
from pymongo import MongoClient
import psycopg2
from datetime import datetime

client = MongoClient("mongodb://"something here"") 
db = client["Sports"]
pg_conn = psycopg2.connect(
    host="localhost",
    dbname="sports_dw",
    user="postgres",
    password=""something here""
)

class Pipeline:
    def __init__(self,sport):
        self.collection = db[sport]
        self.sport = sport
        self.api_key = '"something here"'
        self.data = None
        self.pg_cursor = pg_conn.cursor()

    def extract(self):
        url = f'https://v1.{self.sport}.api-sports.io/games?date=2025-08-26'
        headers = {
            'x-apisports-key': self.api_key,
            'x-apisports-host': 'v3.football.api-sports.io'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            self.data = response.json()  
            if isinstance(self.data, dict):
                self.data = [self.data]

            if self.data:  
                result = self.collection.insert_many(self.data)
                print(f"Inserted {len(result.inserted_ids)} documents")
            else:
                print("No se encontraron datos para insertar")
        else:
            print(f"Error en la API: {response.status_code}")
    def insert_dim_date(self,date_str):
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        self.pg_cursor.execute("""
            INSERT INTO dim_date (full_date, year, month, day, week)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING date_id
        """, (dt, dt.year, dt.month, dt.day, dt.isocalendar().week))
        res = self.pg_cursor.fetchone()
        if res:
            return res[0]
        else:
            self.pg_cursor.execute("SELECT date_id FROM dim_date WHERE full_date = %s", (dt,))
            return self.pg_cursor.fetchone()[0]

    def insert_dim_team(self,team):
        self.pg_cursor.execute("""
            INSERT INTO dim_team (team_id, team_name, team_logo)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (team["id"], team["name"], team.get("logo")))
        return team["id"]

    def insert_dim_league(self,league):
        self.pg_cursor.execute("""
            INSERT INTO dim_league (league_id, league_name, league_type, season, league_logo)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (league["id"], league["name"], league.get("type"), league.get("season"), league.get("logo")))
        return league["id"]

    def insert_dim_country(self,country):
        self.pg_cursor.execute("""
            INSERT INTO dim_country (country_id, country_name, country_code, country_flag)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (country["id"], country["name"], country.get("code"), country.get("flag")))
        return country["id"]

    def insert_dim_status(self,status):
        self.pg_cursor.execute("""
            INSERT INTO dim_status (status_long, status_short)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            RETURNING status_id
        """, (status.get("long"), status.get("short")))
        res = self.pg_cursor.fetchone()
        if res:
            return res[0]
        else:
            self.pg_cursor.execute("""
                SELECT status_id FROM dim_status
                WHERE status_long = %s AND status_short = %s
            """, (status.get("long"), status.get("short")))
            return self.pg_cursor.fetchone()[0]

    def insert_into_postgres(self, collection, sport):
        try:
            for doc in db[collection].find():
                for game in doc["response"]:
                    # Dimensiones
                    date_id = self.insert_dim_date(game["date"])
                    league_id = self.insert_dim_league(game["league"])
                    country_id = self.insert_dim_country(game["country"])
                    status_id = self.insert_dim_status(game["status"])
                    home_team_id = self.insert_dim_team(game["teams"]["home"])
                    away_team_id = self.insert_dim_team(game["teams"]["away"])

                    # Fact table
                    home_total = game["scores"]["home"]["total"] if sport == "basketball" else game["scores"]["home"]
                    print(home_total)
                    away_total = game["scores"]["away"]["total"] if sport == "basketball" else game["scores"]["away"]
                    print(away_total)
                    
                    # Periods (flexible mapping)
                    periods = game.get("periods", {})
                    if sport == "basketball":
                        period1_home = game["scores"]["home"].get("quarter_1")
                        period2_home = game["scores"]["home"].get("quarter_2")
                        period3_home = game["scores"]["home"].get("quarter_3")
                        period4_home = game["scores"]["home"].get("quarter_4")
                        period5_home = game["scores"]["home"].get("over_time")
                        period1_away = game["scores"]["away"].get("quarter_1")
                        period2_away = game["scores"]["away"].get("quarter_2")
                        period3_away = game["scores"]["away"].get("quarter_3")
                        period4_away = game["scores"]["away"].get("quarter_4")
                        period5_away = game["scores"]["away"].get("over_time")
                    else:
                        # Handball & Volleyball: use "periods"
                        period1_home = periods.get("first", {}).get("home")
                        period2_home = periods.get("second", {}).get("home")
                        period3_home = periods.get("third", {}).get("home")
                        period4_home = periods.get("fourth", {}).get("home")
                        period5_home = periods.get("fifth", {}).get("home")

                        period1_away = periods.get("first", {}).get("away")
                        period2_away = periods.get("second", {}).get("away")
                        period3_away = periods.get("third", {}).get("away")
                        period4_away = periods.get("fourth", {}).get("away")
                        period5_away = periods.get("fifth", {}).get("away")

                    self.pg_cursor.execute("""
                        INSERT INTO fact_game (
                            game_id, sport, date_id, league_id, country_id, status_id,
                            home_team_id, away_team_id, venue,
                            home_total, away_total,
                            period1_home, period1_away,
                            period2_home, period2_away,
                            period3_home, period3_away,
                            period4_home, period4_away,
                            period5_home, period5_away
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT DO NOTHING
                    """, (
                        game["id"], sport, date_id, league_id, country_id, status_id,
                        home_team_id, away_team_id, game.get("venue"),
                        home_total, away_total,
                        period1_home, period1_away,
                        period2_home, period2_away,
                        period3_home, period3_away,
                        period4_home, period4_away,
                        period5_home, period5_away
                    ))
            
            pg_conn.commit()
            print(f"Successfully committed data for {sport}")
            
        except Exception as e:
            print(f"Error processing {sport}: {e}")
            pg_conn.rollback()
            raise

    
  

    

#Todo funciona melo, utilize postgres desde la terminal de WSL
Sports = ['handball', 'volleyball', 'basketball']
for sport in Sports:
    pipeline = Pipeline(sport)
    #pipeline.extract()
    pipeline.insert_into_postgres(sport, sport)
    
