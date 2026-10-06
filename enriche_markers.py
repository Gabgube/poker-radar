import json
import re
import time
import requests
from bs4 import BeautifulSoup

# 1. Chargement de markers.json
with open("markers.json", "r", encoding="utf-8") as f:
    data = json.load(f)

features = data.get("features", [])
total = len(features)

print(f"Analyse de {total} établissements en cours...")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

for idx, feature in enumerate(features, 1):
    bar_id = feature.get("id")
    props = feature.get("properties", {})
    nom = props.get("name", f"Bar #{bar_id}")

    if not bar_id:
        continue

    url = f"https://poker.redcactus.fr/bar/{bar_id}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text(separator=" ")

            # Recherche des jours de la semaine
            match = re.search(
                r"(Chaque\s+\w+|Tous les\s+\w+|\b(Lundi|Mardi|Mercredi|Jeudi|Vendredi|Samedi|Dimanche)\b[^\n.]{0,30})",
                page_text,
                re.IGNORECASE
            )

            if match:
                jour = match.group(0).strip().capitalize()
                props["quand"] = jour
                print(f"[{idx}/{total}] {nom} -> {jour}")
            else:
                props["quand"] = "Tournois réguliers"
                print(f"[{idx}/{total}] {nom} -> Jour non détecté")
        else:
            props["quand"] = "Tournois réguliers"
            print(f"[{idx}/{total}] {nom} -> Erreur HTTP {response.status_code}")

    except Exception as err:
        props["quand"] = "Tournois réguliers"
        print(f"[{idx}/{total}] {nom} -> Erreur : {err}")

    # Pause pour respecter le serveur
    time.sleep(0.15)

# 2. Sauvegarde du fichier enrichi
with open("markers.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\nTerminé ! Le fichier markers.json a été mis à jour.")