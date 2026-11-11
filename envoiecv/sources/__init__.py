"""Sources d'offres d'emploi.

Chaque source expose : NOM, est_configure() et rechercher(mot_cle, ...).
Seules les sources configurées (clés présentes dans .env) sont interrogées.
"""
from . import adzuna, france_travail
from .commun import CATEGORIES, TYPES_CONTRAT, SourceErreur

SOURCES = [adzuna, france_travail]


def sources_actives() -> list:
    return [s for s in SOURCES if s.est_configure()]


__all__ = ["CATEGORIES", "TYPES_CONTRAT", "SourceErreur", "SOURCES", "sources_actives"]
