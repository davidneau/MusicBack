from flask import Flask, request
from fetchData import getSimilarTrack
from flask_cors import CORS
import json
import threading
import requests
from methods.tracks import listenMusica, loadHistoriqueRoute, loadReplayRoute, normaliser_titre
from methods.deezer import getTrackSearchDeezer, getTrackSearchDeezerAll
from googleapiclient.discovery import build
from flask import Flask, request, jsonify
import bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from supabase import create_client
from ytmusicapi import YTMusic
import time
import logging
import re
import urllib
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s -%(message)s"
)

yt = YTMusic()  # pas d'auth nécessaire pour juste chercher

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=15)

jwt = JWTManager(app)

# Activer CORS pour toutes les routes et pour toutes les origines
CORS(app, resources={r"/*": {"origins": "*"}})

youtube = build("youtube", "v3", developerKey='AIzaSyA8apjRRfjCHmu6M_4q_r3kUbnO_qJ7xfk')

DATABASE_URL = "https://qtkheteiebuzzedvlrtn.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF0a2hldGVpZWJ1enplZHZscnRuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzMzU3MTIsImV4cCI6MjA3OTkxMTcxMn0.vp-JoA-6T-kpOahwI__SwKXVUyaxF82LPfnyQA7ZGy8"

ClientAPI = create_client(DATABASE_URL, API_KEY)

SuggestionMusics = []

@app.post('/login')
def login():
    data = request.get_json()
    identifiant = data.get('identifiant')
    password = data.get('password')

    #app.cur.execute(f"SELECT * FROM public.\"Users\" WHERE identifiant='{identifiant}'")
    response = (
        ClientAPI.table("Users")
        .select("*")
        .eq("identifiant", identifiant)
        .execute()
    )
    users = response.data
    logging.info("response")
    logging.info(response.data)

    if (len(users) != 0):
        logging.info(users[0])
        if bcrypt.checkpw(password.encode("utf-8"), users[0]["password"].encode("utf-8")) :
            token = create_access_token(identity=identifiant)
            return jsonify(access_token=token), 200
    return jsonify(msg="Invalid credentials"), 401

@app.get('/profile')
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    return jsonify(user=current_user), 200

@app.post('/signIn')
@jwt_required()
def signIn():
    data = request.get_json()
    identifiant = data.get('identifiant')
    password = data.get('password')
    password_bytes = password.encode("utf-8")
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

    response = (
        ClientAPI.table("Users")
        .insert({"identifiant" : identifiant, "password": hashed_password.decode("utf-8")})
        .execute()
    )
    return "OK", 200

@app.route('/getSimilarTrack/<string:search>')
@jwt_required()
def getSimilarTrackRoute(search):
    global SuggestionMusics
    logging.info("get Similar Tracks Route")
    
    try:
        similarTrack = getSimilarTrack(search)
        logging.info("z")
        logging.info(similarTrack)
        logging.info(len(similarTrack))

        if len(similarTrack["Result"]) == 0:
            return similarTrack
        
        SuggestionMusics = similarTrack["Result"]
        for i in SuggestionMusics:
            i["Title"] = i["name"]
            i["Artist"] = i["artist"]["name"]

        if similarTrack == "None":
            if SuggestionMusics == []:
                response = (
                    ClientAPI.table("UserMusic")
                    .select("*")
                    .eq("User", get_jwt_identity())
                    .execute()
                )
                choice = random.randint(0, len(response.data))
                return {"music": response.data[choice], "Result": response.data}
            else:
                choice = random.randint(0, len(SuggestionMusics))
                return {"music": SuggestionMusics[choice], "Result": SuggestionMusics}
        

        titleMusics = [normaliser_titre(i["Title"].lower()) for i in SuggestionMusics]
        artistsMusics = [i["Artist"].lower() for i in SuggestionMusics]

        logging.info([artist.lower() + "|" + title.lower() for (title, artist) in zip(titleMusics,artistsMusics)])
        existing = (
            ClientAPI
            .table("StatMusic3")
            .select("*")
            .in_("track_key", [artist.lower() + "|" + title.lower() for (title, artist) in zip(titleMusics,artistsMusics)])
            .execute()
        )
        missing_tracks = [
            track for track in SuggestionMusics
            if track["Artist"].lower() + "|" + track["Title"].lower() not in [music["track_key"] for music in existing.data]
        ]

        logging.info(len(missing_tracks))
        logging.info(existing.data)
        choice = random.randint(0, len(existing.data) - 1)
        return {"Result": existing.data}
    except Exception as Ex:
        logging.info(f"exception : {Ex}")
        return "500 error"


