import requests
import re

""" API utilisé = lastFM """

API_KEY = '96c12ef32c83c6763cbfe10cc098219c'
USER_AGENT = 'Dataquest'

def getTrackSearch(searchStr):
    searchStr = epuration(searchStr, "crochets")
    searchStr = epuration(searchStr, "parentheses")
    searchStr = searchStr.replace(":", "")
    print("getTrackSearch searchStr: ", searchStr)

    headers = {
        'user-agent': USER_AGENT
    }

    payloadAT = {
        'api_key': API_KEY,
        'method': 'track.search',
        'track': searchStr,
        'format': 'json'
    }

    r = requests.get('https://ws.audioscrobbler.com/2.0/', headers=headers, params=payloadAT)

    artist = r.json()["results"]["trackmatches"]["track"][0]["artist"]
    title = r.json()["results"]["trackmatches"]["track"][0]["name"].split('-')[1].lstrip()

    print(r.json()["results"]["trackmatches"]["track"][0])

    i = 0
    while "remaster" in title.lower():
        i += 1
        print(i)
        
        artist = r.json()["results"]["trackmatches"]["track"][i]["artist"]
        title = r.json()["results"]["trackmatches"]["track"][i]["name"].split('-')[1].lstrip()


    print("artist :", artist)
    print("title :", title)
    return artist, title

def getTrackSearchDeezer(searchStr):
    searchStr = epuration(searchStr, "crochets")
    searchStr = epuration(searchStr, "parentheses")
    searchStr = searchStr.replace(":", "")
    print("getTrackSearch searchStr: ", searchStr)


    r = requests.get('https://api.deezer.com/search?q=' + searchStr)

    artist = r.json()["data"][0]["artist"]["name"]
    title = r.json()["data"][0]["title_short"]
    album = r.json()["data"][0]["album"]["title"]

    return artist, title, album

def getTrackSearchDeezerAll(searchStr):
    print("getTrackSearch searchStr: ", searchStr)
    result = []
    r = requests.get('https://api.deezer.com/search?q=' + searchStr)
    for music in r.json()["data"]:
        title = music["title"]
        artist = music["artist"]["name"]
        album = music["album"]["title"]
        result.append({"Title": title, "Artist": artist, "Album": album})
    [print(i) for i in result]
    return result
    
def listenMusica(id_yt, click, title, artist, user, app, ClientAPI):
    response = (
        ClientAPI.table("UserMusic")
        .select("*")
        .eq("id_yt", id_yt)
        .eq("User", user)
        .execute()
    )
    if len(response.data)== 0:
        print("Adding to db")
        response = (
            ClientAPI.table("UserMusic")
            .insert({"id_yt": id_yt, "User" : user, "noClicked": 0, "noViews": 1, "Title": title, "Artist": artist})
            .execute()
        )
    else:
        print("increment noViews")
        updateIncrement("UserMusic", "noViews", id_yt, user, ClientAPI)
    
    if click:
        print("increment noClicked")
        updateIncrement("UserMusic", "noClicked", id_yt, user, ClientAPI)
    return 'OK'

def epuration(string, scenario):
    if scenario == "parentheses":
        return re.sub(r'\s*\(.*?\)', '', string)
    if scenario == "crochets":
        return re.sub(r'\s*\[.*?\]', '', string)

def loadHistoriqueRoute(user, ClientAPI):
    print(user)
    response = (
        ClientAPI.table("UserMusic")
        .select("*, StatMusic3(id_yt, Image, Album)")
        .eq("User", user)
        .order("created_at", desc=True)
        .execute()
    )
    [print(i) for i in response.data[:20]]
    return response.data

def loadReplayRoute(user, ClientAPI):
    response = (
        ClientAPI.table("UserMusic")
        .select("*")
        .eq("User", user)
        .order("noViews")
        .execute()
    )
    return response.data

def updateIncrement(table, col, id_yt, user, ClientAPI):
    response = (
        ClientAPI.table("UserMusic")
        .select({col})
        .eq("User", user)
        .eq("id_yt", id_yt)
        .execute()
    )        
    print(response.data)
    value = response.data[0][col]
    print(id_yt)
    print(user)
    response2 = (
        ClientAPI.table("UserMusic")
        .update({col: value + 1})
        .eq("id_yt", id_yt)
        .eq("User", user)
        .execute()
    )
