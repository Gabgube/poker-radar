"""
Génère casinos.json à partir du Google Sheet (exporté en CSV).
Filtre : Exclut les casinos marqués "Non" et catégorise le poker :
        - 'cash' (Cash Game uniquement)
        - 'tournois' (Tournois uniquement)
        - 'les_deux' (Cash Game + Tournois)
        - 'a_verifier' (Autre / Non spécifié)

Colonnes reconnues : n°, ville, exploitant, lieu, Poker ?, adresse, telephone
"""

import csv
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request

# --- METS TON LIEN CSV GOOGLE SHEETS ICI ---
# Format recommandé : https://docs.google.com/spreadsheets/d/ID_DE_TON_FICHIER/export?format=csv
URL_SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSTZq18FLR7Svfn6PeISmF0ZaKstVpkePsFKTPnF3g2Xq8XtAbJrOfnXBV4YV3inSYdxBrLQ7wXxIPV/pub?output=csv"

# Contexte SSL sécurisé
try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "carte-poker-france/0.1"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return r.read()

def lire_csv_depuis_sheet(url):
    print("Téléchargement des données depuis Google Sheets...")
    raw = http_get(url)
    texte = raw.decode("utf-8-sig")
    
    if "<!DOCTYPE html>" in texte or "<html" in texte:
        sys.exit("❌ L'URL renvoie une page HTML. Assure-toi d'utiliser le bon lien d'export CSV (/export?format=csv).")

    lignes = texte.splitlines()
    if not lignes:
        return []
    delim = ";" if lignes[0].count(";") >= lignes[0].count(",") else ","
    return list(csv.DictReader(lignes, delimiter=delim))

def geocoder(ville):
    """Géolocalisation via l'API geo.api.gouv.fr"""
    if not ville:
        return None, None, False
    try:
        url = "https://geo.api.gouv.fr/communes?" + urllib.parse.urlencode({
            "nom": ville.strip(),
            "fields": "centre",
            "limit": 1
        })
        res = json.loads(http_get(url))
        if res:
            lng, lat = res[0]["centre"]["coordinates"]
            return lat, lng, False
    except Exception as e:
        print(f"  Erreur lors de la géolocalisation de {ville}: {e}")
    return None, None, True

def classifier_poker(val):
    """
    Analyse la chaîne de caractères issue du Sheet et retourne :
    'cash', 'tournois', 'les_deux', 'non', ou 'a_verifier'.
    """
    v = (val or "").strip().lower()
    
    # 1. Cas d'exclusion
    if v in ["non", "no", "false", "0", "aucun", "none"]:
        return "non"
    
    # 2. Analyse des mots-clés
    a_cash = any(k in v for k in ["cash", "cg", "cash-game", "cash game"])
    a_tournoi = any(k in v for k in ["tournoi", "tournois", "mtt", "mtt/"])
    a_les_deux = any(k in v for k in ["les deux", "les_deux", "tous", "tout", "les 2", "cash + tournoi", "tournoi + cash"])

    if a_les_deux or (a_cash and a_tournoi):
        return "les_deux"
    elif a_cash:
        return "cash"
    elif a_tournoi:
        return "tournois"
    elif v in ["oui", "yes", "vrai", "true"]:
        # Si c'est juste "Oui" sans précision, on met 'les_deux' ou 'a_verifier' selon la convention
        return "les_deux"
    
    return "a_verifier"

import re

def normaliser_telephone(tel_raw):
    if not tel_raw:
        return ""
    
    # 1. Ne garder que les chiffres et le '+'
    cleand = re.sub(r"[^\d+]", "", str(tel_raw).strip())
    
    # 2. Convertir +33X... ou 33X... au format local 0X...
    if cleand.startswith("+33"):
        cleand = "0" + cleand[3:]
    elif cleand.startswith("33") and len(cleand) == 11:
        cleand = "0" + cleand[2:]
        
    # 3. Formater en blocs de 2 chiffres si c'est un numéro français à 10 chiffres (0X XX XX XX XX)
    if len(cleand) == 10 and cleand.startswith("0"):
        return " ".join([cleand[i:i+2] for i in range(0, 10, 2)])
    
    return cleand

if __name__ == "__main__":
    if "TON_LIEN_ICI" in URL_SHEET_CSV:
        sys.exit("❌ Pense à remplacer URL_SHEET_CSV par ton lien au format CSV !")

    rows = lire_csv_depuis_sheet(URL_SHEET_CSV)
    if not rows:
        sys.exit("❌ Aucune donnée trouvée dans le CSV.")

    print(f"Colonnes détectées : {list(rows[0].keys())}\n")

    resultat = []
    ignores = 0

    for i, row in enumerate(rows, 1):
        ville = (row.get("ville") or "").strip()
        exploitant = (row.get("exploitant") or "").strip()
        lieu = (row.get("lieu") or "").strip()
        poker_raw = row.get("Poker ?") or row.get("Poker") or ""
        adresse = (row.get("adresse") or "").strip()
        tel = (row.get("telephone") or "").strip()
        web = (row.get("site web") or "").strip()

        poker_type = classifier_poker(poker_raw)
        tel = normaliser_telephone(tel)

        # Exclusion des établissements sans poker
        if poker_type == "non" or poker_type == "a_verifier":
            ignores += 1
            continue

        if not ville and not lieu:
            continue

        # Formattage du nom (ex: Casino Barrière - Deauville)
        nom_base = f"Casino {exploitant}".strip() if exploitant else "Casino"
        if lieu:
            nom = f"{nom_base} - {lieu}"
        elif ville:
            nom = f"{nom_base} de {ville}"
        else:
            nom = nom_base

        # Géolocalisation
        lat, lng, approx = geocoder(ville)

        cas_data = {
            "id": f"cas_{len(resultat) + 1}",
            "nom": nom,
            "type": "casino",
            "ville": ville,
            "adresse": adresse or (f"{ville}" if ville else "Adresse non spécifiée"),
            "telephone": tel,
            "lat": lat,
            "lng": lng,
            "position_approximative": approx,
            "exploitant": exploitant,
            "poker": poker_type,  # 'cash', 'tournois', 'les_deux', ou 'a_verifier'
            "gratuit": False,
            "web" : web
        }

        resultat.append(cas_data)
        print(f"[{len(resultat)}] {nom} ({ville}) -> Offre Poker: {poker_type} | Coordonnées: {lat}, {lng}")
        time.sleep(0.05)

    # Sauvegarde du JSON
    with open("casinos.json", "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Terminé : {len(resultat)} casinos conservés dans casinos.json.")
    print(f"ℹ️ {ignores} casinos ignorés car 'Poker ?' = Non.")