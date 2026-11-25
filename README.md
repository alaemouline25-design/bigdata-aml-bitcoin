# Surveillance anti-blanchiment sur la blockchain Bitcoin

Projet fil rouge · Big Data & Applications · ENSIAS (filière IDF) · 2026-2027

## Question de recherche

Peut-on détecter les transactions illicites à partir de la structure du graphe des transactions ? Un modèle sur graphe fait-il mieux qu'un modèle tabulaire ?

## Architecture

    Direct       : mempool.space -> producteur Python -> Kafka -> Spark Structured Streaming -> alertes MongoDB
    Historique   : jeu Elliptic (Kaggle) -> Delta Lake (Bronze / Silver / Gold) -> entraînement des modèles
    Secours      : simulateur de rejeu d'Elliptic -> Kafka (débit réglable)
    Orchestration: Airflow (collecte et contrôles qualité)
    Interface    : application Streamlit (état de la chaîne, alertes, résultats des modèles)

## Équipe

| Membre | Mission |
|---|---|
| (à compléter) | (à compléter) |

## Structure du dépôt

    docs/         cahier des charges, schémas JSON, usage_ia.md
    data/raw/     données brutes (Elliptic), non versionnées
    producer/     producteur et simulateur de rejeu
    streaming/    jobs Spark Structured Streaming
    lakehouse/    couches Bronze / Silver / Gold
    ml/           forêt aléatoire, GCN
    airflow/      DAG
    app/          interface Streamlit

## Installation (Windows, PowerShell)

    git clone https://github.com/alaemouline25-design/bigdata-aml-bitcoin.git
    cd bigdata-aml-bitcoin
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt

Créer un fichier `.env` à partir du modèle `.env.example` et y renseigner `MONGODB_URI`. Ce fichier n'est jamais versionné.

Les données Elliptic sont à télécharger sur Kaggle et à placer dans `data/raw/elliptic`.

## Règles méthodologiques

- Découpage train/test temporel, jamais aléatoire.
- Transactions « inconnues » exclues de l'entraînement et de l'évaluation.
- Évaluation par précision, rappel et F1 de la classe illicite (pas l'accuracy).
- Le flux direct n'a pas d'étiquettes : le modèle n'y est pas validé.

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