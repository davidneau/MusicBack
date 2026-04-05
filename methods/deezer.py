import requests
import re
import random
import logging
from methods.tracks import normaliser_titre

def epuration(string, scenario):
    if scenario == "parentheses":
        return re.sub(r'\s*\(.*?\)', '', string)
    if scenario == "crochets":
        return re.sub(r'\s*\[.*?\]', '', string)


def getTrackSearchDeezer(searchStr):
    searchStr = epuration(searchStr, "crochets")
    searchStr = epuration(searchStr, "parentheses")
    searchStr = searchStr.replace(":", "")
    print("getTrackSearch searchStr: ", searchStr)


    r = requests.get('https://api.deezer.com/search?q=' + searchStr)

    artist = r.json()["data"][0]["artist"]["name"]
    title = r.json()["data"][0]["title_short"]
    album = r.json()["data"][0]["album"]["title"]
    artist_id = r.json()["data"][0]["artist"]["id"]

    return artist, title, album, artist_id

def getTrackSearchDeezerAll(searchStr):
    print("getTrackSearch searchStr: ", searchStr)
    result = []
    logging.info('https://api.deezer.com/search?q=' + searchStr)
    r = requests.get(
        "https://api.deezer.com/search",
        params={"q": searchStr}
    )
    for music in r.json()["data"]:
        title = music["title"]
        artist = music["artist"]["name"]
        album = music["album"]["title"]
        result.append({"Title": normaliser_titre(title), "Artist": artist, "Album": album})
    [print(i) for i in result]
    return result

def getRecommendationDeezer(searchStr):
    _,_,_,artist_id = getTrackSearchDeezer(searchStr)
    
    r = requests.get('https://api.deezer.com/artist/' + str(artist_id) + '/related')
    data = r.json()["data"]
    choice = random.randint(0, 5)
    print("choice", choice)
    print("len data", "5")
    artist = data[choice]["id"]
    r = requests.get('https://api.deezer.com/artist/' + str(artist) + "/top")
    dataChanson = r.json()["data"]
    choice = random.randint(0, len(dataChanson) - 1)
    print("choice", choice)
    print("len data", len(data))
    chanson = dataChanson[choice]
    print("deezer", chanson)
    chanson["Title"] = chanson["title"]
    chanson["Artist"] = chanson["artist"]["name"]
    return chanson