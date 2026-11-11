"""Source d'offres : API "Offres d'emploi v2" de France Travail.

⚠ Depuis fin 2026, cette API n'est plus proposée aux nouvelles applications sur
francetravail.io (accès sur demande via le formulaire de contact). Ce module reste
utilisable si l'accès est accordé : il suffit de remplir les clés dans .env.
"""
import re
import time
import unicodedata

import requests

from .. import config
from .commun import TIMEOUT, SourceErreur, extraire_email

NOM = "France Travail"
URL_TOKEN = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
URL_SEARCH = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"

# Paris, Lyon et Marseille : l'API attend un code d'arrondissement.
COMMUNES_ARRONDISSEMENTS = {"75056": "75101", "69123": "69381", "13055": "13201"}

_token = {"valeur": None, "expire": 0.0}


def est_configure() -> bool:
    return bool(config.FRANCE_TRAVAIL_CLIENT_ID and config.FRANCE_TRAVAIL_CLIENT_SECRET)


def _get_token() -> str:
    if _token["valeur"] and time.time() < _token["expire"] - 60:
        return _token["valeur"]
    if not est_configure():
        raise SourceErreur("Clés France Travail manquantes dans le fichier .env.")
    try:
        r = requests.post(
            URL_TOKEN,
            params={"realm": "/partenaire"},
            data={
                "grant_type": "client_credentials",
                "client_id": config.FRANCE_TRAVAIL_CLIENT_ID,
                "client_secret": config.FRANCE_TRAVAIL_CLIENT_SECRET,
                "scope": SCOPE,
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise SourceErreur(f"Impossible de contacter France Travail : {e}") from e
    if r.status_code != 200:
        raise SourceErreur(
            f"Connexion à France Travail refusée ({r.status_code}). L'application doit être "
            f"abonnée à l'API « Offres d'emploi v2 ». Détail : {r.text[:200]}"
        )
    data = r.json()
    _token["valeur"] = data["access_token"]
    _token["expire"] = time.time() + int(data.get("expires_in", 1499))
    return _token["valeur"]


def nettoyer_mot_cle(texte: str) -> str:
    """L'API n'accepte que lettres non accentuées, chiffres et espaces dans motsCles."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    mots = re.sub(r"[^A-Za-z0-9 ]", " ", sans_accents).split()
    return " ".join(m for m in mots if len(m) >= 2).lower()


def normaliser_offre(o: dict, mot_cle: str = "") -> dict:
    contact = o.get("contact") or {}
    lieu = o.get("lieuTravail") or {}
    origine = o.get("origineOffre") or {}
    return {
        "id": "FT-" + o["id"],
        "source": "france_travail",
        "intitule": o.get("intitule", "Sans titre"),
        "entreprise": (o.get("entreprise") or {}).get("nom") or contact.get("nom"),
        "lieu": lieu.get("libelle"),
        "type_contrat": o.get("typeContratLibelle") or o.get("typeContrat"),
        "duree_travail": o.get("dureeTravailLibelle"),
        "salaire": (o.get("salaire") or {}).get("libelle"),
        "date_creation": (o.get("dateCreation") or "")[:10],
        "description": o.get("description", ""),
        "email_contact": extraire_email(
            contact.get("courriel"), contact.get("coordonnees1"), contact.get("coordonnees2"),
            contact.get("coordonnees3"), o.get("description"),
        ),
        "url_postulation": contact.get("urlPostulation") or origine.get("urlOrigine"),
        "url_offre": f"https://candidat.francetravail.fr/offres/recherche/detail/{o['id']}",
        "competences": [c["libelle"] for c in o.get("competences", []) if c.get("libelle")]
        + [q["libelle"] for q in o.get("qualitesProfessionnelles", []) if q.get("libelle")],
        "mot_cle": mot_cle,
    }


def rechercher(mot_cle: str, departement: str | None = None, commune: str | None = None,
               distance: int | None = None, contrats: list[str] | None = None,
               publiee_depuis: int = 31) -> list[dict]:
    """Recherche les offres pour UN mot-clé. Renvoie au plus 150 offres normalisées."""
    mc = nettoyer_mot_cle(mot_cle)
    if not mc:
        return []
    params = {"motsCles": mc, "range": "0-149", "sort": 1, "publieeDepuis": publiee_depuis}
    if commune:
        params["commune"] = COMMUNES_ARRONDISSEMENTS.get(commune, commune)
        if distance is not None:
            params["distance"] = distance
    elif departement:
        params["departement"] = departement
    contrats = contrats or []
    types = [c for c in contrats if c in ("CDI", "CDD", "MIS", "SAI")]
    if types:
        params["typeContrat"] = ",".join(types)
    if "PARTIEL" in contrats:
        params["tempsPlein"] = "false"

    for _ in range(3):
        try:
            r = requests.get(
                URL_SEARCH, params=params, timeout=TIMEOUT,
                headers={"Authorization": f"Bearer {_get_token()}", "Accept": "application/json"},
            )
        except requests.RequestException as e:
            raise SourceErreur(f"Impossible de contacter France Travail : {e}") from e
        if r.status_code == 401:  # jeton expiré : on en redemande un
            _token["valeur"] = None
        elif r.status_code == 429:  # quota (4 appels/s) dépassé : attendre le délai demandé
            time.sleep(min(int(r.headers.get("Retry-After", "1") or 1), 10))
        else:
            break

    if r.status_code == 204:  # aucune offre
        return []
    if r.status_code not in (200, 206):
        raise SourceErreur(f"Erreur France Travail ({r.status_code}) : {r.text[:300]}")
    return [normaliser_offre(o, mot_cle) for o in r.json().get("resultats", [])]
