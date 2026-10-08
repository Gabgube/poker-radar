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

print(f"\n2. Analyse, aplatissement et enrichissement de {total} éléments...")

bars_nettoyes = []

for idx, feature in enumerate(features, 1):
    raw_id = feature.get("id")
    props = feature.get("properties", {})
    geometry = feature.get("geometry", {})
    coordinates = geometry.get("coordinates", [])
    
    type_lieu = props.get("type") or feature.get("type")
    nom = props.get("name") or props.get("nom") or f"Bar #{raw_id}"

    # 1. Ignorer les éléments sans ID, sans GPS ou les finales / demi-finales
    if not raw_id or type_lieu in ['semi-final', 'pre-main-final'] or len(coordinates) < 2:
        continue

    # 2. Extraction et inversion des coordonnées : GeoJSON (lng, lat) -> float(lat), float(lng)
    lng, lat = float(coordinates[0]), float(coordinates[1])

    # 3. Scraping du jour de tournoi
    url_bar = f"https://poker.redcactus.fr/bar/{raw_id}"
    quand = "Tournois réguliers"

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
                quand = match.group(0).strip().capitalize()
                print(f"[{idx}/{total}] {nom} -> {quand}")
            else:
                print(f"[{idx}/{total}] {nom} -> Jour non détecté")
        else:
            print(f"[{idx}/{total}] {nom} -> Erreur HTTP {res.status_code}")

    except Exception as err:
        print(f"[{idx}/{total}] {nom} -> Erreur : {err}")

    # 4. Construction de l'objet plat standardisé avec ID brut intact
    bar_clean = {
        "id": f"rc_{raw_id}",
        "nom": nom,
        "type": "bar",
        "poker": "tournois",
        "gratuit": True,
        "lat": lat,
        "lng": lng,
        "adresse": props.get("adresse") or props.get("address") or "",
        "date": quand,
        "url": url_bar
    }

    bars_nettoyes.append(bar_clean)
    time.sleep(0.05)

# 5. Sauvegarde directe sous forme de tableau d'objets JSON [ {...}, {...} ]
print(f"\n3. Sauvegarde dans {OUTPUT_FILE}...")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(bars_nettoyes, f, ensure_ascii=False, indent=2)

print(f"\nTerminé ! {len(bars_nettoyes)} bars enregistrés dans {OUTPUT_FILE}.")