"""Logique de recherche d'offres, partagée entre l'interface et l'envoi automatique."""
import re
import uuid
from datetime import date

from . import db, france_travail
from .france_travail import FranceTravailErreur

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
        r["departement"] = lieu.upper().zfill(2)
        r["ville"] = f"Département {r['departement']}"
    elif lieu:
        commune = france_travail.chercher_commune(lieu)
        if not commune:
            raise ValueError(f"Ville introuvable : « {lieu} ».")
        r["commune"] = commune["code"]
        r["ville"] = commune["nom"]
        r["distance"] = int(distance) if str(distance or "").isdigit() else 10
    return r


def lancer_recherche(r: dict, publiee_depuis: int = 31) -> tuple[int, int, list[str]]:
    """Lance une recherche et enregistre les offres. Renvoie (trouvées, nouvelles, erreurs)."""
    offres, erreurs = france_travail.rechercher_plusieurs(
        r["mots_cles"].splitlines(),
        departement=r.get("departement"),
        commune=r.get("commune"),
        distance=r.get("distance"),
        contrats=(r.get("contrats") or "").split(",") if r.get("contrats") else None,
        publiee_depuis=publiee_depuis,
    )
    nouvelles = db.enregistrer_offres(offres)
    return len(offres), nouvelles, erreurs


def ajouter_offre_manuelle(form) -> str:
    """Ajoute une offre trouvée ailleurs (Indeed, site d'entreprise, affiche...)."""
    intitule = form.get("intitule", "").strip()
    if not intitule:
        raise ValueError("L'intitulé du poste est obligatoire.")
    description = form.get("description", "").strip()
    email = form.get("email_contact", "").strip() or france_travail.extraire_email(description)
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


__all__ = ["preparer_recherche", "lancer_recherche", "ajouter_offre_manuelle", "FranceTravailErreur"]
