"""Source d'offres : API Adzuna (agrégateur de sites d'emploi).

Clé gratuite sur https://developer.adzuna.com (usage "recherche d'emploi personnelle").
Limites du compte gratuit : environ 25 appels/minute et 250 appels/jour.
Les données proviennent d'Adzuna : on l'indique dans l'interface (obligation des conditions).
"""
import time

import requests

from .. import config
from .commun import TIMEOUT, SourceErreur, SourceIndisponible, extraire_email

NOM = "Adzuna"
URL_SEARCH = "https://api.adzuna.com/v1/api/jobs/fr/search/1"

CONTRATS_ADZUNA = {"CDI": "permanent", "CDD": "contract", "MIS": "contract", "SAI": "contract"}


def est_configure() -> bool:
    return bool(config.ADZUNA_APP_ID and config.ADZUNA_APP_KEY)


def _params_contrats(contrats: list[str]) -> dict:
    params = {}
    types = {CONTRATS_ADZUNA[c] for c in contrats if c in CONTRATS_ADZUNA}
    if len(types) == 1:  # si CDI + CDD cochés, pas de filtre
        params[types.pop()] = 1
    if "PARTIEL" in contrats:
        params["part_time"] = 1
    return params


def normaliser_offre(o: dict, mot_cle: str = "") -> dict:
    salaire = None
    if o.get("salary_min") and not str(o.get("salary_is_predicted")) == "1":
        smin, smax = int(o["salary_min"]), int(o.get("salary_max") or o["salary_min"])
        salaire = f"{smin} €" if smin == smax else f"{smin} - {smax} €"
    contrat = {"permanent": "CDI", "contract": "CDD / intérim"}.get(o.get("contract_type"))
    temps = {"full_time": "Temps plein", "part_time": "Temps partiel"}.get(o.get("contract_time"))
    return {
        "id": f"AZ-{o['id']}",
        "source": "adzuna",
        "intitule": o.get("title") or "Sans titre",
        "entreprise": (o.get("company") or {}).get("display_name"),
        "lieu": (o.get("location") or {}).get("display_name"),
        "type_contrat": contrat,
        "duree_travail": temps,
        "salaire": salaire,
        "date_creation": (o.get("created") or "")[:10],
        "description": o.get("description", ""),
        "email_contact": extraire_email(o.get("description")),
        "url_postulation": o.get("redirect_url"),
        "url_offre": o.get("redirect_url"),
        "competences": [],
        "mot_cle": mot_cle,
    }


def rechercher(mot_cle: str, lieu: str | None = None, distance: int | None = None,
               contrats: list[str] | None = None, publiee_depuis: int = 31) -> list[dict]:
    """Recherche les offres pour UN mot-clé (50 plus récentes)."""
    if not est_configure():
        raise SourceErreur(
            "Clés Adzuna manquantes : remplis ADZUNA_APP_ID et ADZUNA_APP_KEY dans le fichier .env."
        )
    mot_cle = mot_cle.replace("'", " ").strip()
    if not mot_cle:
        return []
    params = {
        "app_id": config.ADZUNA_APP_ID,
        "app_key": config.ADZUNA_APP_KEY,
        "what": mot_cle,
        "results_per_page": 50,
        "sort_by": "date",
        "max_days_old": publiee_depuis,
        "content-type": "application/json",
        **_params_contrats(contrats or []),
    }
    if lieu:
        params["where"] = lieu
        if distance:
            params["distance"] = distance

    r = None
    for attente in (2, 5, 0):  # 3 tentatives en cas de panne passagère
        try:
            r = requests.get(URL_SEARCH, params=params, timeout=TIMEOUT)
        except requests.RequestException:
            r = None
        if r is not None and r.status_code == 429:  # trop d'appels : on patiente
            time.sleep(min(int(r.headers.get("Retry-After", "5") or 5), 20))
        elif r is None or r.status_code >= 500:  # serveur Adzuna en panne
            time.sleep(attente)
        else:
            break

    if r is None or r.status_code >= 500:
        code = f" ({r.status_code})" if r is not None else ""
        raise SourceIndisponible(f"Adzuna est momentanément indisponible{code}.")
    if r.status_code in (401, 403):
        raise SourceErreur(f"Clés Adzuna refusées ({r.status_code}). Vérifie ADZUNA_APP_ID et ADZUNA_APP_KEY.")
    if r.status_code == 429:
        raise SourceErreur("Limite d'appels Adzuna atteinte (250 par jour). Réessaie plus tard.")
    if r.status_code != 200:
        raise SourceErreur(f"Erreur Adzuna ({r.status_code}).")
    return [normaliser_offre(o, mot_cle) for o in r.json().get("results", [])]