@app.post('/createPlaylist')
@jwt_required()
def createPlaylist():
    current_user = get_jwt_identity()
    logging.info(f"fetch playlist from {current_user}")
    response = (
            ClientAPI.table("Users")
            .select("Playlist")
            .eq("identifiant", current_user)
            .execute()
    )
    json = response.data[0]
    logging.info(f"playlists: {json}")
    data = request.get_json()
    logging.info(f"id playlist {data["playlistID"]}")
    if data["fromYT"]:
        videos_id = getVideosIdFromPlaylistYT(data["playlistID"])
        name = data["name"]
        json[name] = videos_id
        response2 = (
            ClientAPI.table("Users")
            .update(json)
            .eq("identifiant", current_user)
            .execute()
        )
    return "OK", 200


@app.post('/createPlaylist2')
@jwt_required()
def createPlaylist2():
    current_user = get_jwt_identity()
    logging.info(f"fetch playlist from {current_user}")
    response = (
            ClientAPI.table("Users")
            .select("Playlist")
            .eq("identifiant", current_user)
            .execute()
    )
    json = response.data[0]["Playlist"]
    logging.info(f"Playlists: {json}")
    
    data = request.get_json()
    logging.info(f"nom Playlist {data["nomPlaylist"]}")
    name = data["nomPlaylist"]
    
    json[name] = []

    (
        ClientAPI.table("Users")
        .update({"Playlist": json})
        .eq("identifiant", current_user)
        .execute()
    )
    return json, 200


@app.post('/addSongToPlaylist')
@jwt_required()
def addSongToPlaylist():
    current_user = get_jwt_identity()
    logging.info(f"fetch playlist from {current_user}")
    response = (
            ClientAPI.table("Users")
            .select("Playlist")
            .eq("identifiant", current_user)
            .execute()
    )
    json = response.data[0]["Playlist"]
    logging.info(f"Playlists: {json}")
    
    data = request.get_json()
    logging.info(f"data {data}")
    logging.info(f"nom Playlist {data["nomPlaylist"]}")
    name = data["nomPlaylist"]
    videoId = data["videoID"]
    
    json[name].append(videoId)

    (
        ClientAPI.table("Users")
        .update({"Playlist": json})
        .eq("identifiant", current_user)
        .execute()
    )
    return json, 200


@app.post('/getPlaylist/<playlistName>')
@jwt_required()
def getPlaylist(playlistName):
    result_list = []
    current_user = get_jwt_identity()
    response = (
            ClientAPI.table("Users")
            .select("Playlist")
            .eq("identifiant", current_user)
            .execute()
    )
    logging.info(f"playlist of {current_user} : {response.data[0]["Playlist"]}")
    i = 1
    try:
        for music in response.data[0]["Playlist"][playlistName][:3]:
            jsonMusic = prepaMusicPlaylist(music)
            jsonMusic['index'] = i
            i += 1
            result_list.append(jsonMusic)
        return result_list, 200
    except:
        return "Not found", 404


@app.post('/getPlaylist2/')
@jwt_required()
def getPlaylist2():
    current_user = get_jwt_identity()
    response = (
            ClientAPI.table("Users")
            .select("Playlist")
            .eq("identifiant", current_user)
            .execute()
    )
    logging.info(f"playlist of {current_user} : {response.data[0]["Playlist"]}")
    for pl in response.data[0]["Playlist"]:
        print("pl", response.data[0]["Playlist"][pl])
        formatted_ids = "(" + ",".join(
            f'"{music_id}"' for music_id in response.data[0]["Playlist"][pl]
        ) + ")"
        responseSong = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .or_(f"id_yt.in.{formatted_ids},id_clip.in.{formatted_ids}")
            .execute()
        )
        response.data[0]["Playlist"][pl] = responseSong.data
    return response.data[0], 200


