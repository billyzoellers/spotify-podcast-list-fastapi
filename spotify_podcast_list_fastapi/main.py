"""
spotify-podcast-list-fastapi / main.py
"""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

## App params
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SEC = os.getenv("SPOTIPY_CLIENT_SECRET")
APP_URI = os.getenv("APP_URI")
SECRET = os.getenv("SECRET")
REDIRECT_URI = f'{APP_URI}/callback'
SCOPE = 'user-library-read,user-read-playback-position'
PAGE_SIZE = 50

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET)
app.mount("/static", StaticFiles(directory="spotify_podcast_list_fastapi/static"), name="static")

templates = Jinja2Templates(directory="spotify_podcast_list_fastapi/templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    request.session['token'], authorized = get_token(request.session)
    if not authorized:
        return RedirectResponse("/verify")

    sp = spotipy.Spotify(auth=request.session.get("token").get('access_token'))
    current_user = sp.me()
    print(current_user)
    offset = 0
    shows = []
    while True:
        page = sp.current_user_saved_shows(limit=PAGE_SIZE, offset=offset)
        shows = shows + page['items']
        offset += PAGE_SIZE
        if page['next'] is None:
            break
    return templates.TemplateResponse("index.html", {"request": request, "shows": shows, "current_user": current_user})

@app.get("/show/{show_id}") 
async def read_show(request: Request, show_id: str):
    request.session['token'], authorized = get_token(request.session)
    if not authorized:
        return RedirectResponse("/verify")

    sp = spotipy.Spotify(auth=request.session.get("token").get('access_token'))
    current_user = sp.me()
    offset = 0
    episodes = []
    while True:
        page = sp.show_episodes(show_id, limit=PAGE_SIZE, offset=offset)
        episodes = episodes + page['items']
        offset += PAGE_SIZE
        if page['next'] is None:
            break

    ## Add some friendly values to each episodes
    ms_per_minute = 60000
    for episode in episodes:
        episode['resume_point_min'] = round(episode['resume_point']['resume_position_ms'] / ms_per_minute)
        episode['duration_min'] = round(episode['duration_ms'] / ms_per_minute)
        episode['pct_completed'] = round(episode['resume_point']['resume_position_ms']/episode['duration_ms']*100)

    return templates.TemplateResponse("show.html", {"request": request, "episodes": episodes, "current_user": current_user, "back_link": "/"})

@app.get("/verify")
async def verify():
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SEC,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
    )
    auth_url = sp_oauth.get_authorize_url()

    return RedirectResponse(auth_url)

@app.get("/callback")
async def callback(request: Request, code: str):
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SEC,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
    )
    token = sp_oauth.get_access_token(code)
    request.session["token"] = token
    return RedirectResponse("/")

# TODO: rewrite
def get_token(session):
  token_valid = False
  token = session.get("token", {})

  # Checking if the session already has a token stored
  if not (session.get('token', False)):
      token_valid = False
      return token, token_valid

  # Checking if token has expired
  now = int(time.time())
  is_token_expired = session.get('token').get('expires_at') - now < 60

  # Refreshing token if it has expired
  if (is_token_expired):
      # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
      sp_oauth = SpotifyOAuth(
        client_id = CLIENT_ID,
        client_secret = CLIENT_SEC,
        redirect_uri = REDIRECT_URI,
        scope = SCOPE
      )
      token = sp_oauth.refresh_access_token(session.get('token').get('refresh_token'))

  token_valid = True
  return token, token_valid