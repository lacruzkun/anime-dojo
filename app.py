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

@app.route("/", methods=["GET", "POST"])
def home():
    conn = get_connection_db()
    anime = conn.execute("""SELECT * FROM anime""").fetchone()
    conn.close()
    return render_template("home.html", anime=anime)


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
            return redirect(url_for("database"))
    return render_template("login.html")

@app.route("/database", methods=["GET", "POST"])
def database():
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

    return render_template("database.html", entries=entries)

@app.route("/add_anime", methods=["GET", "POST"])
def add_anime():
    if "admin" not in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        id = request.form.get("id")
        color = request.form.get("color")
        english_title = request.form.get("english_title")
        japanese_title = request.form.get("japanese_title")
        native_title = request.form.get("native_title")
        cover_image = request.form.get("cover_image")
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
            description) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                    id,
                    english_title, 
                    japanese_title,
                    native_title,
                    year,
                    score,
                    episodes,
                    cover_image,
                    color,
                    description))
        for genre in genres:
            conn.execute("""INSERT INTO anime_genre(
                anime_id,
                genre_id) values(?, ?)""", (id, genre))
        conn.commit()
        conn.close()
        print(id, color, english_title, japanese_title, native_title, cover_image, year, score, episodes, genre)
    conn = get_connection_db()
    genres = conn.execute("""SELECT * FROM genres""").fetchall()
    conn.close()
    return render_template("add_anime.html", genres=genres)

@app.route("/home_anime", methods=["GET", "POST"])
def home_anime():
    results = []
    if request.method == "GET":
        conn = get_connection_db()
        results = conn.execute("""SELECT * FROM anime""").fetchall()

    return render_template("home_anime.html", results=results)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