@app.post('/deleteSongFromPlaylist')
@jwt_required()
def deleteSongFromPlaylist():
    current_user = get_jwt_identity()
    logging.info(f"fetch playlist from {current_user}")
    response = (
            ClientAPI.table("Users")
            .select("Playlist")
            .eq("identifiant", current_user)
            .execute()
    )
    json = response.data[0]["Playlist"]
    logging.info(f"Playlists: {json}")
    
    data = request.get_json()
    logging.info(f"data: {data}")
    music_id = data["music_id"]
    playlist = data["playlist"]

    response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .or_(f"id_yt.eq.{music_id},id_clip.eq.{music_id}")
            .execute()
    )
    json_music = response.data[0]

    try:
        json[playlist].remove(json_music['id_yt'])
    except:
        print("fail to remove")

    try:
        json[playlist].remove(music_id['id_clip'])
    except:
        print("fail to remove")
    
    response = (
            ClientAPI.table("Users")
            .update({"Playlist": json})
            .eq("identifiant", current_user)
            .execute()
    )
    print(response.data)
    return 'OK'


def getVideosIdFromPlaylistYT(playlist_id):
    video_ids = []
    request = youtube.playlistItems().list(
        part="contentDetails",
        playlistId=playlist_id,
        maxResults=50
    )

    while request:
        response = request.execute()

        for item in response.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                video_ids.append(video_id)

        request = youtube.playlistItems().list_next(
            request, response
        )

    return video_ids

def prepaMusicPlaylist(musicId):
    response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .eq("id_yt", musicId)
            .execute()
    )
    if len(response.data) == 0:
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics,status,player,topicDetails,recordingDetails,liveStreamingDetails,localizations",
            id=musicId
        )
        responseYT = request.execute()
        if not responseYT["items"]:
            logging.info("Video not found")
        else:
            snippet = responseYT["items"][0]["snippet"]
            json = {
                "Title": snippet["title"],
                "img": snippet["thumbnails"]["default"]["url"],
                "id": musicId
            }
            return json
    else:
        return response.data[0]

@app.route('/loadHistorique/')
@jwt_required()
def loadHistorique():
    return loadHistoriqueRoute(get_jwt_identity(), ClientAPI)

@app.route('/loadReplay/')
@jwt_required()
def loadReplay():
    return loadReplayRoute(get_jwt_identity(), ClientAPI)


def listenMusic(id_yt, click, title, artist):
    listenMusica(id_yt, click, title, artist, get_jwt_identity(), app, ClientAPI)
    return "OK"


def insertMusic2(id_yt, title, artist, album, img):
    response = (
        ClientAPI.table("StatMusic3")
        .insert({"id_yt": id_yt, "views" : 1, "Title": title, "Artist": artist, "Album": album, "Image": img})
        .execute()
    )
    return response.data

# Route pour enregistrer une musique dans la bdd
@app.route('/insertMusic/', methods = ['POST'])
@jwt_required()
def insertMusic():
    logging.info(request.data)
    payload = json.loads(request.data.decode('utf-8'))
    logging.info(payload)
    if "title" in payload:
        searchStr = payload["title"] + "-" + payload["artist"]
    else:
        searchStr = payload["searchStr"]
        
    artist, title, album = getTrackSearchDeezer(searchStr)
    id_yt = payload["id_yt"]

    response = (
        ClientAPI.table("StatMusic3")
        .select("*")
        .eq("id_yt", id_yt)
        .execute()
    )

    if "img" in payload:
        img = payload["img"]

    #app.cur.execute(f"SELECT * FROM public.\"StatMusic3\" WHERE id_yt='{id_yt}'")
    if (len(response.data)== 0):
        logging.info(id_yt)
        logging.info(title)
        logging.info(artist)
        logging.info(album)
        
        response = (
            ClientAPI.table("StatMusic3")
            .insert({"id_yt": id_yt, "views" : 1, "Title": title, "Artist": artist, "Album": album, "Image": img})
            .execute()
        )
        #app.cur.execute(f"INSERT INTO public.\"StatMusic3\" (id_yt, views, \"Title\", \"Artist\", \"Album\") VALUES ('{id_yt}', 1, '{title.replace("'", '"')}', '{artist.replace("'", '"')}', '{album.replace("'", '"')}')")
        #app.conn.commit()
    else:
        response = (
            ClientAPI.table("StatMusic3")
            .update({"views": response.data[0]["views"] + 1})
            .eq("id_yt", id_yt)
            .execute()
        )
        #app.cur.execute(f"UPDATE public.\"StatMusic3\" SET views = views + 1 WHERE id_yt='{id_yt}'")
        #app.conn.commit()    
    
    listenMusic(id_yt, payload["Clicked"], title, artist)
    return ""


