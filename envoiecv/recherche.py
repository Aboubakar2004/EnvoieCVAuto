"""Logique de recherche d'offres, partagée entre l'interface et l'envoi automatique."""
import re
import time
import uuid
from datetime import date

from . import db
from .sources import SourceErreur, adzuna, france_travail, sources_actives
from .sources.commun import chercher_commune, chercher_departement, extraire_email

RE_DEPARTEMENT = re.compile(r"^(\d{2,3}|2[AaBb])$")


def preparer_recherche(mots_cles: list[str], lieu: str, distance: str | int | None,
                       contrats: list[str]) -> dict:
    """Transforme la saisie du formulaire en recherche prête à lancer/enregistrer.

    `lieu` peut être un département ("69"), une ville ("Lyon") ou un code postal ("69003").
    """
    mots = [m.strip() for m in mots_cles if m.strip()]
    if not mots:
        raise ValueError("Choisis au moins un métier ou un mot-clé.")

    r = {"mots_cles": "\n".join(dict.fromkeys(mots)), "departement": None, "commune": None,
         "ville": None, "distance": None, "contrats": ",".join(contrats) or None}

    lieu = (lieu or "").strip()
    if RE_DEPARTEMENT.match(lieu):
        code = lieu.upper().zfill(2)
        dep = chercher_departement(code)
        if not dep:
            raise ValueError(f"Département inconnu : « {lieu} ».")
        r["departement"], r["ville"] = dep["code"], dep["nom"]
    elif lieu:
        commune = chercher_commune(lieu)
        if not commune:
            raise ValueError(f"Ville introuvable : « {lieu} ».")
        r["commune"], r["ville"] = commune["code"], commune["nom"]
        r["distance"] = int(distance) if str(distance or "").isdigit() else 10
    return r


def _chercher(source, mot_cle: str, r: dict, contrats: list[str], publiee_depuis: int) -> list[dict]:
    if source is adzuna:
        return adzuna.rechercher(mot_cle, lieu=r.get("ville"), distance=r.get("distance"),
                                 contrats=contrats, publiee_depuis=publiee_depuis)
    if source is france_travail:
        return france_travail.rechercher(mot_cle, departement=r.get("departement"),
                                         commune=r.get("commune"), distance=r.get("distance"),
                                         contrats=contrats, publiee_depuis=publiee_depuis)
    raise ValueError(source)


def lancer_recherche(r: dict, publiee_depuis: int = 31) -> tuple[int, int, list[str]]:
    """Lance une recherche sur toutes les sources configurées et enregistre les offres.

    Renvoie (trouvées, nouvelles, erreurs).
    """
    sources = sources_actives()
    if not sources:
        return 0, 0, ["Aucune source d'offres configurée : ajoute tes clés Adzuna dans le fichier .env."]

    contrats = (r.get("contrats") or "").split(",") if r.get("contrats") else []
    offres: dict[str, dict] = {}
    erreurs = []
    for source in sources:
        for mc in r["mots_cles"].splitlines():
            try:
                for o in _chercher(source, mc, r, contrats, publiee_depuis):
                    offres.setdefault(o["id"], o)
            except SourceErreur as e:
                erreurs.append(f"{source.NOM} : {e}")
                break  # erreur de clé ou de quota : inutile d'insister sur cette source
            time.sleep(0.4)  # respecte les quotas d'appels des API
    nouvelles = db.enregistrer_offres(list(offres.values()))
    return len(offres), nouvelles, erreurs


def ajouter_offre_manuelle(form) -> str:
    """Ajoute une offre trouvée ailleurs (Indeed, site d'entreprise, affiche...)."""
    intitule = form.get("intitule", "").strip()
    if not intitule:
        raise ValueError("L'intitulé du poste est obligatoire.")
    description = form.get("description", "").strip()
    email = form.get("email_contact", "").strip() or extraire_email(description)
    url = form.get("url_offre", "").strip() or None
    offre = {
        "id": "MAN-" + uuid.uuid4().hex[:10],
        "source": "manuel",
        "intitule": intitule,
        "entreprise": form.get("entreprise", "").strip() or None,
        "lieu": form.get("lieu", "").strip() or None,
        "type_contrat": form.get("type_contrat", "").strip() or None,
        "date_creation": date.today().isoformat(),
        "description": description,
        "email_contact": email,
        "url_offre": url,
        "url_postulation": url,
        "competences": [],
        "mot_cle": "ajout manuel",
    }
    db.enregistrer_offres([offre])
    return offre["id"]
