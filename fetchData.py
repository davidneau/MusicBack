import requests
import json
import random
from methods.tracks import getTrackSearchDeezer
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def jprint(obj):
    # create a formatted string of the Python JSON object
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)

def getSimilarTrack(searchStr):
    print("getSimilarTrack :", searchStr)
    
    API_KEY = '96c12ef32c83c6763cbfe10cc098219c'
    USER_AGENT = 'Dataquest'

    headers = {
        'user-agent': USER_AGENT
    }


    artist, title, album = getTrackSearchDeezer(searchStr)

    print("resultGetSimTrack :", artist)
    print("resultGetSimTrack :", title)
    print("resultGetSimTrack :", album)

    payloadGS = {
        'api_key': API_KEY,
        'method': 'track.getSimilar',
        'track': title,
        'artist': artist,
        "autocorrect": 1,
        'format': 'json'
    }

    r = requests.get('https://ws.audioscrobbler.com/2.0/', headers=headers, params=payloadGS)
    print("r", r.text)
    choice = random.randint(0, len(r.json()["similartracks"]["track"]))

    if len(r.json()["similartracks"]["track"]) > 0:
        return {"Title": r.json()["similartracks"]["track"][choice]['name'], "Artist": r.json()["similartracks"]["track"][choice]['artist']["name"], "Album": album, "Result": r.json()["similartracks"]["track"]}
    else:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="ID", client_secret="SECRET"))

        track_id = sp.search(q="track:DENIAL IS A RIVER artist:Doechii", type="track")['tracks']['items'][0]['id']

        recs = sp.recommendations(seed_tracks=[track_id], limit=10)
        for t in recs['tracks']:
            print(t['name'], "-", t['artists'][0]['name'])

        return "None"