# Route pour enregistrer une musique dans la bdd
def cleanName(name):
    artist, title, album = getTrackSearchDeezer(name)
    return [artist, title, album]

@app.route('/searchYT/<searchStr>')
@jwt_required()
def searchYT(searchStr, first=False):
    """
    Recherche des vidéos sur YouTube avec l'API YouTube Data v3.
    
    :param api_key: str - Clé API YouTube Data v3
    :param requete: str - Terme de recherche
    :param max_resultats: int - Nombre maximum de résultats
    :return: list - Liste de dicts contenant titre, id vidéo et URL
    """
    
    # Requête vers l'API
    requete_api = youtube.search().list(
        q=searchStr,
        part="snippet",
        type="video",
        maxResults=20
    )
    
    resultats = requete_api.execute()
    
    if first:
        return {"id_yt": resultats.get("items", [])[0]["id"]["videoId"], "img": resultats.get("items", [])[0]["snippet"]["thumbnails"]["default"]["url"] }
    
    videos = []
    for item in resultats.get("items", []):
        if item["id"]["kind"] != "youtube#video":
            continue  # on saute tout ce qui n'est pas une vidéo
        titre = item["snippet"]["title"]
        video_id = item["id"]["videoId"]
        url = f"https://www.youtube.com/watch?v={video_id}"

        videoDict = {
            "titre": titre,
            "id": video_id,
            "url": url,
            "img": item["snippet"]["thumbnails"]["default"]["url"]
        }

        try:
            artist, title, album = cleanName(titre)
            videoDict["titre"] = artist + " - " + title
            videoDict["title"] = title
            videoDict["artist"] = artist
            videoDict["album"] = album
        except Exception as ex:
            logging.info(ex)
        videos.append(videoDict)
    
    thread = threading.Thread(target=insertDataVideoIntoDBB, args=(videos,))
    thread.start()

    return videos


def search1Music(searchStr):
    logging.info(f"Recherche YT: {searchStr}")
    try:
        results = yt.search(searchStr, filter="songs", limit=10)
    except:
        time.sleep(2)
        results = yt.search(searchStr, filter="songs", limit=10)
        
    try:
        resultsClip = yt.search(searchStr + " Clip Video", filter="videos", limit=10)
    except Exception as ex:
        logging.info(f"ex : {ex}")
        time.sleep(2)
        resultsClip = yt.search(searchStr + " Clip Video", filter="videos", limit=10)
    logging.info(results[0]["title"] + "-" + results[0]["artists"][0]["name"])
    clipId = "Not found"
    if len(resultsClip)>0 and resultsClip[0]["title"].lower() in searchStr.lower():
        logging.info(f"add {resultsClip[0]}")
        clipId = resultsClip[0]["videoId"]
    resultJSON = {"id_yt": results[0].get("videoId"), "img": results[0]["thumbnails"][0].get("url"), "clipId": clipId}
    #logging.info(f"Trouvé: {resultJSON}")
    return resultJSON

@app.route('/getMusicFromVideoID')
@jwt_required()
def getMusicFromVideoID():
    Id = request.args.get("id")
    response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .like("id_yt", Id)
            .execute()
        )  
    if len(response.data) != 0:
        return response.data[0]
    else:
        response = (
                ClientAPI.table("StatMusic3")
                .select("*")
                .like("id_clip", Id)
                .execute()
            )  
        if len(response.data) != 0:
            return response.data[0]
        else:
            return "not found"

@app.route('/getMusic')
@jwt_required()
def getMusic():
    Artist = request.args.get("artist")
    Title = request.args.get("title")
    response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .like("Title", Title)
            .like("Artist", Artist)
            .execute()
        )  
    if len(response.data) != 0:
        listenMusic(response.data[0]["id_yt"] , True, Title, Artist)
        return response.data[0]    
    else:
        for i in range(100):
            time.sleep(2)
            response = (
                ClientAPI.table("StatMusic3")
                .select("*")
                .eq("Title", Title)
                .eq("Artist", Artist)
                .execute()
            )   
            if len(response.data) != 0:
                listenMusic(response.data[0]["id_yt"] , True, Title, Artist)
                return response.data[0]
        return "Not in BDD"

