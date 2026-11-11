"""Recherche automatique des offres à partir du CV.

Tant que l'application tourne, une recherche est lancée au démarrage puis toutes les
INTERVALLE_HEURES heures, avec les postes recherchés, la ville et le rayon du profil.
Si la recherche échoue (site en panne), elle est retentée après DELAI_REESSAI_MINUTES.
"""
import logging
import threading
import time
from datetime import datetime, timedelta

from . import db
from .pertinence import mots_cles_depuis_profil
from .profil import charger_profil
from .recherche import lancer_recherche, preparer_recherche
from .sources import SourceErreur

INTERVALLE_HEURES = 3
DELAI_REESSAI_MINUTES = 15
PUBLIEE_DEPUIS_JOURS = 7  # on ne récupère que les offres récentes

log = logging.getLogger(__name__)
_verrou = threading.Lock()
_demarre = False


def en_cours() -> bool:
    return _verrou.locked()


def recherche_automatique() -> dict | None:
    """Lance la recherche basée sur le CV. Renvoie un résumé (aussi stocké en base),
    ou None si une recherche est déjà en cours."""
    if not _verrou.acquire(blocking=False):
        return None
    try:
        profil = charger_profil()
        mots = mots_cles_depuis_profil(profil)
        resultat = {"date": datetime.now().isoformat(timespec="seconds"),
                    "trouvees": 0, "nouvelles": 0, "erreurs": [], "echec": False}
        if not mots:
            resultat["erreurs"].append("Ajoute des « postes recherchés » dans Mon CV pour lancer la recherche.")
        else:
            try:
                r = preparer_recherche(mots, profil.get("ville", ""), profil.get("rayon_km", 20),
                                       profil.get("contrats_souhaites", []))
                t, n, err = lancer_recherche(r, PUBLIEE_DEPUIS_JOURS)
                resultat.update(trouvees=t, nouvelles=n, erreurs=err)
            except (ValueError, SourceErreur) as e:
                resultat["erreurs"].append(str(e))
            # rien trouvé à cause d'une erreur : on réessaiera bientôt
            resultat["echec"] = bool(resultat["erreurs"]) and resultat["trouvees"] == 0
        db.set_meta("derniere_recherche_auto", resultat)
        log.info("Recherche automatique : %s", resultat)
        return resultat
    finally:
        _verrou.release()


def lancer_en_arriere_plan() -> bool:
    """Démarre une recherche sans bloquer la page. False si une recherche tourne déjà."""
    if en_cours():
        return False
    threading.Thread(target=recherche_automatique, name="recherche-manuelle", daemon=True).start()
    return True


def prochaine_recherche() -> datetime | None:
    derniere = db.get_meta("derniere_recherche_auto")
    if not derniere:
        return None
    delai = (timedelta(minutes=DELAI_REESSAI_MINUTES) if derniere.get("echec")
             else timedelta(hours=INTERVALLE_HEURES))
    return datetime.fromisoformat(derniere["date"]) + delai


def _boucle():
    while True:
        try:
            prochaine = prochaine_recherche()
            if prochaine is None or datetime.now() >= prochaine:
                recherche_automatique()
        except Exception:  # le planificateur ne doit jamais s'arrêter
            log.exception("Erreur dans la recherche automatique")
        time.sleep(60)  # vérifie chaque minute


def demarrer_planificateur() -> None:
    global _demarre
    if _demarre:
        return
    _demarre = True
    threading.Thread(target=_boucle, name="recherche-auto", daemon=True).start()
