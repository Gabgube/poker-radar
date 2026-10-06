import json
import re
import ssl
import time
import unicodedata
import urllib.parse
import urllib.request
import certifi

def slugify(text):
    """Génère un ID propre à partir du nom et de la ville (ex: 'chope-et-compagnie-pornic')"""
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def fetch_bars(query):
    """Interroge l'API RedCactus pour un département ou un terme donné"""
    url = f"https://poker.redcactus.fr/search-bars.json?q={urllib.parse.quote(str(query))}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context(cafile=certifi.where())
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            res = json.loads(r.read().decode("utf-8"))
            return res.get("results", res if isinstance(res, list) else [])
    except Exception:
        try:
            with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=10) as r:
                res = json.loads(r.read().decode("utf-8"))
                return res.get("results", res if isinstance(res, list) else [])
        except Exception as e:
            return []

# Liste de tous les départements français (Metropole 01-95 + Corse 2A/2B + DOM)
departements = [f"{i:02d}" for i in range(1, 96)] + ["2A", "2B", "971", "972", "973", "974", "976"]

bars_dict = {}

print("Récupération de TOUS les bars RedCactus en France...")

for dep in departements:
    results = fetch_bars(dep)
    nouveaux = 0
    for item in results:
        # 1. Filtre strict : Uniquement la France (exclut Belgique BE, Suisse, etc.)
        if item.get("country") != "FR":
            continue

        # 2. Exclure les événements uniquement en ligne
        if item.get("is_online") == 1:
            continue

        bar_id = item.get("id")
        if bar_id and bar_id not in bars_dict:
            bars_dict[bar_id] = item
            nouveaux += 1

    if len(results) > 0:
        print(f"  - Dép. {dep} : {len(results)} trouvés ({nouveaux} nouveaux ajoutés)")
    
    time.sleep(0.15)  # Légère pause pour respecter le serveur

print(f"\nTOTAL UNIQUE EN FRANCE : {len(bars_dict)} bars trouvés.")

lieux = []

for bar_id, item in bars_dict.items():
    raw_name = item.get("name", "")
    clean_name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
    
    adresse1 = item.get("address1", "")
    zip_code = str(item.get("zip_code") or "")
    city = str(item.get("city") or "")
    
    adresse_parts = [p for p in [adresse1, f"{zip_code} {city}".strip()] if p]
    adresse_complete = ", ".join(adresse_parts)

    # Récupération directe des coordonnées GPS de l'API RedCactus
    # Inversion de RedCactus : item["lon"] = Latitude, item["lat"] = Longitude
    latitude = item.get("lon")
    longitude = item.get("lat")

    lieu = {
        "id": slugify(f"{clean_name} {city}"),
        "nom": f"{clean_name} (RedCactus)",
        "type": "redcactus",
        "ville": city.capitalize(),
        "adresse": adresse_complete,
        "lat": round(latitude, 6) if latitude is not None else None,
        "lng": round(longitude, 6) if longitude is not None else None,
        "gratuit": True,
        "prix": "Gratuit",
        "quand": "Selon calendrier RedCactus, inscription obligatoire",
        "inscription": {
            "type": "lien",
            "valeur": f"https://poker.redcactus.fr{item.get('url', f'/bar/{bar_id}')}",
            "libelle": f"Voir la page RedCactus de {clean_name}"
        },
        "a_verifier": "Consulter les dates et horaires exacts des prochains tournois sur la fiche RedCactus."
    }

    lieux.append(lieu)

with open("lieux.json", "w", encoding="utf-8") as f:
    json.dump(lieux, f, ensure_ascii=False, indent=2)

print(f"Fichier lieux.json créé avec succès ({len(lieux)} établissements français).")