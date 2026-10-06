"""
Construit casinos.json à partir de la liste officielle des casinos (data.gouv.fr).

Usage :
    python casinos.py            # Loire-Atlantique seulement (par défaut)
    python casinos.py tous       # toute la France

Si le téléchargement échoue, télécharge le CSV à la main, enregistre-le
sous le nom casinos_officiel.csv dans ce dossier, et relance le script.
"""
import csv, difflib, io, json, os, re, ssl, sys, time, unicodedata
import urllib.parse, urllib.request

API_DATASET = "https://www.data.gouv.fr/api/1/datasets/liste-des-casinos-de-france/"
CSV_LOCAL = "casinos_officiel.csv"
# Par défaut, DEPARTEMENT est à None (toute la France).
# Si un paramètre est passé (ex: python generate_casinos.py 44), on filtre sur ce département.
DEPARTEMENT = sys.argv[1] if (len(sys.argv) > 1 and sys.argv[1] != "tous") else None

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "carte-poker-france/0.1 (projet etudiant)"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return r.read()

def url_du_csv():
    data = json.loads(http_get(API_DATASET))
    csvs = [r for r in data.get("resources", []) if (r.get("format") or "").lower() == "csv"]
    if not csvs:
        raise RuntimeError("Aucun fichier CSV trouvé dans le jeu de données.")
    csvs.sort(key=lambda r: r.get("last_modified") or "", reverse=True)
    print("Fichier retenu :", csvs[0].get("title"), "-", csvs[0].get("last_modified"))
    return csvs[0]["url"]

def lire_csv():
    if os.path.exists(CSV_LOCAL):
        raw = open(CSV_LOCAL, "rb").read()
        print("Lecture du fichier local", CSV_LOCAL)
    else:
        print("Téléchargement de la liste officielle...")
        raw = http_get(url_du_csv())
    try:
        texte = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        texte = raw.decode("cp1252")
    l1 = texte.splitlines()[0]
    delim = ";" if l1.count(";") >= l1.count(",") else ","
    return list(csv.DictReader(io.StringIO(texte), delimiter=delim))

def trouver(row, *mots):
    for col, val in row.items():
        c = (col or "").lower()
        if any(m in c for m in mots):
            return (val or "").strip()
    return ""

GROUPES = {"Joagroupe": "JOA", "Barriere": "Barrière", "Barriere/Desseigne": "Barrière/Desseigne"}

def joli(txt):
    t = " ".join(txt.replace("- ", "-").replace(" -", "-").title().split())
    return GROUPES.get(t, t)

def norm(txt):
    t = unicodedata.normalize("NFD", txt.lower())
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn").strip()

# Noms du CSV qui ne correspondent pas à une commune officielle -> nom de la commune
CORRECTIONS = {
    "cap-d'agde": "Agde", "antibes-juan-les-pins": "Antibes", "royat-chamalieres": "Royat",
    "dunkerque-malo-les-bains": "Dunkerque", "le touquet": "Le Touquet-Paris-Plage",
    "argeles-plage": "Argelès-sur-Mer", "la-faute-sur-mer": "La Faute-sur-Mer",
    "les sables d'olonne": "Les Sables-d'Olonne", "gosier-les-bains": "Le Gosier",
    "frehel-les-sables d'or": "Fréhel", "santenay-les-bains": "Santenay",
    "cazaubon-barbotan": "Cazaubon", "chamonix": "Chamonix-Mont-Blanc",
    "saint-gilles": "Saint-Paul", "berck-sur-mer": "Berck", "evian-les-bains": "Évian-les-Bains",
    "hauteville-lompnes": "Plateau d'Hauteville",
    "saint-gervais": "Saint-Gervais-les-Bains", "megeve": "Megève",
}

rows = lire_csv()
if not rows:
    sys.exit("Le CSV est vide.")
print("\nColonnes du fichier :", list(rows[0].keys()))
print("Première ligne      :", rows[0], "\n")

