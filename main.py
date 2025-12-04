from flask import Flask, render_template, request
from fetchData import getSimilarTrack
from flask_cors import CORS
import json
import threading
import psycopg2
import os
from methods.tracks import getTrackSearchDeezer, listenMusica, loadHistoriqueRoute, loadReplayRoute
from googleapiclient.discovery import build
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
import os
from supabase import create_client

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

#conn = psycopg2.connect(DATABASE_URL)
#app.conn = conn
#app.cur = conn.cursor()
#conn.autocommit = True  # plus besoin de rollback
#cur = conn.cursor()

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
    print("response", response.data)
    #users = app.cur.fetchall()
    if (len(users) != 0):
        print(users[0])
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
    print(search)
    return getSimilarTrack(search)

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

# Route pour enregistrer une musique dans la bdd
@app.route('/insertMusic/', methods = ['POST'])
@jwt_required()
def insertMusic():
    print(request.data)
    payload = json.loads(request.data.decode('utf-8'))
    print(payload)
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
    print(f"SELECT * FROM public.\"StatMusic3\" WHERE id_yt='{id_yt}'")
    #app.cur.execute(f"SELECT * FROM public.\"StatMusic3\" WHERE id_yt='{id_yt}'")
    if (len(response.data)== 0):
        print(id_yt)
        print(title)
        print(artist)
        print(album)
        
        response = (
            ClientAPI.table("StatMusic3")
            .insert({"id_yt": id_yt, "views" : 1, "Title": title, "Artist": artist, "Album": album})
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
def searchYT(searchStr):
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
            print(ex)
        videos.append(videoDict)
    
    thread = threading.Thread(target=insertDataVideoIntoDBB, args=(videos,))
    thread.start()

    return videos

def insertDataVideoIntoDBB(videos):
    for video in videos:
        print(video)
        if "title" in video:
            response = (
                ClientAPI.table("StatMusic3")
                .select("*")
                .eq("id_yt", video["id"])
                .execute()
            )
            #app.cur.execute(f"SELECT * FROM public.\"StatMusic3\" WHERE id_yt='{video["id"]}'")
            if (len(response.data)) == 0:
                    response = (
                        ClientAPI.table("StatMusic3")
                        .insert({"id_yt": video["id"], "views" : 0, "Title": video["title"], "Artist": video["artist"], "Album": video["album"]})
                        .execute()
                    )
                    #app.cur.execute(f"INSERT INTO public.\"StatMusic3\" (id_yt, views, \"Title\", \"Artist\", \"Album\") VALUES ('{video["id"]}', 0, '{video["title"].replace("'", '"')}', '{video["artist"].replace("'", '"')}', '{video["album"].replace("'", '"')}')")
                    #app.conn.commit()
                    print("video registered")


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


# Lancer l'application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

