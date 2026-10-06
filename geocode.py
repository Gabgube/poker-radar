"""Remplit lat/lng dans lieux.json à partir des adresses (API Adresse du gouvernement, gratuite)."""
import json
import ssl
import urllib.parse
import urllib.request
import certifi

FICHIER = "lieux.json"

# Contexte SSL sécurisé avec le trousseau de certificats certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())

with open(FICHIER, encoding="utf-8") as f:
    lieux = json.load(f)

for l in lieux:
    if l.get("lat") is not None and l.get("lng") is not None:
        continue

    url = "https://api-adresse.data.gouv.fr/search/?limit=1&q=" + urllib.parse.quote(l["adresse"])
    
    # On passe le context SSL à urlopen
    with urllib.request.urlopen(url, context=ssl_context, timeout=15) as r:
        data = json.load(r)

    if not data["features"]:
        print("INTROUVABLE :", l["nom"], "-", l["adresse"])
        continue

    feat = data["features"][0]
    lng, lat = feat["geometry"]["coordinates"]
    l["lat"], l["lng"] = round(lat, 6), round(lng, 6)
    print(f'{l["nom"]} -> {lat:.5f}, {lng:.5f}  (trouvé : {feat["properties"]["label"]}, score {feat["properties"]["score"]:.2f})')

with open(FICHIER, "w", encoding="utf-8") as f:
    json.dump(lieux, f, ensure_ascii=False, indent=2)

print("lieux.json mis à jour.")