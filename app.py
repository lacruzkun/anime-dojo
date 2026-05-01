from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
import requests
import os
import sqlite3


load_dotenv
app = Flask(__name__)
app.jinja_env.globals['enumerate'] = enumerate
app.jinja_env.globals['zip'] = zip
app.jinja_env.globals['len'] = len
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
      format
    }
  }
}"""

# get the popular anime by popularity to populate our database for testing purposes
POPULAR_QUERY = """query {
  Page(page: 1, perPage: 1) {
    media(type: ANIME, sort: POPULARITY_DESC) {
      id
    }
  }
}"""

GENRE_QUERY = """query {
  GenreCollection
}"""
GENRES =[
            ("Action",),
            ("Adventure",),
            ("Comedy",),
            ("Drama",),
            ("Ecchi",),
            ("Fantasy",),
            ("Hentai",),
            ("Horror",),
            ("Mahou Shoujo",),
            ("Mecha",),
            ("Music",),
            ("Mystery",),
            ("Psychological",),
            ("Romance",),
            ("Sci-Fi",),
            ("Slice of Life",),
            ("Sports",),
            ("Supernatural",),
            ("Thriller",),
    ]

@app.route("/", methods=["GET", "POST"])
def home():
    conn = get_connection_db()
    slides = [conn.execute("""SELECT * FROM anime WHERE id = ?""", (11061,)).fetchone(),
    conn.execute("""SELECT * FROM anime WHERE id = ?""", (11757,)).fetchone(),
     conn.execute("""SELECT * FROM anime WHERE id = ?""", (20447,)).fetchone(),
    conn.execute("""SELECT * FROM anime WHERE id = ?""", (21234,)).fetchone()]
    if request.method == "GET":
        results = conn.execute("""SELECT * FROM anime""").fetchall()
    conn.close()
    return render_template("home.html", results=results, slides=slides)


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
            description STRING,
            format STRING
         )"""
     )

    conn.execute("""CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_id INTEGER NOT NULL,
        episode_number INTEGER NOT NULL,
        file_path1 TEXT,
        file_path2 TEXT,
        file_path3 TEXT,
        file_path4 TEXT,
        title TEXT,
        FOREIGN KEY (anime_id) REFERENCES anime(id) ON DELETE CASCADE,
        UNIQUE (anime_id, episode_number)
    )"""
    )

    conn.execute("""CREATE TABLE IF NOT EXISTS
        genres(
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )
        """)

    conn.executemany("""INSERT OR IGNORE INTO
    genres(name) values(?)""", GENRES)

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
        genres = conn.execute("""
                  SELECT genres.name FROM genres 
                  JOIN anime_genre ON genres.id = anime_genre.genre_id 
                  WHERE anime_genre.anime_id = ?""", (anime["id"],)).fetchall()
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
    if "admin" not in session:
        return redirect(url_for("home"))
    series_id = request.form.get("id")
    anime_data = get_anime_by_id(series_id)
    return render_template("add_anime.html", anime_data=anime_data)

@app.route("/admin/add/save", methods=["GET", "POST"])
def save_series():
    if "admin" not in session:
        return redirect(url_for("home"))
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
    _format = request.form.get("format")
    genres = request.form.getlist("genre")

    if color == "None":
        color = "#202020"

    conn = get_connection_db()
    try:
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
            color,
            format,
            description) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    _format,
                    description))
        for genre in genres:
            conn.execute("""INSERT INTO anime_genre(
                anime_id,
                genre_id) values(?, ?)""", (id, genre))
    except Exception as e:
        print(e)

    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/anime/<int:anime_id>")
def manage_episode(anime_id):
    if "admin" not in session:
        return redirect(url_for("home"))
    conn = get_connection_db()
    anime = conn.execute("""SELECT * FROM anime WHERE id = ?""", (anime_id, )).fetchone()
    episodes = conn.execute("""
    SELECT * FROM episodes WHERE id = ?""", (anime_id, )).fetchall()
    print(len(episodes))
    conn.close()
    return render_template("manage_episodes.html", anime=anime, episodes=episodes, length=len(episodes))

