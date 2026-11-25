# Surveillance anti-blanchiment sur la blockchain Bitcoin

Projet fil rouge · Big Data & Applications · ENSIAS (filière IDF) · 2026-2027

## Question de recherche

Peut-on détecter les transactions illicites à partir de la structure du graphe des transactions ? Un modèle sur graphe fait-il mieux qu'un modèle tabulaire ?

## Architecture

    Direct        : mempool.space -> producteur Python -> Kafka -> Spark Structured Streaming -> alertes MongoDB
    Historique    : jeu Elliptic (Kaggle) -> Delta Lake (Bronze / Silver / Gold) -> entraînement des modèles
    Secours       : simulateur de rejeu d'Elliptic -> Kafka (débit réglable)
    Orchestration : Airflow (collecte et contrôles qualité)
    Interface     : application Streamlit (état de la chaîne, alertes, résultats des modèles)

## Équipe

| Membre | Mission |
|---|---|
| (à compléter) | (à compléter) |

## Structure du dépôt

    docs/                  cahier des charges, résultats des tests, schémas JSON, usage_ia.md
    data/raw/              données brutes (Elliptic), non versionnées
    producer/              producteur et simulateur de rejeu
    streaming/             jobs Spark Structured Streaming
    lakehouse/             couches Bronze / Silver / Gold
    ml/                    forêt aléatoire, GCN
    airflow/               DAG
    app/                   interface Streamlit
    test_sources.py        test des sources : mempool.space et fichiers Elliptic (J1)
    test_sources_tx.py     test du flux mempool.space : détail, débit, rafale (J1)

## Installation (Windows, PowerShell)

    git clone https://github.com/alaemouline25-design/bigdata-aml-bitcoin.git
    cd bigdata-aml-bitcoin
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt

Créer un fichier `.env` à partir du modèle `.env.example` et y renseigner `MONGODB_URI`. Ce fichier n'est jamais versionné.

Télécharger le jeu Elliptic sur Kaggle (`ellipticco/elliptic-data-set`) et placer les 3 fichiers CSV dans `data/raw/elliptic`.

## Tests des sources (J1)

    python test_sources.py --ws --elliptic-dir data\raw\elliptic
    python test_sources_tx.py

Les résultats sont enregistrés dans `docs/resultats_J1_sources.json` et `docs/resultats_J1_tx.json`.

## Résultats des tests de sources (J1)

### mempool.space (flux direct)

| Mesure | Résultat |
|---|---|
| Accès REST | statut 200, environ 1 s par appel ; **premier essai en timeout** (REST et WebSocket) : accès intermittent |
| `/mempool/recent` | 10 transactions par appel ; champs `fee`, `txid`, `value`, `vsize` (pas d'entrées ni de sorties) |
| Débit observé | 109 `txid` distincts en 60 s (11 appels, 0 erreur) : **échantillon**, le débit réel est probablement plus élevé |
| Détail `/tx/<txid>` | statut 200 ; champs `fee`, `locktime`, `sigops`, `size`, `status`, `txid`, `version`, `vin`, `vout`, `weight` ; listes `vin` et `vout` présentes |
| Rafale de 20 appels de détail | 20 × statut 200, latence de 0,77 à 1,06 s, aucun en-tête de quota |
| WebSocket | 1 message reçu (clé `blocks`) ; l'abonnement aux nouvelles transactions reste à identifier dans la doc |

L'absence d'en-tête de quota ne prouve pas l'absence de limite : les conditions d'utilisation restent à lire.

### Elliptic (historique)

| Mesure | Résultat |
|---|---|
| Transactions | 203 769 |
| Arêtes | 234 355 |
| `unknown` | 157 205 (environ 77,1 %) |
| Classe `2` | 42 019 (environ 20,6 %) |
| Classe `1` | 4 545 (environ 2,2 %) |
| Transactions étiquetées | 46 564, dont environ 9,8 % de classe `1` |
| Fichier des attributs | 689,7 Mo, sans en-tête |

Correspondance des classes à confirmer (`1` = illicite et `2` = licite d'après la description du jeu). Nombre de colonnes et pas de temps à vérifier.

## Limites et points ouverts

- Les attributs d'Elliptic sont anonymisés : aucun lien documenté avec les champs calculables sur le flux direct. Tout attribut recalculé en direct est un **proxy**.
- Le flux direct n'a **pas d'étiquettes** : le modèle n'y est pas validé.
- L'interrogation périodique de `/mempool/recent` ne capture qu'un échantillon des transactions.
- Chaque détail de transaction demande un appel d'environ 1 s : l'enrichissement se limite à un sous-ensemble.
- Accès à mempool.space intermittent : le rejeu d'Elliptic reste la source de secours et de démonstration.

## Règles méthodologiques

- Découpage train/test temporel, jamais aléatoire.
- Transactions « inconnues » exclues de l'entraînement et de l'évaluation.
- Évaluation par précision, rappel et F1 de la classe illicite (pas l'accuracy).
- Comparaison minimale : forêt aléatoire sur attributs locaux, forêt aléatoire locaux + agrégés, puis GCN.

## Jalons

| Jalon | Contenu | Statut |
|---|---|---|
| J0 | Équipe et sujet | fait |
| J1 | Cahier des charges, sources testées | en cours |
| J2 | Couches Bronze et Silver | à faire |
| J3 | Producteur et simulateur de rejeu | à faire |
| J4 | Alertes temps réel dans MongoDB | à faire |
| J5 | DAG Airflow | à faire |
| J6 | Pipeline intégré et démonstration | à faire |

## Conformité et usage de l'IA

Respect des conditions d'utilisation des sources et de la loi 09-08 (identifiants pseudonymisés). L'usage de l'IA générative est consigné dans `docs/usage_ia.md` et déclaré dans le rapport.

## Référence

Weber, M. et al. (2019). Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics. KDD '19 Workshop on Anomaly Detection in Finance. https://arxiv.org/abs/1908.02591