"""
spotify-podcast-list-fastapi / main.py
"""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import spotipy
import os
from spotify_podcast_list_fastapi.helpers import new_sp_aouth, validate_token
from dotenv import load_dotenv

## App params
load_dotenv()
PAGE_SIZE = 50

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET"))
app.mount(
    "/static",
    StaticFiles(directory="spotify_podcast_list_fastapi/static"),
    name="static",
)
templates = Jinja2Templates(directory="spotify_podcast_list_fastapi/templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    request.session["token"], authorized = validate_token(request.session)
    if not authorized:
        return RedirectResponse("/verify")

    sp = spotipy.Spotify(auth=request.session.get("token").get("access_token"))
    current_user = sp.me()
    print(current_user)
    offset = 0
    shows = []
    while True:
        page = sp.current_user_saved_shows(limit=PAGE_SIZE, offset=offset)
        shows = shows + page["items"]
        offset += PAGE_SIZE
        if page["next"] is None:
            break
    return templates.TemplateResponse(
        "index.html", {"request": request, "shows": shows, "current_user": current_user}
    )


@app.get("/show/{show_id}", response_class=HTMLResponse)
async def read_show(request: Request, show_id: str):
    request.session["token"], authorized = validate_token(request.session)
    if not authorized:
        return RedirectResponse("/verify")

    sp = spotipy.Spotify(auth=request.session.get("token").get("access_token"))
    current_user = sp.me()
    offset = 0
    episodes = []
    while True:
        page = sp.show_episodes(show_id, limit=PAGE_SIZE, offset=offset)
        episodes = episodes + page["items"]
        offset += PAGE_SIZE
        if page["next"] is None:
            break

    ## Add some friendly values to each episodes
    ms_per_minute = 60000
    for episode in episodes:
        episode["resume_point_min"] = round(
            episode["resume_point"]["resume_position_ms"] / ms_per_minute
        )
        episode["duration_min"] = round(episode["duration_ms"] / ms_per_minute)
        episode["pct_completed"] = round(
            episode["resume_point"]["resume_position_ms"] / episode["duration_ms"] * 100
        )

    return templates.TemplateResponse(
        "show.html",
        {
            "request": request,
            "episodes": episodes,
            "current_user": current_user,
            "back_link": "/",
        },
    )


@app.get("/verify")
async def verify():
    sp_oauth = new_sp_aouth()
    auth_url = sp_oauth.get_authorize_url()

    return RedirectResponse(auth_url)


@app.get("/callback")
async def callback(request: Request, code: str):
    sp_oauth = new_sp_aouth()
    token = sp_oauth.get_access_token(code)
    request.session["token"] = token
    return RedirectResponse("/")
