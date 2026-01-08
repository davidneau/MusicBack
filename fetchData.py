import requests
import json
import random
from methods.tracks import getTrackSearch, getTrackSearchDeezer
import logging

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
    choice = random.randint(0, len(r.json()["similartracks"]["track"]))
    logging.info(r.json()["similartracks"]["track"])

    return {"Title": r.json()["similartracks"]["track"][choice]['name'], "Artist": r.json()["similartracks"]["track"][choice]['artist']["name"], "Album": album}