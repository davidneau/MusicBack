import requests
import json
import random
from methods.deezer import getTrackSearchDeezer, getRecommendationDeezer
from urllib.parse import quote

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


    artist, title, album, id = getTrackSearchDeezer(searchStr)

    print("resultGetSimTrack :", artist)
    print("resultGetSimTrack :", title)
    print("resultGetSimTrack :", album)

    payloadGS = {
        'api_key': API_KEY,
        'method': 'track.getSimilar',
        'track': quote(title),
        'artist': quote(artist),
        "autocorrect": 1,
        'format': 'json'
    }

    r = requests.get('https://ws.audioscrobbler.com/2.0/', headers=headers, params=payloadGS)

    try:
        length = len(r.json()["similartracks"]["track"])
        if length != 0:
            print("z")
            return {"chanson": "", "Result": r.json()["similartracks"]["track"]}
        else:
            chanson = getRecommendationDeezer(artist)
            return {"chanson": chanson, "Result": []}
    except:
        chanson = getRecommendationDeezer(artist)
        return {"chanson": chanson, "Result": []}