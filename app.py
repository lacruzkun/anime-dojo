from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
import requests
import os
import sqlite3

load_dotenv
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

DB = "anime.db"
ANILIST_URL = "https://graphql.anilist.co"
ADMIN = {
        "email": "super@gmail.com",
        "password": "master"
    }

ID_QUERY = """query ($id: Int){
  Page(page: 1, perPage: 1) {
    media(id: $id type: ANIME, sort: POPULARITY_DESC) {
      id
      title {
        english
        romaji
        native
      }
      seasonYear
      averageScore
      episodes
      coverImage {
        extraLarge
        large
        color
      }
      description
      genres
    }
  }
}"""

@app.route("/", methods=["GET", "POST"])
def home():
    conn = get_connection_db()
    anime = conn.execute("""SELECT * FROM anime""").fetchone()
    if request.method == "GET":
        results = conn.execute("""SELECT * FROM anime""").fetchall()
    conn.close()
    return render_template("home.html", anime=anime, results=results)


def get_connection_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS 
        anime(
            id INTEGER PRIMARY KEY, 
            english_title STRING, 
            japanese_title STRING, 
            native_title STRING,
            year INTEGER, 
            score INTEGER, 
            no_of_episodes INTEGER, 
            cover_image STRING,
            large_cover_image STRING,
            color STRING,
            description STRING
         )"""
     )

    conn.execute("""CREATE TABLE IF NOT EXISTS
        genres(
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )
        """)

    conn.execute("""CREATE TABLE IF NOT EXISTS 
        anime_genre(
            anime_id INTEGER,
            genre_id INTEGER,
            PRIMARY KEY (anime_id, genre_id),
            FOREIGN KEY (anime_id) REFERENCES anime(id),
            FOREIGN KEY (genre_id) REFERENCES genre(id)
        )
    """)

    conn.commit()
    conn.close()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == ADMIN["email"] and password == ADMIN["password"]:
            session["admin"] = True
            return redirect(url_for("admin"))
    return render_template("login.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "admin" not in session:
        return redirect(url_for("home"))
    entries = []
    conn = get_connection_db()
    animes = conn.execute("""SELECT * FROM anime""").fetchall()
    for anime in animes:
        genres = conn.execute("""SELECT genres.name FROM genres JOIN anime_genre ON genres.id = anime_genre.genre_id WHERE anime_genre.anime_id = ?""", (anime["id"],)).fetchall()
        entry = dict(anime)
        entry["genres"] = []
        for genre in genres:
            entry["genres"].append(genre["name"])
        entries.append(entry)

    return render_template("admin.html", entries=entries)

@app.route("/admin/add_anime", methods=["GET", "POST"])
def add_anime():
    if "admin" not in session:
        return redirect(url_for("home"))
    return render_template("add_anime.html")

def get_anime_by_id(Id):
    response = requests.post(
            ANILIST_URL,
            json={
                "query":ID_QUERY,
                "variables": {"id": Id}
            },
            timeout=10
        )
    response.raise_for_status()

    data = response.json()
    return data["data"]["Page"]["media"][0]

@app.route("/admin/add/fetch", methods=["GET", "POST"])
def fetch_preview():
    series_id = request.form.get("id")
    anime_data = get_anime_by_id(series_id)
    return render_template("add_anime.html", anime_data=anime_data)

@app.route("/admin/add/save", methods=["GET", "POST"])
def save_series():
    data = request.form.to_dict()
    print(data)
    id = request.form.get("id")
    color = request.form.get("color")
    english_title = request.form.get("english_title")
    japanese_title = request.form.get("japanese_title")
    native_title = request.form.get("native_title")
    cover_image = request.form.get("cover_image")
    large_cover_image = request.form.get("large_cover_image")
    year = request.form.get("year")
    score = request.form.get("score")
    episodes = request.form.get("episodes")
    description = request.form.get("description")
    genres = request.form.getlist("genre")
    conn = get_connection_db()
    conn.execute("""INSERT INTO anime(
        id ,
        english_title ,
        japanese_title ,
        native_title ,
        year ,
        score ,
        no_of_episodes ,
        cover_image ,
        large_cover_image,
        color ,
        description) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
                id,
                english_title, 
                japanese_title,
                native_title,
                year,
                score,
                episodes,
                cover_image,
                large_cover_image,
                color,
                description))
    for genre in genres:
        conn.execute("""INSERT INTO anime_genre(
            anime_id,
            genre_id) values(?, ?)""", (id, genre))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/anime/<int:anime_id>")
def admin_anime_detail(anime_id):
    conn = get_connection_db()
    anime = conn.execute("""SELECT * FROM anime WHERE id = ?""", (anime_id, )).fetchone()
    conn.close()
    return render_template("manage_episodes.html", anime=anime)

@app.route("/anime/<int:anime_id>")
def anime_detail(anime_id):
    conn = get_connection_db()
    anime = conn.execute("""SELECT * FROM anime WHERE id = ?""", (anime_id, )).fetchone()
    conn.close()
    return render_template("anime_details.html", anime=anime)

@app.route("/home_anime", methods=["GET", "POST"])
def home_anime():
    results = []
    if request.method == "GET":
        conn = get_connection_db()
        results = conn.execute("""SELECT * FROM anime""").fetchall()

    return render_template("home_anime.html", results=results)

@app.route("/home_anime", methods=["GET", "POST"])
def toggle_episode_status():
    return "OK"

@app.route("/home_anime", methods=["GET", "POST"])
def upload_episode():
    return "OK"

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
