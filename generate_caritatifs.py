import csv
import json
import time
import urllib.request
import urllib.parse
import ssl

# Contournement SSL si besoin
ssl_context = ssl._create_unverified_context()

# URL de publication CSV du Google Sheet
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ12t8_TrPVdbeTurKo581f2dpQDKVVaRcO1e5zq4Xiuq5ygswfueMtHau1xyVN4T6t5jmj0cnnYmzU/pub?output=csv"

print("Téléchargement des réponses Google Forms...")

caritatifs_json = []

try:
    req = urllib.request.Request(SHEET_CSV_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ssl_context) as response:
        lines = [line.decode('utf-8', errors='ignore') for line in response.readlines()]
        reader = csv.DictReader(lines)

        for idx, raw_row in enumerate(reader, 1):
            # Nettoyage automatique des clés et des valeurs (supprime \xa0, espaces en début/fin)
            row = {k.strip(): v.strip() for k, v in raw_row.items() if k}

            # Extraction des champs avec les noms propres après nettoyage
            nom_event = row.get("Nom de l'événement ou de l'association", "")
            lieu_nom = row.get("Nom de l'établissement", "")
            adresse_brute = row.get("Adresse complète (Rue, Code postal, Ville)", "")
            quand = row.get("Date et Horaires", "Date à confirmer")
            prix = row.get("Modalités de l'inscription", "Payant")
            lien = row.get("Lien vers la billetterie", "")

            # Si l'événement ou l'adresse est manquant, on passe à la suite
            if not nom_event or not adresse_brute:
                continue

            # Géolocalisation via l'API BAN (data.gouv.fr)
            query_geo = f"{lieu_nom} {adresse_brute}".strip()
            encoded_addr = urllib.parse.quote(query_geo)
            geo_url = f"https://api-adresse.data.gouv.fr/search/?q={encoded_addr}&limit=1"
            
            lat, lng = None, None
            adresse_validee = adresse_brute

            try:
                geo_req = urllib.request.Request(geo_url, headers={'User-Agent': 'ScriptCaritatifs/1.0'})
                with urllib.request.urlopen(geo_req, context=ssl_context) as res:
                    geo_data = json.loads(res.read().decode('utf-8'))
                    features = geo_data.get('features', [])
                    if features:
                        coords = features[0]['geometry']['coordinates'] # [lng, lat]
                        lng, lat = coords[0], coords[1]
                        adresse_validee = features[0]['properties'].get('label', adresse_brute)
            except Exception as e:
                print(f"Erreur géo pour {nom_event}: {e}")

            if lat and lng:
                # Formatage du champ gratuité
                is_gratuit = "gratuit" in prix.lower() or prix.strip() in ["0", "0€"]
                
                # Construction du lien d'inscription
                lien_formatted = ""
                if lien:
                    lien_formatted = lien if lien.startswith("http") else f"https://{lien}"

                item = {
                    "id": 4000 + idx,
                    "nom": f"{nom_event} ({lieu_nom})" if lieu_nom else nom_event,
                    "type": "caritatif",
                    "lat": lat,
                    "lng": lng,
                    "adresse": adresse_validee,
                    "quand": quand,
                    "prix": prix,
                    "gratuit": is_gratuit,
                    "inscription": {
                        "type": "url",
                        "valeur": lien_formatted,
                        "libelle": "En savoir plus / S'inscrire"
                    }
                }
                caritatifs_json.append(item)
                print(f"[{idx}] Ajouté : {nom_event} ({adresse_validee})")
            else:
                print(f"[{idx}] Adresse introuvable pour : {nom_event} ({adresse_brute})")

            time.sleep(0.2)

except Exception as err:
    print(f"Erreur de lecture du Google Sheet : {err}")

# Sauvegarde du fichier JSON
with open("caritatifs.json", "w", encoding="utf-8") as f:
    json.dump(caritatifs_json, f, ensure_ascii=False, indent=2)

print(f"\nTerminé ! {len(caritatifs_json)} tournois caritatifs enregistrés dans caritatifs.json.")