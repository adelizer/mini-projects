import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "user-top-read user-read-recently-played"
REDIRECT_URI = "http://localhost:8888/callback"

TIME_RANGES = {
    "short_term": "Last 4 Weeks",
    "medium_term": "Last 6 Months",
    "long_term": "All Time",
}


def get_spotify_client() -> spotipy.Spotify:
    # If a direct access token is provided, use it (skips OAuth flow)
    token = os.environ.get("SPOTIFY_TOKEN")
    if token:
        return spotipy.Spotify(auth=token)

    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=REDIRECT_URI,
            scope=SCOPES,
            cache_path=".cache",
        )
    )


def get_top_artists(sp: spotipy.Spotify, time_range: str, limit: int = 20) -> list[dict]:
    results = sp.current_user_top_artists(time_range=time_range, limit=limit)
    return [
        {
            "name": artist["name"],
            "genres": artist["genres"],
            "popularity": artist["popularity"],
            "followers": artist["followers"]["total"],
        }
        for artist in results["items"]
    ]


def get_top_tracks(sp: spotipy.Spotify, time_range: str, limit: int = 20) -> list[dict]:
    results = sp.current_user_top_tracks(time_range=time_range, limit=limit)
    return [
        {
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "popularity": track["popularity"],
        }
        for track in results["items"]
    ]


def get_recently_played(sp: spotipy.Spotify, limit: int = 50) -> list[dict]:
    results = sp.current_user_recently_played(limit=limit)
    return [
        {
            "name": item["track"]["name"],
            "artist": ", ".join(a["name"] for a in item["track"]["artists"]),
            "played_at": item["played_at"],
        }
        for item in results["items"]
    ]


def fetch_all_data(sp: spotipy.Spotify) -> dict:
    data = {"top_artists": {}, "top_tracks": {}}

    for time_range in TIME_RANGES:
        data["top_artists"][time_range] = get_top_artists(sp, time_range)
        data["top_tracks"][time_range] = get_top_tracks(sp, time_range)

    try:
        data["recently_played"] = get_recently_played(sp)
    except spotipy.exceptions.SpotifyException:
        data["recently_played"] = []

    return data
