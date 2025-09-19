import os
import json
import random
from flask import Flask, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Flask setup
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "secret-key")

# Spotify credentials
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SCOPE = "user-library-read playlist-modify-private playlist-modify-public"

# Show ID (Rabarba podcast)
SHOW_ID = "1GXG3jPwGZUl3P8AWxu7F8" # örnek ID

# Konuk filtresi
GUESTS = [
"nuri çetin",
"kemal ayça",
"ilker gümüşoluk",
"anlatan adam",
"anlatanadam",
"alper çelik",
"ömür okumuş",
"erman arıcasoy"
]

# JSON dosyaları
QUEUE_FILE = "queue.json"
UNPLAYED_FILE = "unplayed.json"


# ================= Spotify Helper =================
def get_spotify():
return spotipy.Spotify(auth=session.get("token"))


def fetch_all_episodes(sp):
all_eps = []
offset = 0
limit = 50
while True:
res = sp.show_episodes(SHOW_ID, limit=limit, offset=offset)
items = res.get("items", []) or []
items = [it for it in items if isinstance(it, dict)]
all_eps.extend(items)
if len(items) < limit:
break
offset += limit
return all_eps


def filter_episodes(episodes):
"""Konuk filtresi + 0853 sonrası bölümleri alma"""
filtered = []
for ep in episodes:
name = ep.get("name", "").lower()
desc = ep.get("description", "").lower()

# Sadece filtredeki isimler varsa
if any(g in name or g in desc for g in GUESTS):
# 0853 sonrası gelenleri alma
if "853" not in name and "0853" not in name:
filtered.append(ep)

# A/B sıralaması
filtered.sort(key=lambda x: x.get("name", ""))
return filtered


# ================= Routes =================
@app.route("/")
def index():
if not session.get("token"):
return '<a href="/login">Log In with Spotify</a>'
return """
<h2>Spotify Rabarba App</h2>
<ul>
<li><a href="/load_podcast">Load Podcast</a></li>
<li><a href="/sync_playlist">Sync Playlist (Choosen)</a></li>
<li><a href="/sync_unplayed">Sync Playlist (Unplayed)</a></li>
<li><a href="/view_queue">View Queue</a></li>
</ul>
"""


@app.route("/login")
def login():
auth_manager = SpotifyOAuth(
client_id=CLIENT_ID,
client_secret=CLIENT_SECRET,
redirect_uri=REDIRECT_URI,
scope=SCOPE
)
return redirect(auth_manager.get_authorize_url())


@app.route("/callback")
def callback():
auth_manager = SpotifyOAuth(
client_id=CLIENT_ID,
client_secret=CLIENT_SECRET,
redirect_uri=REDIRECT_URI,
scope=SCOPE
)
code = request.args.get("code")
token_info = auth_manager.get_access_token(code, as_dict=True)
session["token"] = token_info["access_token"]
return redirect(url_for("index"))


@app.route("/load_podcast")
def load_podcast():
sp = get_spotify()
episodes = fetch_all_episodes(sp)
filtered = filter_episodes(episodes)

with open(QUEUE_FILE, "w", encoding="utf-8") as f:
json.dump(filtered, f, ensure_ascii=False, indent=2)

with open(UNPLAYED_FILE, "w", encoding="utf-8") as f:
json.dump(filtered, f, ensure_ascii=False, indent=2)

return {"queued": len(filtered), "total": len(episodes)}


@app.route("/sync_playlist")
def sync_playlist():
sp = get_spotify()
if not os.path.exists(QUEUE_FILE):
return "Queue not loaded"

with open(QUEUE_FILE, "r", encoding="utf-8") as f:
episodes = json.load(f)

if not episodes:
return "Queue empty"

chosen = random.choice(episodes)
return {"chosen": chosen.get("name")}


@app.route("/sync_unplayed")
def sync_unplayed():
if not os.path.exists(UNPLAYED_FILE):
return "Unplayed not found"

with open(UNPLAYED_FILE, "r", encoding="utf-8") as f:
episodes = json.load(f)

if not episodes:
return "Unplayed empty"

chosen = random.choice(episodes)
# seçileni listeden çıkar
episodes = [ep for ep in episodes if ep["id"] != chosen["id"]]

with open(UNPLAYED_FILE, "w", encoding="utf-8") as f:
json.dump(episodes, f, ensure_ascii=False, indent=2)

return {"unplayed_chosen": chosen.get("name"), "remaining": len(episodes)}


@app.route("/view_queue")
def view_queue():
try:
if not os.path.exists(QUEUE_FILE):
return "queue.json bulunamadı!"

with open(QUEUE_FILE, "r", encoding="utf-8") as f:
queue = json.load(f)

if not queue:
return "queue.json boş görünüyor!"

names = [ep.get("name", "??") for ep in queue]
return "<br>".join(names)

except Exception as e:
return f"Hata: {e}"
