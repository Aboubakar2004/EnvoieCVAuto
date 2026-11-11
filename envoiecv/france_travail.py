"""Client de l'API "Offres d'emploi v2" de France Travail.

Doc : https://francetravail.io/data/api/offres-emploi
Il faut un compte (gratuit) sur francetravail.io, créer une application et
l'abonner à l'API "Offres d'emploi v2" pour obtenir client_id / client_secret.
"""
import re
import time
import unicodedata

import requests

from . import config

URL_TOKEN = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
URL_SEARCH = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
URL_GEO = "https://geo.api.gouv.fr/communes"
SCOPE = "api_offresdemploiv2 o2dsoffre"
TIMEOUT = 20

# Paris, Lyon et Marseille : l'API attend un code d'arrondissement.
COMMUNES_ARRONDISSEMENTS = {"75056": "75101", "69123": "69381", "13055": "13201"}

# Mots-clés proposés dans l'interface, par catégorie de métier.
CATEGORIES = {
    "Nettoyage / propreté": [
        "agent entretien", "agent proprete", "agent de service", "agent de menage",
        "laveur de vitres",
    ],
    "Hôtellerie": [
        "femme de chambre", "valet de chambre", "employe etage", "receptionniste hotel",
        "gouvernante hotel",
    ],
    "Restauration (dont cantines scolaires)": [
        "agent de restauration", "restauration collective", "restauration scolaire",
        "cantine", "plongeur", "employe polyvalent restauration", "aide cuisine",
        "commis de cuisine",
    ],
}

TYPES_CONTRAT = {"CDI": "CDI", "CDD": "CDD", "MIS": "Intérim", "SAI": "Saisonnier"}

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class FranceTravailErreur(Exception):
    pass


_token = {"valeur": None, "expire": 0.0}


def est_configure() -> bool:
    return bool(config.FRANCE_TRAVAIL_CLIENT_ID and config.FRANCE_TRAVAIL_CLIENT_SECRET)


def _get_token() -> str:
    if _token["valeur"] and time.time() < _token["expire"] - 60:
        return _token["valeur"]
    if not est_configure():
        raise FranceTravailErreur(
            "Clés France Travail manquantes : remplis FRANCE_TRAVAIL_CLIENT_ID et "
            "FRANCE_TRAVAIL_CLIENT_SECRET dans le fichier .env."
        )
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
        raise FranceTravailErreur(f"Impossible de contacter France Travail : {e}") from e
    if r.status_code != 200:
        raise FranceTravailErreur(
            f"Connexion à France Travail refusée ({r.status_code}). Vérifie tes clés et que "
            f"ton application est bien abonnée à l'API « Offres d'emploi v2 ». Détail : {r.text[:200]}"
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


def chercher_commune(nom: str) -> dict | None:
    """Trouve le code INSEE d'une ville (API publique geo.api.gouv.fr, sans clé)."""
    nom = nom.strip()
    if not nom:
        return None
    params = {"fields": "nom,code,codesPostaux,codeDepartement", "limit": 1, "boost": "population"}
    if nom.isdigit() and len(nom) == 5:
        params["codePostal"] = nom
    else:
        params["nom"] = nom
    try:
        r = requests.get(URL_GEO, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        res = r.json()
    except requests.RequestException as e:
        raise FranceTravailErreur(f"Recherche de la ville impossible : {e}") from e
    if not res:
        return None
    c = res[0]
    return {
        "nom": c["nom"],
        "code": COMMUNES_ARRONDISSEMENTS.get(c["code"], c["code"]),
        "departement": c.get("codeDepartement"),
    }


def extraire_email(*textes: str | None) -> str | None:
    for t in textes:
        if t:
            m = RE_EMAIL.search(t)
            if m:
                return m.group(0).rstrip(".").lower()
    return None


def normaliser_offre(o: dict, mot_cle: str = "") -> dict:
    contact = o.get("contact") or {}
    lieu = o.get("lieuTravail") or {}
    origine = o.get("origineOffre") or {}
    url_postulation = contact.get("urlPostulation") or origine.get("urlOrigine")
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
        "url_postulation": url_postulation,
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
        params["commune"] = commune
        if distance is not None:
            params["distance"] = distance
    elif departement:
        params["departement"] = departement
    if contrats:
        params["typeContrat"] = ",".join(contrats)

    for essai in range(3):
        try:
            r = requests.get(
                URL_SEARCH, params=params, timeout=TIMEOUT,
                headers={"Authorization": f"Bearer {_get_token()}", "Accept": "application/json"},
            )
        except requests.RequestException as e:
            raise FranceTravailErreur(f"Impossible de contacter France Travail : {e}") from e
        if r.status_code == 401:  # jeton expiré : on en redemande un
            _token["valeur"] = None
        elif r.status_code == 429:  # quota dépassé : attendre le délai demandé
            time.sleep(min(int(r.headers.get("Retry-After", "1") or 1), 10))
        else:
            break

    if r.status_code == 204:  # aucune offre
        return []
    if r.status_code not in (200, 206):
        raise FranceTravailErreur(f"Erreur France Travail ({r.status_code}) : {r.text[:300]}")
    return [normaliser_offre(o, mot_cle) for o in r.json().get("resultats", [])]


def rechercher_plusieurs(mots_cles: list[str], **kwargs) -> tuple[list[dict], list[str]]:
    """Lance une recherche par mot-clé et fusionne les résultats (sans doublons).

    Renvoie (offres, erreurs).
    """
    offres: dict[str, dict] = {}
    erreurs = []
    for mc in mots_cles:
        try:
            for o in rechercher(mc, **kwargs):
                offres.setdefault(o["id"], o)
        except FranceTravailErreur as e:
            erreurs.append(f"« {mc} » : {e}")
            if "Clés France Travail" in str(e) or "refusée" in str(e):
                break  # inutile de réessayer avec les autres mots-clés
        time.sleep(0.3)  # quota France Travail : 4 appels par seconde maximum
    return list(offres.values()), erreurs