casinos = []
for row in rows:
    dep = trouver(row, "départ", "depart")
    brut = trouver(row, "commune", "ville", "établissement", "etablissement")
    groupe = trouver(row, "groupe", "exploit", "société", "societe")
    if not brut:
        continue
    if DEPARTEMENT and not (dep.startswith(DEPARTEMENT) or "loire-atlantique" in dep.lower()):
        continue
    # "VICHY "GRAND CAFÉ"" -> commune "Vichy" + lieu "Grand Café"
    m = re.match(r'^(.*?)\s*"(.+?)"\s*$', brut)
    commune_csv, lieu = (m.group(1), joli(m.group(2))) if m else (brut, "")
    commune = joli(commune_csv)
    ville_api = CORRECTIONS.get(norm(commune), commune)
    nom = f"Casino {joli(groupe)} de {commune}" if groupe else f"Casino de {commune}"
    if lieu:
        nom += f" – {lieu}"
    casinos.append({"dep": dep, "commune": commune, "ville_api": ville_api,
                    "lieu": lieu, "nom": nom, "exploitant": joli(groupe)})

def communes(**params):
    q = {"fields": "nom,centre,codeDepartement", "boost": "population"}
    q.update(params)
    return json.loads(http_get("https://geo.api.gouv.fr/communes?" + urllib.parse.urlencode(q)))

_cache_dep = {}

def communes_du_departement(cd):
    if cd not in _cache_dep:
        _cache_dep[cd] = json.loads(http_get(f"https://geo.api.gouv.fr/departements/{cd}/communes?fields=nom,centre"))
    return _cache_dep[cd]

def simplifier(nom):
    return " ".join(norm(nom).replace("-", " ").replace("'", " ").split())

def geocoder(c):
    """Renvoie (lat, lng, approx). approx=True si la commune n'a pas été trouvée dans le bon département."""
    code = c["dep"].split(" - ")[0].strip()
    codes = [code] + (["2A", "2B"] if code == "20" else [])
    for cd in codes:                                   # 1) avec le département
        res = communes(nom=c["ville_api"], codeDepartement=cd, limit=1)
        if res:
            lng, lat = res[0]["centre"]["coordinates"]
            return lat, lng, False
    res = communes(nom=c["ville_api"], limit=5)        # 2) sans filtre : on prend ce qui est dans le bon département
    for r in res:
        if r.get("codeDepartement") in codes:
            lng, lat = r["centre"]["coordinates"]
            return lat, lng, False
    if res:                                            # 3) dernier recours : meilleure correspondance, à vérifier
        lng, lat = res[0]["centre"]["coordinates"]
        return lat, lng, True
    for cd in codes:                                   # 4) comparaison approchée avec toutes les communes du département
        try:
            liste = {simplifier(r["nom"]): r for r in communes_du_departement(cd)}
        except Exception:
            continue
        proche = difflib.get_close_matches(simplifier(c["ville_api"]), list(liste), n=1, cutoff=0.6)
        if proche:
            lng, lat = liste[proche[0]]["centre"]["coordinates"]
            return lat, lng, True
    return None, None, False

print(len(casinos), "casinos retenus. Géolocalisation (centre de la commune, API geo.api.gouv.fr)...\n")

resultat, echecs = [], []
for i, c in enumerate(casinos, 1):
    try:
        lat, lng, approx = geocoder(c)
    except Exception as e:
        print("  erreur géocodage", c["commune"], e)
        lat = lng = None; approx = False
    marque = " (APPROXIMATIF, à vérifier)" if approx else ""
    print(f"[{i}/{len(casinos)}] {c['nom']} -> {lat}, {lng}{marque}")
    if lat is None:
        echecs.append(f'{c["nom"]}   [département CSV : {c["dep"]}]')
    resultat.append({
        "id": f"cas_{i}",
        "nom": c["nom"],
        "type": "casino",
        "ville": c["commune"],
        "departement": c["dep"],
        "adresse": f"{c['commune']} (adresse exacte à compléter)",
        "lat": lat, "lng": lng,
        "position_approximative": approx,
        "exploitant": c["exploitant"],
        "poker": "a_verifier",      # valeurs : tournois, cash, les_deux, non, a_verifier
        "gratuit": False,
        "prix": "À renseigner",
        "quand": "À renseigner",
        "inscription": None
    })
    time.sleep(0.1)

with open("casinos.json", "w", encoding="utf-8") as f:
    json.dump(resultat, f, ensure_ascii=False, indent=2)
print(f"\nTerminé : {len(resultat)} casinos écrits dans casinos.json (poker = a_verifier pour tous).")
if echecs:
    print(f"\n{len(echecs)} casinos sans coordonnées :")
    for e in echecs:
        print("  -", e)