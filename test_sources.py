"""test_sources.py - Jalon J1 : tester les sources et noter leurs limites.

Usage :
  python test_sources.py                                   # REST mempool.space
  python test_sources.py --ws                              # + WebSocket (30 s)
  python test_sources.py --elliptic-dir data/raw/elliptic  # inspecte les CSV Elliptic

Principe : on ne SUPPOSE aucun nom de champ. On affiche ce que la source
renvoie reellement, et on garde le resultat dans docs/resultats_J1_sources.json
pour le cahier des charges.
"""
import argparse
import asyncio
import json
import time
from pathlib import Path

import requests

BASE = "https://mempool.space/api"  # a verifier : https://mempool.space/docs/api/rest
HEADERS = {"User-Agent": "ensias-bigdata-projet/0.1 (projet pedagogique)"}


def test_rest():
    """Appelle 2 endpoints REST et releve statut, latence, limites eventuelles."""
    out = {}
    endpoints = [("hauteur_bloc", "/blocks/tip/height"),
                 ("mempool_recent", "/mempool/recent")]  # chemins a confirmer dans la doc
    for nom, chemin in endpoints:
        t0 = time.time()
        try:
            r = requests.get(BASE + chemin, headers=HEADERS, timeout=15)
            info = {
                "statut": r.status_code,
                "latence_s": round(time.time() - t0, 2),
                # En-tetes de quota s'ils existent (sinon dict vide = a noter)
                "en_tetes_quota": {k: v for k, v in r.headers.items()
                                   if k.lower().startswith(("x-ratelimit", "retry-after"))},
            }
            if r.ok:
                try:
                    corps = r.json()
                except ValueError:
                    corps = r.text
                if isinstance(corps, list):
                    info["nb_elements"] = len(corps)
                    if corps and isinstance(corps[0], dict):
                        # Les VRAIS champs renvoyes : a recopier dans le schema JSON Kafka
                        info["champs_premier_element"] = sorted(corps[0].keys())
                else:
                    info["apercu"] = str(corps)[:100]
            out[nom] = info
        except requests.RequestException as e:
            out[nom] = {"erreur": str(e)}  # ex. blocage reseau du Codespace : a noter
    return out


async def test_ws(duree=30):
    """Ouvre la WebSocket et compte les messages recus pendant `duree` secondes."""
    import websockets  # pip install websockets

    url = "wss://mempool.space/api/v1/ws"  # a confirmer dans la doc
    stats = {"messages": 0, "cles_recues": set()}
    try:
        async with websockets.connect(url) as ws:
            # Abonnement "blocks" : message a verifier dans la doc. Le flux de
            # NOUVELLES transactions demande peut-etre un autre abonnement : a
            # chercher dans la doc avant J3.
            await ws.send(json.dumps({"action": "want", "data": ["blocks"]}))
            fin = time.time() + duree
            while time.time() < fin:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=max(0.1, fin - time.time()))
                except asyncio.TimeoutError:
                    break
                stats["messages"] += 1
                try:
                    stats["cles_recues"].update(json.loads(msg).keys())
                except Exception:
                    pass
    except Exception as e:
        stats["erreur"] = str(e)
    stats["cles_recues"] = sorted(stats["cles_recues"])
    return stats


def inspecter_elliptic(dossier):
    """Pour chaque CSV : taille, nb de lignes, 2 premieres lignes brutes."""
    out = {}
    for f in sorted(Path(dossier).glob("*.csv")):
        with open(f, encoding="utf-8") as fh:
            lignes = [next(fh).rstrip() for _ in range(2)]
            nb = 2 + sum(1 for _ in fh)
        info = {"taille_Mo": round(f.stat().st_size / 1e6, 1),
                "nb_lignes_total": nb,
                "2_premieres_lignes": [l[:120] for l in lignes]}
        if "class" in f.name.lower():
            import pandas as pd
            df = pd.read_csv(f)
            # Repartition licite / illicite / inconnu : a verifier sur le fichier
            info["repartition_derniere_colonne"] = df.iloc[:, -1].value_counts().to_dict()
        out[f.name] = info
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ws", action="store_true", help="tester aussi la WebSocket")
    p.add_argument("--elliptic-dir", help="dossier contenant les CSV Elliptic")
    a = p.parse_args()

    resultats = {"mempool_rest": test_rest()}
    if a.ws:
        resultats["mempool_ws"] = asyncio.run(test_ws())
    if a.elliptic_dir:
        resultats["elliptic"] = inspecter_elliptic(a.elliptic_dir)

    Path("docs").mkdir(exist_ok=True)
    Path("docs/resultats_J1_sources.json").write_text(
        json.dumps(resultats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resultats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