def normalize(s):
    s = s.replace("/", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return urllib.parse.quote(s)

@app.route('/getLyrics')
@jwt_required()
def getLyrics():
    logging.info("get Lyrics")
    Artist = normalize(request.args.get("artist"))
    Title = normalize(request.args.get("title"))
    logging.info(Artist)
    logging.info(Title)
    try:
        logging.info(f"https://lrclib.net/api/get?artist_name={Artist}&track_name={Title}")
        response = requests.get(f"https://lrclib.net/api/get?artist_name={Artist}&track_name={Title}")
    except:
        logging.info(f"https://api.lyrics.ovh/v1/{Artist}/{Title}")
        response = requests.get(f"https://api.lyrics.ovh/v1/{Artist}/{Title}")
        if "error" in response or response.status_code != 200:
            return "lyrics not found"
        else:
            return json.loads(response.text)["lyrics"]
        
    if response.json()["name"] == "TrackNotFound" or response.status_code != 200:
        logging.info(f"https://api.lyrics.ovh/v1/{Artist}/{Title}")
        response = requests.get(f"https://api.lyrics.ovh/v1/{Artist}/{Title}")
        if "error" in response or response.status_code != 200:
            return "lyrics not found"
        else:
            return json.loads(response.text)["lyrics"]
    else:
        return json.loads(response.text)["plainLyrics"]
    
@app.route('/searchMusic/<searchStr>')
@jwt_required()
def searchMusic(searchStr):
    musics = getTrackSearchDeezerAll(searchStr)
    titleMusics = [music["Title"].lower() for music in musics]
    artistsMusics = [music["Artist"].lower() for music in musics]
    existing = (
        ClientAPI
        .table("StatMusic3")
        .select("*")
        .in_("track_key", [artist.lower() + "|" + title.lower() for (title, artist) in zip(titleMusics,artistsMusics)])
        .execute()
    )
    missing_tracks = [
        track for track in musics
        if track["Artist"].lower() + "|" + track["Title"].lower() not in [music["track_key"] for music in existing.data]
    ]
    print('existing', [i["track_key"] for i in existing.data])
    print('missing', missing_tracks)
    """ for music in musics:
        time.sleep(0.5)
        logging.info("title:")
        logging.info(music["Title"])
        logging.info("artist:")
        logging.info(music["Artist"])
        response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .ilike("Title", normaliser_titre(music["Title"]))
            .ilike("Artist", music["Artist"])
            .execute()
        )
        if len(response.data) == 0:
            music["id_yt"] = "none"
            music["Image"] = "https://upload.wikimedia.org/wikipedia/commons/9/97/Music_-_The_Noun_Project.svg"
            logging.info("not in BDD")
            musicToRegistered.append(music)
            resultMusic.append(prepaMusic(music, withYTID=True))
        else:
            logging.info("already in BDD")
            logging.info(response.data)
            resultMusic.append(prepaMusic(response.data[0])) """
    
    print("mt", missing_tracks)
    if len(missing_tracks)>0:
        thread = threading.Thread(target=insertDataVideoIntoDBB2, args=(missing_tracks,))
        thread.start()
    
    ResultList = [prepaMusic(music, withYTID=False) for music in missing_tracks]
    preparedMusicExisting = [prepaMusic(music) for music in existing.data]
    ResultList.extend(preparedMusicExisting)
    return ResultList
    
def prepaMusic(music, YTmusique={}, withYTID=True):
    videoDict = {}

    if withYTID:
        if YTmusique:
            videoDict["img"] = YTmusique["img"]
        else:
            videoDict["img"] = music["Image"]

        if YTmusique:
            video_id = YTmusique["id_yt"]
        else:
            video_id = music["id_yt"]
        videoDict["url"] = f"https://www.youtube.com/watch?v={video_id}"
        videoDict["id"] = video_id

    if 'id_clip' in music and music["id_clip"] != "Not found" and music["id_clip"] != None:
        videoDict["id_clip"] = music["id_clip"]
    else:
        videoDict["id_clip"] = "Not found"
    videoDict["titre"] = music["Artist"] + " - " + music["Title"]
    videoDict["title"] = music["Title"]
    videoDict["artist"] = music["Artist"]
    videoDict["album"] = music["Album"]
    return videoDict


def insertDataVideoIntoDBB2(videos):
    ResultVideos = []
    for video in videos:
        time.sleep(1)

        try:
            YTmusique = search1Music(video["Title"] + " - " + video["Artist"])
        except Exception as ex:
            logging.info(f"Exception recherche: {ex}")
            continue

        video["Title"] = normaliser_titre(video["Title"])
        video["id_yt"] = YTmusique["id_yt"]
        video["Image"] = YTmusique["img"]
        video["id_clip"] = YTmusique["clipId"]

        if video["id_yt"] not in [videor["id_yt"] for videor in ResultVideos]:
            ResultVideos.append(video)
    
    ClientAPI.table("StatMusic3").upsert(ResultVideos).execute()

def insertDataVideoIntoDBB(videos, From="search"):
    if From == "Sugg":
        time.sleep(5)
    t0 = time.time()
    for video in videos:
        logging.info("insert Data Video Into BDD", video)
        logging.info("-----------------------")
        logging.info(video)
        logging.info("time")
        logging.info(str(time.time() - t0))
        time.sleep(1)
        
        if From == "search":
            videoTitle= video["Title"]
            videoArtist = video["Artist"]
        else:
            videoTitle= video["name"]
            videoArtist = video["artist"]["name"]
            
        try:
            YTmusique = search1Music(videoTitle + " - " + videoArtist)
        except Exception as ex:
            logging.info(f"Exception recherche: {ex}")
            continue

        if "Album" not in video:
            video["Album"] = "NA"


        videoTitle = normaliser_titre(videoTitle)
        videoTitle = videoTitle.replace("'", "''")

        logging.info(videoTitle)
        logging.info(videoArtist)

        response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .eq("Title", videoTitle)
            .eq("Artist", videoArtist)
            .execute()
        )
 
        if (len(response.data)) == 0:
            try: 
                
                response2 = (
                    ClientAPI.table("StatMusic3")
                    .select("*")
                    .eq("id_yt", YTmusique["id_yt"])
                    .execute()
                )
                if len(response2.data) != 0:
                    ClientAPI.table("StatMusic3").delete().eq("id_yt", YTmusique["id_yt"]).execute()
            
                data = {"id_yt": YTmusique["id_yt"], "views" : 0, "Title": videoTitle, "Artist": videoArtist, "Album": video["Album"], "Image": YTmusique["img"], "id_clip": YTmusique["clipId"]}
                logging.info(f"inserting : {data}")
                response = (
                    ClientAPI.table("StatMusic3")
                    .insert(data)
                    .execute()
                )
                logging.info("video registered")
            except Exception as e:
                logging.info(e)
    logging.info("-----------------------")


