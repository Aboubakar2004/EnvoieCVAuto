"""Correspondance entre le CV (profil) et les offres.

- mots_cles_depuis_profil() : transforme les "postes recherchés" du CV en mots-clés de recherche
- score_offre() : note de 0 à 100 indiquant si l'offre correspond au CV
"""
import re
import unicodedata

SEUIL_PERTINENT = 40

# Poste recherché (racine, sans accent) -> mots-clés envoyés aux sites d'offres
SYNONYMES = {
    "restauration": ["agent de restauration", "restauration scolaire", "restauration collective",
                     "cantine", "employé polyvalent restauration"],
    "cantine": ["cantine", "restauration scolaire"],
    "hospitalier": ["agent de service hospitalier", "ASH"],
    "ash": ["agent de service hospitalier", "ASH"],
    "entretien": ["agent entretien", "agent de propreté", "agent de nettoyage"],
    "nettoyage": ["agent de nettoyage", "agent entretien"],
    "chambre": ["femme de chambre", "valet de chambre", "employé d'étage"],
    "plong": ["plongeur"],
    "menage": ["femme de ménage", "agent de ménage"],
}

# Mots dans le TITRE d'une offre qui indiquent un poste correspondant au CV
RACINES_METIER = [
    "restaur", "cantine", "plong", "entretien", "nettoy", "propret", "menag", "chambre",
    "etage", "hospitalier", "agent de service", "agent d entretien", "lingere", "linge",
    "aide cuisin", "aide de cuisine", "employe polyvalent", "agent polyvalent", "self",
    "collectivite", "housekeeping", "room attendant",
]
MOTS_SEULS_METIER = {"ash", "asem"}

# Mots dans le TITRE qui indiquent un poste d'encadrement ou hors profil
RACINES_EXCLUES = [
    "responsable", "directeur", "directrice", "manager", "chef", "superviseur", "superviseuse",
    "adjoint", "stage", "stagiaire", "alternance", "alternant", "apprenti", "ingenieur",
    "commercial", "comptable", "gouvernant", "gerant", "cadre", "coordinat", "chauffeur",
    "infirmier", "aide soignant", "cuisinier", "second de cuisine", "technicien", "coordon",
    " resp ", "livreur", "livraison", "vente", "vendeur", "vendeuse",
    # "agent d'entretien" au sens maintenance / extérieur
    "voirie", "espaces verts", "espace vert", "jardin", "parcs", "batiment", "maintenance",
    "electri", "plomb", "technique", "vehicule", "mecani",
]

MOTS_VIDES = {
    "les", "des", "une", "aux", "avec", "pour", "dans", "sur", "par", "est", "son", "ses",
    "leur", "vos", "nos", "qui", "que", "et", "de", "du", "la", "le", "en", "un", "au",
    "plusieurs", "differents", "clients", "aujourd", "hui", "missions", "semaines", "quelques",
}


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", texte).strip() + " "


def mots_cles_depuis_profil(profil: dict) -> list[str]:
    """Mots-clés de recherche déduits des postes recherchés du CV (sans doublons)."""
    mots: list[str] = []
    for poste in profil.get("postes_recherches", []):
        p = normaliser(poste)
        trouves = [syn for racine, syns in SYNONYMES.items()
                   if (f" {racine} " in p if racine == "ash" else racine in p) for syn in syns]
        mots.extend(trouves or [poste])
    return list(dict.fromkeys(mots))


def _vocabulaire_cv(profil: dict) -> set[str]:
    """Mots significatifs du CV (compétences, expériences) pour comparer aux descriptions."""
    textes = list(profil.get("competences", [])) + list(profil.get("postes_recherches", []))
    for e in profil.get("experiences", []):
        textes.append(e.get("titre", ""))
        textes.extend(e.get("details", []))
    mots = normaliser(" ".join(textes)).split()
    return {m for m in mots if len(m) >= 4 and m not in MOTS_VIDES}


def score_offre(offre: dict, profil: dict) -> int:
    titre = normaliser(offre.get("intitule", ""))
    description = normaliser(offre.get("description", ""))

    if any(r in titre for r in RACINES_EXCLUES):
        return 0

    score = 0
    if any(r in titre for r in RACINES_METIER) or MOTS_SEULS_METIER & set(titre.split()):
        score += 60
    elif any(r in description for r in RACINES_METIER):
        score += 25

    communs = _vocabulaire_cv(profil) & set((titre + description).split())
    score += min(len(communs) * 4, 40)
    return min(score, 100)
