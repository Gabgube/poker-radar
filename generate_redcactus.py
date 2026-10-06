import json
import re
import time
import requests
from bs4 import BeautifulSoup

URL_MARKERS = "https://poker.redcactus.fr/map/markers.json"
OUTPUT_FILE = "redcactus.json"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("1. Téléchargement du fichier markers.json depuis Red Cactus...")

try:
    response = requests.get(URL_MARKERS, headers=headers, timeout=15)
    if response.status_code == 200:
        data = response.json()
        print("   Téléchargement réussi.")
    else:
        raise Exception(f"Erreur HTTP {response.status_code}")
except Exception as err:
    print(f"Erreur lors du téléchargement : {err}")
    exit(1)

features = data.get("features", [])
total = len(features)

print(f"\n2. Analyse et enrichissement de {total} éléments...")

features_enrichies = []

for idx, feature in enumerate(features, 1):
    raw_id = feature.get("id")
    props = feature.get("properties", {})
    type_lieu = props.get("type") or feature.get("type")
    nom = props.get("name", f"Bar #{raw_id}")

    # Ignorer les éléments sans ID et les finales / demi-finales
    if not raw_id or type_lieu in ['semi-final', 'pre-main-final']:
        continue

    # Scraping de la page du bar sur Red Cactus
    url_bar = f"https://poker.redcactus.fr/bar/{raw_id}"
    try:
        res = requests.get(url_bar, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            page_text = soup.get_text(separator=" ")

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
            print(f"[{idx}/{total}] {nom} -> Erreur HTTP {res.status_code}")

    except Exception as err:
        props["quand"] = "Tournois réguliers"
        print(f"[{idx}/{total}] {nom} -> Erreur : {err}")

    features_enrichies.append(feature)
    time.sleep(0.05)

data["features"] = features_enrichies

print(f"\n3. Sauvegarde dans {OUTPUT_FILE}...")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nTerminé ! {len(features_enrichies)} bars enregistrés dans {OUTPUT_FILE}.")