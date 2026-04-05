import requests
import os

# 🔑 Remplace par ta clé CometAPI
API_KEY = "sk-c7aUGkkujKxdX0TrbxeU5Ls5S9Xj5z1XjV8skaHQpgwU9fxD"

# Fonction de recommandation
def get_music_recommendations(artist: str, title: str):
    url = "https://api.cometapi.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Prompt pour générer des recommandations
    prompt = (
        f"Liste 10 artistes et titres similaires à l'artiste '{artist}' "
        f"et la chanson '{title}', avec une courte description de pourquoi ils sont similaires."
    )

    json_data = {
        "model": "gpt-5",                # tu peux changer de modèle si besoin
        "messages": [
            {"role": "system", "content": "Vous êtes un assistant expert en musique."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300
    }

    response = requests.post(url, headers=headers, json=json_data)
    
    if response.status_code != 200:
        print("Erreur:", response.status_code, response.text)
        return None
    
    data = response.json()
    
    # Récupère le texte généré
    text = data.get("choices")[0].get("message").get("content")
    return text

# Exécution
result = get_music_recommendations("Coldplay", "Yellow")
print(result)