def updateIncrementViews(table, col, id_yt):
    response = (
        ClientAPI.table(table)
        .select({col})
        .eq("id_yt", id_yt)
        .execute()
    )        
    value = response.data[col]
    response2 = (
        ClientAPI.table(table)
        .update({"noViews": value + 1})
        .eq("id_yt", id_yt)
        .execute()
    )

def normaliserLesTitres(liste):
    resultat = []
    vus = []

    for item in liste:
        item["title_normalize"] = normaliser_titre(item["title"])
        if item["title_normalize"] not in vus:
            vus.append(item["title_normalize"])
            resultat.append(item)

    return resultat

def normaliser_tout_les_titres():
    all_tracks = []
    BATCH_SIZE = 1000  # nombre de lignes par requête
    ind = 0

    while True:

        # Récupération d'un batch
        response = (
            ClientAPI
            .table("StatMusic3")
            .select("*")
            .is_("id_clip", "null")
            .limit(BATCH_SIZE)
            .execute()
        )
        
        batch = response.data
        if not batch:
            break  # plus de données

        for music in batch:
            ind += 1
            print(ind)
            try:
                YTmusic = search1Music(music["Artist"] + " - " + music["Title"])
            except:
                continue

            if (music["id_clip"] == "Not found" or music["id_clip"] == None) and YTmusic["clipId"] != "Not Found":
                ClientAPI.table("StatMusic3").update({"id_clip": YTmusic["clipId"]}).eq("id_yt", music["id_yt"]).execute()
            else:
                ClientAPI.table("StatMusic3").update({"id_clip": "Not found"}).eq("id_yt", music["id_yt"]).execute()

# Lancer l'application
if __name__ == "__main__":
    #search1Music("nessa muse")
    app.run(host="0.0.0.0", port=5001)
    #normaliser_tout_les_titres()
    

