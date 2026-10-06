import json
import re
import ssl
import unicodedata
import urllib.parse
import urllib.request
import certifi

def slugify(text):
    """Génère un ID propre (ex: 'Vertical' Art' -> 'vertical-art')"""
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

# URL exacte de l'API RedCactus
URL_API = "https://poker.redcactus.fr/search-bars.json?q=44"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

print("Téléchargement des bars RedCactus du 44...")

req = urllib.request.Request(URL_API, headers=headers)
ssl_context = ssl.create_default_context(cafile=certifi.where())

try:
    with urllib.request.urlopen(req, context=ssl_context, timeout=15) as r:
        raw_data = json.loads(r.read().decode("utf-8"))
except Exception:
    # Mode de secours en cas de problème de certificat SSL
    with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=15) as r:
        raw_data = json.loads(r.read().decode("utf-8"))

elements = raw_data.get("results", raw_data if isinstance(raw_data, list) else [])
lieux = []

for item in elements:
    # Ignorer les évènements uniquement en ligne
    if item.get("is_online") == 1:
        continue

    bar_id_redcactus = item.get("id")
    raw_name = item.get("name", "")
    
    # Nettoyage du nom (ex: "Vertical' Art (Nantes)" -> "Vertical' Art")
    clean_name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
    
    adresse1 = item.get("address1", "")
    zip_code = str(item.get("zip_code") or "")
    city = str(item.get("city") or "")
    
    adresse_parts = [p for p in [adresse1, f"{zip_code} {city}".strip()] if p]
    adresse_complete = ", ".join(adresse_parts)

    lieu = {
        "id": slugify(clean_name),
        "nom": f"{clean_name} (RedCactus)",
        "type": "redcactus",
        "ville": city.capitalize(),
        "adresse": adresse_complete,
        "lat": None,
        "lng": None,
        "gratuit": True,
        "prix": "Gratuit",
        "quand": "Selon calendrier RedCactus, inscription obligatoire",
        "inscription": {
            "type": "lien",
            "valeur": f"https://poker.redcactus.fr/bar/{bar_id_redcactus}" if bar_id_redcactus else "https://poker.redcactus.fr/",
            "libelle": f"Voir la page RedCactus de {clean_name}"
        },
        "a_verifier": "Consulter les dates et horaires exacts des prochains tournois sur la fiche RedCactus."
    }

    lieux.append(lieu)

with open("lieux.json", "w", encoding="utf-8") as f:
    json.dump(lieux, f, ensure_ascii=False, indent=2)

print(f"Succès : {len(lieux)} établissements générés dans lieux.json.")