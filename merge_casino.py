"""
Fusionne poker_casinos.csv dans casinos.json.

    python merge_poker.py

Produit :
  - casinos.json            : mis à jour (champ poker, source, date, inscription)
  - casinos_poker.json      : uniquement les casinos dont le poker est confirmé (c'est ce fichier que la carte doit charger)
"""
import csv, json, unicodedata

def norm(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").replace("-", " ").strip()

with open("casinos.json", encoding="utf-8") as f:
    casinos = json.load(f)
with open("poker_casinos.csv", encoding="utf-8-sig", newline="") as f:
    lignes = list(csv.DictReader(f, delimiter=";"))

non_trouves = []
for l in lignes:
    cible = [c for c in casinos
             if norm(c["ville"]) == norm(l["ville"])
             and (norm(l["exploitant"]) in norm(c.get("exploitant")) or norm(c.get("exploitant")) in norm(l["exploitant"]))]
    if not cible:
        non_trouves.append(f'{l["ville"]} ({l["exploitant"]})')
        continue
    for c in cible:
        c["poker"] = l["poker"]
        c["source_poker"] = l["source_url"]
        c["fiabilite_source"] = l["fiabilite"]
        c["date_verification"] = l["date_verification"]
        c["notes"] = l["notes"]
        tel = l["telephone"].strip()
        if tel:
            c["inscription"] = {"type": "telephone", "valeur": tel, "libelle": "Appeler le casino pour s'inscrire"}
        elif l["fiabilite"] == "officielle":
            c["inscription"] = {"type": "lien", "valeur": l["source_url"], "libelle": "Voir la page du casino"}

with open("casinos.json", "w", encoding="utf-8") as f:
    json.dump(casinos, f, ensure_ascii=False, indent=2)

valides = [c for c in casinos if c.get("poker") in ("tournois", "cash", "les_deux") and c.get("lat") is not None]
with open("casinos_poker.json", "w", encoding="utf-8") as f:
    json.dump(valides, f, ensure_ascii=False, indent=2)

print(f"{len(lignes)} lignes lues, {len(valides)} casinos avec poker confirmé -> casinos_poker.json")
if non_trouves:
    print("Sans correspondance dans casinos.json (vérifie le nom de la ville et de l'exploitant) :")
    for n in non_trouves:
        print("  -", n)
