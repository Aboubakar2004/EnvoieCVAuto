"""Éléments partagés par toutes les sources d'offres."""
import re

import requests

TIMEOUT = 20
URL_GEO = "https://geo.api.gouv.fr"

# Mots-clés proposés dans l'interface, par catégorie de métier.
CATEGORIES = {
    "Nettoyage / propreté": [
        "agent entretien", "agent de propreté", "agent de service", "agent de ménage",
        "laveur de vitres",
    ],
    "Hôtellerie": [
        "femme de chambre", "valet de chambre", "employé d'étage", "réceptionniste hôtel",
        "gouvernante hôtel",
    ],
    "Restauration (dont cantines scolaires)": [
        "agent de restauration", "restauration collective", "restauration scolaire",
        "cantine", "plongeur", "employé polyvalent restauration", "aide cuisine",
        "commis de cuisine",
    ],
}

# Codes de contrat communs à toutes les sources (chaque source les traduit).
TYPES_CONTRAT = {
    "CDI": "CDI",
    "CDD": "CDD",
    "MIS": "Intérim",
    "SAI": "Saisonnier",
    "PARTIEL": "Temps partiel",
}

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class SourceErreur(Exception):
    """Erreur d'une source d'offres (message lisible pour l'utilisateur)."""


def extraire_email(*textes: str | None) -> str | None:
    for t in textes:
        if t:
            m = RE_EMAIL.search(t)
            if m:
                return m.group(0).rstrip(".").lower()
    return None


def _geo(chemin: str, params: dict | None = None):
    try:
        r = requests.get(URL_GEO + chemin, params=params, timeout=TIMEOUT)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise SourceErreur(f"Recherche du lieu impossible : {e}") from e


def chercher_commune(nom: str) -> dict | None:
    """Trouve une ville par nom ou code postal (API publique geo.api.gouv.fr, sans clé)."""
    nom = nom.strip()
    if not nom:
        return None
    params = {"fields": "nom,code,codeDepartement", "limit": 1, "boost": "population"}
    if nom.isdigit() and len(nom) == 5:
        params["codePostal"] = nom
    else:
        params["nom"] = nom
    res = _geo("/communes", params)
    if not res:
        return None
    return {"nom": res[0]["nom"], "code": res[0]["code"], "departement": res[0].get("codeDepartement")}


def chercher_departement(code: str) -> dict | None:
    res = _geo(f"/departements/{code}")
    return {"nom": res["nom"], "code": res["code"]} if res else None
