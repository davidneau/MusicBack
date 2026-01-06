from flask import Flask, render_template, request
from fetchData import getSimilarTrack
from flask_cors import CORS
import json
import threading
import psycopg2
import os
from methods.tracks import getTrackSearchDeezer, getTrackSearchDeezerAll, listenMusica, loadHistoriqueRoute, loadReplayRoute, normaliser_titre
from googleapiclient.discovery import build
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
import os
from supabase import create_client
from ytmusicapi import YTMusic
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s -%(message)s"
)

yt = YTMusic()  # pas d'auth nécessaire pour juste chercher

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=15)

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Activer CORS pour toutes les routes et pour toutes les origines
CORS(app, resources={r"/*": {"origins": "*"}})

#DATABASE_URL = "postgres://postgres:Dragon-49@db.abcdefghijklmnopqrst.supabase.co:5432/postgres"

DATABASE_URL = "https://qtkheteiebuzzedvlrtn.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF0a2hldGVpZWJ1enplZHZscnRuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzMzU3MTIsImV4cCI6MjA3OTkxMTcxMn0.vp-JoA-6T-kpOahwI__SwKXVUyaxF82LPfnyQA7ZGy8"

ClientAPI = create_client(DATABASE_URL, API_KEY)

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
    #users = app.cur.fetchall()
    if (len(users) != 0):
        logging.info(users[0])
        if bcrypt.check_password_hash(users[0]["password"], password):
            token = create_access_token(identity=identifiant)
            return jsonify(access_token=token), 200
    return jsonify(msg="Invalid credentials"), 401

@app.get('/profile')
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    return jsonify(user=current_user), 200

@app.route('/getSimilarTrack/<string:search>')
@jwt_required()
def getSimilarTrackRoute(search):
    logging.info(search)
    
    similarTrack = getSimilarTrack(search)
    Title = similarTrack["Title"]
    Artist = similarTrack["Artist"]
    Album = similarTrack["Album"]
    response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .eq("Title", Title)
            .eq("Artist", Artist)
            .execute()
        )  
    if len(response.data) == 0:
        YTmusique = search1Music(Title + " - " + Artist)
        response = (
                    ClientAPI.table("StatMusic3")
                    .insert({"id_yt": YTmusique["id_yt"], "views" : 0, "Title": Title, "Artist":Artist, "Album": Album, "Image": YTmusique["img"]})
                    .execute()
            )
        listenMusic(YTmusique["id_yt"] , False, Title, Artist)
        return {"yt_id" : YTmusique["id_yt"], "Title" : Title, "Artist" : Artist}
    else:
        logging.info("already in BDD")
        logging.info(response.data)
        listenMusic(response.data[0]["id_yt"] , False, Title, Artist)
        return {"yt_id" : response.data[0]["id_yt"], "Title" : Title, "Artist" : Artist}

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
    youtube = build("youtube", "v3", developerKey='AIzaSyA8apjRRfjCHmu6M_4q_r3kUbnO_qJ7xfk')
    
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
    
    #thread = threading.Thread(target=insertDataVideoIntoDBB, args=(videos,))
    #thread.start()

    return videos


def search1Music(searchStr):
    results = yt.search(searchStr, filter="songs", limit=10)
    return {"id_yt": results[0].get("videoId"), "img": results[0]["thumbnails"][0].get("url")}

@app.route('/getMusic/<searchStr>')
@jwt_required()
def getMusic(searchStr):
    Artist = searchStr.split("-")[0]
    Title = searchStr.split("-")[1]
    logging.info(Artist)
    logging.info(Title)
    print(Artist)
    print(Title)
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
    else:
        return "Not in BDD"

@app.route('/searchMusic/<searchStr>')
@jwt_required()
def searchMusic(searchStr):
    musics = getTrackSearchDeezerAll(searchStr)
    resultMusic = []
    musicToRegistered = []
    for music in musics:
        logging.info("title:")
        logging.info(music["Title"])
        logging.info("artist:")
        logging.info(music["Artist"])
        response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .ilike("Title", music["Title"])
            .ilike("Artist", music["Artist"])
            .execute()
        )      
        if len(response.data) == 0:
            logging.info("not in BDD")
            musicToRegistered.append(music)
            resultMusic.append(prepaMusic(music, withYTID=False))
        else:
            logging.info("already in BDD")
            logging.info(response.data)
            resultMusic.append(prepaMusic(response.data[0]))
    
    thread = threading.Thread(target=insertDataVideoIntoDBB, args=(musicToRegistered,))
    thread.start()
    
    return normaliserLesTitres(resultMusic)
    
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


    videoDict["titre"] = music["Artist"] + " - " + music["Title"]
    videoDict["title"] = music["Title"]
    videoDict["artist"] = music["Artist"]
    videoDict["album"] = music["Album"]
    return videoDict

def insertDataVideoIntoDBB(videos):
    t0 = time.time()
    for video in videos:
        logging.info("-----------------------")
        logging.info(video)
        logging.info("time")
        logging.info(str(time.time() - t0))
        time.sleep(1)
        
        YTmusique = search1Music(video["Title"] + " - " + video["Artist"])
        
        response = (
            ClientAPI.table("StatMusic3")
            .select("*")
            .eq("Title", video["Title"])
            .eq("Artist", video["Artist"])
            .execute()
        )
 
        if (len(response.data)) == 0:
            try: 
                response = (
                    ClientAPI.table("StatMusic3")
                    .insert({"id_yt": YTmusique["id_yt"], "views" : 0, "Title": video["Title"], "Artist": video["Artist"], "Album": video["Album"], "Image": YTmusique["img"]})
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
    vus = set()

    for item in liste:
        titre_normalise = normaliser_titre(item["titre"])
        if titre_normalise not in vus:
            vus.add(titre_normalise)
            resultat.append(item)

    return resultat

# Lancer l'application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

