"""
spotify-podcast-list-fastapi / helpers.py
"""
import time
import os
from spotipy.oauth2 import SpotifyOAuth

def new_sp_aouth() -> SpotifyOAuth:
    """
    Return a new instance of the SpotifyOAuth object
    """
    params = {
        "client_id": os.getenv("SPOTIPY_CLIENT_ID"),
        "client_secret": os.getenv("SPOTIPY_CLIENT_SECRET"),
        "redirect_uri": f'{os.getenv("APP_URI")}/callback',
        "scope": 'user-library-read,user-read-playback-position',
    }
    return SpotifyOAuth(*params)

def validate_token(session) -> tuple:
    """
    Return token validity status and a valid token from the session
    """
    # Checking if the session already has a token stored
    token = session.get("token")
    if token is None:
        token_valid = False
        return {}, token_valid

    # If token has expired, refresh token
    now = int(time.time())
    token_expired = token.get('expires_at') - now < 60
    if token_expired:
        sp_oauth = new_sp_aouth()
        token = sp_oauth.refresh_access_token(token.get('refresh_token'))

    token_valid = True
    return token, token_valid