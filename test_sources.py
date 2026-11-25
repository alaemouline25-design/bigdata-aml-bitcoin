"""test_sources_tx.py - Jalon J1 : 3 questions precises sur mempool.space.

Q1. Que renvoie le detail d'UNE transaction ? (entrees/sorties disponibles ?)
Q2. Combien de transactions NOUVELLES voit-on en interrogeant /mempool/recent ?
Q3. Que se passe-t-il si on enchaine ~20 appels de detail (latence, limitation) ?

Usage :  python test_sources_tx.py
Resultat : docs/resultats_J1_tx.json  (aucun champ suppose : on affiche le reel)
Le test est volontairement SOBRE (peu d'appels, pauses) : ne pas l'augmenter,
pour ne pas se faire bloquer et respecter les conditions d'utilisation.
"""
import json
import time
from pathlib import Path

import requests

BASE = "https://mempool.space/api"  # chemins a confirmer dans la doc
HEADERS = {"User-Agent": "ensias-bigdata-projet/0.1 (projet pedagogique)"}


def get(chemin):
    """GET avec mesure de latence. Retourne (reponse, latence en secondes)."""
    t0 = time.time()
    r = requests.get(BASE + chemin, headers=HEADERS, timeout=15)
    return r, round(time.time() - t0, 2)


def structure_tx(txid):
    """Q1 : champs du detail d'une transaction (endpoint /tx/<txid> a confirmer)."""
    info = {}
    try:
        r, lat = get(f"/tx/{txid}")
        info = {"statut": r.status_code, "latence_s": lat}
        if r.ok:
            d = r.json()
            info["champs"] = sorted(d.keys())
            # Pour chaque champ qui est une liste : sa taille (ex. entrees/sorties
            # si elles existent). On ne suppose pas les noms, on les releve.
            info["tailles_listes"] = {k: len(v) for k, v in d.items() if isinstance(v, list)}
    except (requests.RequestException, ValueError, AttributeError) as e:
        info["erreur"] = str(e)
    return info


def debit_flux(duree=60, pas=5):
    """Q2 : on interroge /mempool/recent toutes les `pas` s pendant `duree` s
    et on compte les txid distincts vus. Retourne (resume, liste de txid)."""
    vus, appels, erreurs = set(), 0, 0
    fin = time.time() + duree
    while time.time() < fin:
        try:
            r, _ = get("/mempool/recent")
            appels += 1
            if r.ok:
                vus.update(t["txid"] for t in r.json()
                           if isinstance(t, dict) and "txid" in t)
            else:
                erreurs += 1
        except (requests.RequestException, ValueError):
            erreurs += 1
        time.sleep(pas)
    resume = {"duree_s": duree, "pas_s": pas, "appels": appels,
              "erreurs": erreurs, "txid_distincts_vus": len(vus)}
    return resume, sorted(vus)


def rafale(txids, n=20):
    """Q3 : n appels /tx a la suite (pause 0,5 s). On releve statuts, latences
    et tout signe de limitation (code 429, en-tetes de quota)."""
    statuts, lats, quota = {}, [], {}
    for txid in txids[:n]:
        try:
            r, lat = get(f"/tx/{txid}")
            statuts[str(r.status_code)] = statuts.get(str(r.status_code), 0) + 1
            lats.append(lat)
            for k, v in r.headers.items():
                if k.lower().startswith(("x-ratelimit", "retry-after")):
                    quota[k] = v
        except requests.RequestException:
            statuts["erreur"] = statuts.get("erreur", 0) + 1
        time.sleep(0.5)
    return {"appels_tentes": min(n, len(txids)), "statuts": statuts,
            "latence_min_s": min(lats) if lats else None,
            "latence_max_s": max(lats) if lats else None,
            "en_tetes_quota": quota}


def main():
    resultats = {}
    print("Q2 : interrogation de /mempool/recent pendant 60 s...", flush=True)
    resultats["debit_flux"], txids = debit_flux()
    if txids:
        print("Q1 : detail d'une transaction...", flush=True)
        resultats["detail_tx"] = structure_tx(txids[0])
        print("Q3 : rafale de 20 appels...", flush=True)
        resultats["rafale_tx"] = rafale(txids)
    else:
        resultats["remarque"] = "aucun txid recupere : Q1 et Q3 non testees"

    Path("docs").mkdir(exist_ok=True)
    Path("docs/resultats_J1_tx.json").write_text(
        json.dumps(resultats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resultats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