@app.route("/anime/<int:anime_id>", methods=["GET", "POST"])
def anime_detail(anime_id):
    conn = get_connection_db()
    anime = conn.execute("""SELECT * FROM anime WHERE id = ?""", (anime_id, )).fetchone()
    genres = conn.execute("""
                  SELECT genres.name FROM genres 
                  JOIN anime_genre ON genres.id = anime_genre.genre_id 
                  WHERE anime_genre.anime_id = ?""", 
                          (anime["id"],)).fetchall()
    episodes = conn.execute("""
        SELECT * FROM episodes WHERE id = ?
    """, (anime_id, )).fetchall()

    if request.method == "POST":
        eps = []
        urls = []
        q = request.form
        for ep in q:
            eps.append(ep.split("-")[1])

        for ep in eps:
            url = conn.execute("""
            SELECT file_path FROM episodes 
            WHERE anime_id = ? AND episode_number = ? """, 
                               (anime_id, ep)).fetchone()
            urls.append(url)

        return render_template("anime_details.html", anime=anime, genres=genres, urls=urls, eps=eps)

    conn.close()
    return render_template("anime_details.html", anime=anime, genres=genres, episodes=episodes)

@app.route("/home_anime", methods=["GET", "POST"])
def home_anime():
    results = []
    if request.method == "GET":
        conn = get_connection_db()
        results = conn.execute("""SELECT * FROM anime""").fetchall()

    return render_template("home_anime.html", results=results)

@app.route("/admin/toggle_episode_status", methods=["GET", "POST"])
def toggle_episode_status():
    return "OK"

@app.route("/admin/upload_episode<int:anime_id>", methods=["GET", "POST"])
def upload_episode(anime_id):
    if request.method == "POST":
        episode_number = request.form.get("episode_number")
        title = request.form.get("title")
        path = request.form.get("video_url")
        conn = get_connection_db()
        try:
            conn.execute("""
            INSERT INTO episodes(anime_id, episode_number, file_path, title)
            VALUES(?, ?, ?, ?)""", (anime_id, episode_number, path, title))
            conn.commit()
        except Exception as e:
            print(e)

        conn.close()

        return redirect(url_for("manage_episode", anime_id=anime_id))


@app.route("/admin/edit_episode<int:anime_id>", methods=["GET", "POST"])
def edit_episode(anime_id):
    if request.method == "POST":
        episode = request.form.get("episode_number")
        title = request.form.get("title")
        path = request.form.getlist("video_url")
        print("path: ", path)
        conn = get_connection_db()
        #try:
        #    conn.execute("""
        #    UPDATE  episodes SET 
        #    file_path = ?, title = ? 
        #    WHERE anime_id = ? AND episode_number = ?""", 
        #                 (path, title, anime_id, episode))
        #    print(episode)
        #    conn.commit()
        #except Exception as e:
        #    print(e)

        conn.close()

        return redirect(url_for("manage_episode", anime_id=anime_id))


@app.route("/admin/delete_episode<int:anime_id><int:ep_id>", methods=["GET", "POST"])
def delete_episode(anime_id, ep_id):
    if request.method == "POST":
        conn = get_connection_db()
        try:
            conn.execute("""
            DELETE FROM  episodes
            WHERE anime_id = ? AND id = ?""", 
                         (anime_id, ep_id))
            print(anime_id, ep_id)
            conn.commit()
        except Exception as e:
            print(e)

        conn.close()

        return redirect(url_for("manage_episode", anime_id=anime_id))

@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.args.get("q", "").strip()
    conn = get_connection_db()
    results = conn.execute("""
    SELECT * FROM anime
    WHERE english_title like ? 
    OR japanese_title like ? 
    OR native_title like ?""", (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
    print(query)

    conn.close()
    return render_template("search.html", query=query, results=results)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
