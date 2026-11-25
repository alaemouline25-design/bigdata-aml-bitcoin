"""test_sources_tx.py - Jalon J1 : la source mempool.space suffit-elle a notre besoin ?

Complete test_sources.py (qui repond a : "la source repond-elle ?").
  Q1. Le detail d'une transaction permet-il de construire des aretes du graphe ?
      (on releve les champs ET les cles des elements des listes, sans rien supposer)
  Q2. Le sondage de /mempool/recent capte-t-il tout le flux, ou sature-t-il ?
  Q3. A quel debit effectif peut-on enchainer les appels de detail ?

Usage    : python test_sources_tx.py --reseau partage-mobile
Resultat : docs/resultats_J1_tx_<reseau>.json
Test volontairement sobre : ne pas augmenter les volumes (conditions d'utilisation).
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://mempool.space/api"  # chemins a confirmer dans la doc REST
HEADERS = {"User-Agent": "ensias-bigdata-projet/0.1 (projet pedagogique)"}


def get(chemin):
    """GET avec mesure de latence. Retourne (reponse, latence en secondes)."""
    t0 = time.time()
    r = requests.get(BASE + chemin, headers=HEADERS, timeout=15)
    return r, round(time.time() - t0, 2)


def decrire(objet):
    """Pour un dictionnaire : {cle: type de la valeur}. Sinon : le type seul.
    On releve la structure reelle au lieu de supposer des noms de champs."""
    if isinstance(objet, dict):
        return {k: type(v).__name__ for k, v in objet.items()}
    return type(objet).__name__


def structure_tx(txid):
    """Q1 : structure du detail d'une transaction, sur deux niveaux.
    Le second niveau dit si une entree reference la transaction qu'elle depense,
    condition necessaire pour tracer une arete du graphe."""
    info = {"txid_teste": txid}
    try:
        r, lat = get(f"/tx/{txid}")
        info.update(statut=r.status_code, latence_s=lat)
        if r.ok:
            d = r.json()
            info["champs"] = decrire(d)
            listes = {}
            for cle, valeur in d.items():
                if not isinstance(valeur, list):
                    continue
                entree = {"taille": len(valeur)}
                if valeur and isinstance(valeur[0], dict):
                    premier = valeur[0]
                    entree["cles_premier_element"] = decrire(premier)
                    # Objets imbriques dans le premier element (un niveau de plus)
                    entree["sous_objets"] = {k: decrire(v) for k, v in premier.items()
                                             if isinstance(v, dict)}
                listes[cle] = entree
            info["listes"] = listes
    except (requests.RequestException, ValueError) as e:
        info["erreur"] = str(e)
    return info


def debit_flux(duree=60, pas=5):
    """Q2 : sonde /mempool/recent toutes les `pas` s pendant `duree` s.
    Un appel est SATURE si toutes les transactions qu'il renvoie sont nouvelles :
    il en est probablement arrive d'autres, invisibles, entre deux appels."""
    vus, historique, erreurs = set(), [], 0
    fin = time.time() + duree
    while time.time() < fin:
        try:
            r, _ = get("/mempool/recent")
            if r.ok:
                lot = {t["txid"] for t in r.json() if isinstance(t, dict) and "txid" in t}
                historique.append({"taille_lot": len(lot), "nouveaux": len(lot - vus)})
                vus |= lot
            else:
                erreurs += 1
        except (requests.RequestException, ValueError):
            erreurs += 1
        time.sleep(pas)
    # Le premier appel est forcement "tout nouveau" : on l'exclut du comptage
    satures = sum(1 for h in historique[1:] if h["taille_lot"] and h["nouveaux"] == h["taille_lot"])
    resume = {
        "duree_s": duree, "pas_s": pas,
        "appels_reussis": len(historique), "erreurs": erreurs,
        "txid_distincts_vus": len(vus),
        "nouveaux_par_appel": [h["nouveaux"] for h in historique],
        "appels_satures": satures,
        "lecture": "borne inferieure du flux reel ; appels_satures > 0 => transactions manquees",
    }
    return resume, sorted(vus)


def rafale(txids, n=20, pause=0.5):
    """Q3 : n appels de detail a la suite. On releve statuts, latences,
    en-tetes de quota, et le debit effectif reellement teste."""
    statuts, lats, quota = {}, [], {}
    cibles = txids[1:n + 1]  # le premier txid a deja servi en Q1
    t0 = time.time()
    for txid in cibles:
        try:
            r, lat = get(f"/tx/{txid}")
            statuts[str(r.status_code)] = statuts.get(str(r.status_code), 0) + 1
            lats.append(lat)
            for k, v in r.headers.items():
                if k.lower().startswith(("x-ratelimit", "retry-after")):
                    quota[k] = v
        except requests.RequestException:
            statuts["erreur"] = statuts.get("erreur", 0) + 1
        time.sleep(pause)
    duree = time.time() - t0
    return {
        "appels_tentes": len(cibles), "statuts": statuts,
        "latence_min_s": min(lats) if lats else None,
        "latence_max_s": max(lats) if lats else None,
        "debit_effectif_req_s": round(len(cibles) / duree, 2) if duree > 0 else None,
        "en_tetes_quota": quota,
        "lecture": "aucun 429 = ce debit est tolere ; cela ne prouve pas l'absence de limite",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reseau", required=True,
                   help="nom court du reseau teste (ex. partage-mobile, ensias, codespace)")
    a = p.parse_args()
    reseau = re.sub(r"[^A-Za-z0-9_-]", "-", a.reseau)  # nom utilisable dans un fichier

    resultats = {"reseau": reseau,
                 "horodatage_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    print("Q2 : sondage de /mempool/recent pendant 60 s...", flush=True)
    resultats["debit_flux"], txids = debit_flux()
    if txids:
        print("Q1 : detail d'une transaction...", flush=True)
        resultats["detail_tx"] = structure_tx(txids[0])
        print("Q3 : rafale d'appels de detail...", flush=True)
        resultats["rafale_tx"] = rafale(txids)
    else:
        resultats["remarque"] = "aucun txid recupere : Q1 et Q3 non testees"

    sortie = Path("docs") / f"resultats_J1_tx_{reseau}.json"
    sortie.parent.mkdir(exist_ok=True)
    sortie.write_text(json.dumps(resultats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resultats, indent=2, ensure_ascii=False))
    print(f"\nResultat ecrit dans {sortie}")


if __name__ == "__main__":
    main()
