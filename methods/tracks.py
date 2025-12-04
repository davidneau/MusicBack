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


    #[print(r.json()["results"]["trackmatches"]["track"][i]) for i in range(len(r.json()["results"]["trackmatches"]["track"]))]
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
    
def listenMusica(id_yt, click, title, artist, user, app, ClientAPI):
    response = (
        ClientAPI.table("UserMusic")
        .select("*")
        .eq("id_yt", id_yt)
        .eq("User", user)
        .execute()
    )
    #app.cur.execute(f"SELECT * FROM public.\"UserMusic\" WHERE id_yt='{id_yt}' AND \"User\"='{user}'")
    #if len(app.cur.fetchall())== 0:
    if len(response.data)== 0:
        print("Adding to db")
        response = (
            ClientAPI.table("UserMusic")
            .insert({"id_yt": id_yt, "User" : user, "noClicked": 0, "noViews": 1, "Title": title, "Artist": artist})
            .execute()
        )
        #app.cur.execute(f"INSERT INTO public.\"UserMusic\" (id_yt, \"User\", \"noClicked\", \"noViews\", \"Title\", \"Artist\") VALUES ('{id_yt}', '{user}', 0, 1, '{title.replace("'", '"')}', '{artist.replace("'", '"')}')")
        #app.conn.commit()
    else:
        print("increment noViews")
        updateIncrement("UserMusic", "noViews", id_yt, user, ClientAPI)
        #app.cur.execute(f"UPDATE public.\"UserMusic\" SET \"noViews\" = \"noViews\" + 1 WHERE id_yt='{id_yt}' AND \"User\"='{user}'")
        #app.conn.commit()
    
    if click:
        print("increment noClicked")
        updateIncrement("UserMusic", "noClicked", id_yt, user, ClientAPI)
        #app.cur.execute(f"UPDATE public.\"UserMusic\" SET \"noClicked\" = \"noClicked\" + 1 WHERE id_yt='{id_yt}' AND \"User\"='{user}'")
        #app.conn.commit()
    return 'OK'

def epuration(string, scenario):
    if scenario == "parentheses":
        return re.sub(r'\s*\(.*?\)', '', string)
    if scenario == "crochets":
        return re.sub(r'\s*\[.*?\]', '', string)

def loadHistoriqueRoute(user, ClientAPI):
    response = (
        ClientAPI.table("UserMusic")
        .select("*")
        .eq("User", user)
        .order("created_at")
        .execute()
    )
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
