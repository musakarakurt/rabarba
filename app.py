import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, redirect, request, session, url_for, render_template

app = Flask(__name__)
app.secret_key = "supersecret"
app.config["SESSION_COOKIE_NAME"] = "spotify-login-session"

# Spotify API kimlik bilgileri
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SHOW_ID = "40ORgVQqJWPQGRMUXmL67y"  # Rabarba podcast ID

SCOPE = "user-read-playback-state,user-modify-playback-state,playlist-modify-private,playlist-modify-public"

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )

def get_token():
    token_info = session.get("token_info", None)
    if not token_info:
        return None
    sp_oauth = get_spotify_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
    return token_info

def fetch_all_episodes(sp):
    all_eps = []
    offset = 0
    limit = 50
    trid = SHOW_ID
    while True:
        res = sp.show_episodes(trid, limit=limit, offset=offset)
        items = res.get("items", []) or []
        items = [it for it in items if isinstance(it, dict)]
        all_eps.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return all_eps

@app.route("/")
def index():
    return redirect(url_for("view_queue"))

@app.route("/login")
def login():
    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    sp_oauth = get_spotify_oauth()
    session.clear()
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for("view_queue"))

@app.route("/load_podcast")
def load_podcast():
    token_info = get_token()
    if not token_info:
        return redirect(url_for("login"))
    sp = spotipy.Spotify(auth=token_info["access_token"])

    episodes = fetch_all_episodes(sp)

    if not os.path.exists("queue.json"):
        with open("queue.json", "w", encoding="utf-8") as f:
            json.dump([], f)

    with open("queue.json", "r", encoding="utf-8") as f:
        queue = json.load(f)

    added = 0
    for ep in episodes:
        try:
            name = ep["name"]
            release_date = ep["release_date"]
            eid = ep["id"]
        except Exception as e:
            print("[load_podcast] skip invalid episode:", e)
            continue

        if not any(q["id"] == eid for q in queue):
            queue.append({
                "id": eid,
                "name": name,
                "release_date": release_date,
                "played": False
            })
            added += 1

    with open("queue.json", "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

    return {"queued": added, "total": len(queue)}

@app.route("/view_queue")
def view_queue():
    try:
        if not os.path.exists("queue.json"):
            return "queue.json bulunamadı!"
        with open("queue.json", "r", encoding="utf-8") as f:
            queue = json.load(f)
        if not queue:
            return "queue.json boş görünüyor!"
        return render_template("queue.html", queue=queue)
    except Exception as e:
        return f"Hata: {e}"
