"""Génération automatique de la lettre de motivation (et d'un message court) pour une offre.

Sans IA : la lettre est assemblée à partir du profil (expériences, qualités, disponibilités)
et de l'offre (poste, entreprise, type de métier). Elle n'invente aucune expérience.
"""
import re
from datetime import date

from .pertinence import normaliser

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]

# Type de métier -> mots repérés dans l'offre ou dans une expérience
CATEGORIES = {  # l'ordre compte : la première catégorie trouvée l'emporte
    "plonge": ["plong"],
    "hospitalier": ["hospital", "ash", "ehpad", "clinique", "hopital", "soins"],
    "hotellerie": ["chambre", "hotel", "etage", "housekeeping", "gouvernante", "lingere"],
    "restauration": ["restaur", "cantine", "self", "repas", "scolaire", "cuisine", "collectivite"],
    "entretien": ["entretien", "nettoy", "propret", "menag", "desinfect", "locaux"],
}

DOMAINES = {
    "hospitalier": "le milieu hospitalier",
    "hotellerie": "l'hôtellerie",
    "restauration": "la restauration collective",
    "plonge": "la restauration",
    "entretien": "l'entretien de locaux",
}

MOTIVATION = {
    "restauration": (
        "Le travail en restauration collective me plaît particulièrement : préparer et servir "
        "les repas dans le respect des règles d'hygiène, en équipe et dans les temps."
    ),
    "plonge": (
        "Je suis à l'aise avec le rythme soutenu d'une cuisine et j'attache une grande importance "
        "à la propreté de la vaisselle et du matériel."
    ),
    "hotellerie": (
        "Je connais les exigences de l'hôtellerie : des chambres impeccables, un travail rapide "
        "et soigné, et la discrétion vis-à-vis des clients."
    ),
    "hospitalier": (
        "Je sais que le milieu hospitalier demande de la rigueur et un respect strict des règles "
        "d'hygiène, et je suis {motivee} à mettre mon sérieux au service des patients et des équipes."
    ),
    "entretien": (
        "J'ai à cœur de rendre des locaux propres et accueillants, en respectant les protocoles "
        "d'hygiène et de désinfection."
    ),
    None: "Je suis {motivee} à mettre mon expérience et mon sérieux au service de votre structure.",
}


# ----------------------------------------------------------------- outils de texte

def _g(profil: dict, feminin: str, masculin: str) -> str:
    genre = profil.get("genre")
    if genre == "f":
        return feminin
    if genre == "m":
        return masculin
    return f"{masculin}·e" if feminin == masculin + "e" else f"{masculin}/{feminin}"


def _min1(texte: str) -> str:
    """Première lettre en minuscule (sauf sigle comme ASH)."""
    if not texte or (len(texte) > 1 and texte[:2].isupper()):
        return texte
    return texte[0].lower() + texte[1:]


def _elision(mot_avant: str, texte: str) -> str:
    """'de' + 'agent' -> "d'agent" ; 'de' + 'femme' -> 'de femme'."""
    if texte and normaliser(texte[0]).strip() in list("aeiouyh"):
        return f"{mot_avant[:-1]}'{texte}"
    return f"{mot_avant} {texte}"


def _liste(elements: list[str]) -> str:
    elements = [e for e in elements if e]
    if len(elements) <= 1:
        return "".join(elements)
    return ", ".join(elements[:-1]) + " et " + elements[-1]


def date_fr(d: date | None = None) -> str:
    d = d or date.today()
    jour = "1er" if d.day == 1 else str(d.day)
    return f"{jour} {MOIS[d.month - 1]} {d.year}"


def nettoyer_intitule(intitule: str) -> str:
    """'AGENT NETTOYAGE AVION H/F' -> 'agent nettoyage avion' ; retire H/F, CDD, lieux..."""
    t = re.sub(r"[^\w\s'’()/,.\-–—&+]", " ", intitule or "")           # emojis
    t = re.sub(r"\(?\b[hfHF]\s*/\s*[hfHF]\b\)?", " ", t)               # H/F, (f/h)
    t = re.split(r"\s[-–—|]\s|\sdès\s|\s\(\d", t)[0]                    # " - CDD", " dès le..."
    t = re.sub(r"(\s\d+)+\s*$", "", t)                                  # " 70" (de "70 %")
    t = re.sub(r"\s+", " ", t).strip(" -–—,.")
    if len(t.split()) > 1 and t.isupper():  # titre tout en majuscules
        t = t.lower()
    # minuscules, sauf les sigles courts (ASH, ATSEM, VIP...)
    t = " ".join(m if (m.isupper() and 2 <= len(m) <= 5) else m.lower() for m in t.split())
    return t or "ce poste"


def categorie(texte: str) -> str | None:
    """Type de métier principal d'un texte (titre d'offre ou d'expérience)."""
    n = normaliser(texte)
    mots = set(n.split())
    for cat, racines in CATEGORIES.items():
        for r in racines:
            if (r in mots) if r == "ash" else (r in n):
                return cat
    return None


# ----------------------------------------------------------------- choix des expériences

def _score_experience(exp: dict, offre_norm: str, cat_offre: str | None) -> int:
    texte = " ".join([exp.get("titre", "")] + exp.get("details", []))
    score = 0
    if cat_offre and categorie(exp.get("titre", "") + " " + " ".join(exp.get("details", []))) == cat_offre:
        score += 10
    mots = {m for m in normaliser(texte).split() if len(m) >= 5}
    score += sum(1 for m in mots if f" {m}" in offre_norm)
    return score


def experiences_pertinentes(profil: dict, offre: dict, nombre: int = 2) -> list[dict]:
    exps = profil.get("experiences", [])
    offre_norm = normaliser(offre.get("intitule", "") + " " + (offre.get("description") or ""))
    cat = categorie(offre.get("intitule", "")) or categorie(offre_norm)
    classees = sorted(enumerate(exps), key=lambda ie: (-_score_experience(ie[1], offre_norm, cat), ie[0]))
    choisies = sorted(classees[:nombre], key=lambda ie: ie[0])  # garder l'ordre du CV (récent d'abord)
    return [e for _, e in choisies]


def _phrase_experience(exp: dict) -> str:
    titre = _min1(exp.get("titre", "").split("–")[0].split(" - ")[0].strip())
    ou = exp.get("structure") or ""
    if normaliser(ou).split()[:1] in (["plusieurs"], ["differentes"], ["diverses"], ["differents"]):
        ou = _min1(ou)
    dates = exp.get("dates") or ""
    actuel = "aujourd" in normaliser(dates)
    debut = f"En tant {_elision('que', titre)}" if titre else "Dans mon poste"
    if ou:
        debut += f" chez {ou}"
    if actuel:
        depart = re.split(r"\s*[-–—]\s*", dates)[0].strip()
        debut += f" (depuis {_min1(depart)})" if depart and "aujourd" not in normaliser(depart) else ""
    elif dates:
        debut += f" ({dates})"
    details = [_min1(d.rstrip(".")) for d in exp.get("details", [])
               if "quelques semaines" not in normaliser(d)]
    if not details:
        return debut + "."
    verbe = "mes missions sont" if actuel else "mes missions étaient"
    return f"{debut}, {verbe} : {_liste(details)}."


def _domaines(profil: dict) -> list[str]:
    vus = []
    for e in profil.get("experiences", []):
        cat = categorie(e.get("titre", "") + " " + " ".join(e.get("details", [])))
        if cat and DOMAINES[cat] not in vus:
            vus.append(DOMAINES[cat])
    return vus


def _premiere_annee(profil: dict) -> int | None:
    annees = [int(a) for e in profil.get("experiences", []) for a in re.findall(r"\b(19\d\d|20\d\d)\b", e.get("dates", ""))]
    return min(annees) if annees else None


# ----------------------------------------------------------------- lettre complète

def generer_lettre(profil: dict, offre: dict, aujourd_hui: date | None = None) -> str:
    poste = nettoyer_intitule(offre.get("intitule", ""))
    entreprise = (offre.get("entreprise") or "").strip()
    cat = categorie(offre.get("intitule", "")) or categorie(offre.get("description") or "")
    motivee = _g(profil, "motivée", "motivé")

    paragraphes = []

    # 1. Objet de la candidature + parcours
    intro = f"Je vous propose ma candidature au poste {_elision('de', poste)}"
    intro += f" au sein {_elision('de', entreprise)}." if entreprise else "."
    domaines = _domaines(profil)
    annee = _premiere_annee(profil)
    if domaines:
        depuis = f"Depuis {annee}, j'ai travaillé" if annee else "J'ai travaillé"
        intro += f" {depuis} dans {_liste(domaines)}, ce qui m'a permis d'acquérir une solide expérience du terrain."
    paragraphes.append(intro)

    # 2. Expériences les plus proches de l'offre
    phrases = [_phrase_experience(e) for e in experiences_pertinentes(profil, offre)]
    if phrases:
        paragraphes.append(" ".join(phrases))

    # 3. Motivation propre au métier + qualités
    motivation = MOTIVATION.get(cat, MOTIVATION[None]).format(motivee=motivee)
    qualites = [_min1(q) for q in profil.get("qualites", [])]
    if qualites:
        motivation += f" Je mets à votre service les qualités suivantes : {_liste(qualites)}."
    paragraphes.append(motivation)

    # 4. Disponibilités + conclusion
    fin = ""
    if profil.get("disponibilite"):
        fin = f"Côté disponibilités : {_min1(profil['disponibilite'].rstrip('.'))}. "
    fin += ("Je serais ravie" if profil.get("genre") == "f" else "Je serais ravi" if profil.get("genre") == "m"
            else "Je serais heureux·se")
    fin += " de vous rencontrer afin de vous présenter ma motivation lors d'un entretien."
    paragraphes.append(fin)

    nom = f"{profil.get('prenom', '')} {profil.get('nom', '')}".strip()
    lieu_date = f"{profil.get('ville') or ''}, le {date_fr(aujourd_hui)}".lstrip(", ")
    return "\n\n".join([
        lieu_date,
        f"Objet : candidature au poste {_elision('de', poste)}",
        "Madame, Monsieur,",
        *paragraphes,
        "Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.",
        nom,
    ])


def generer_message_court(profil: dict, offre: dict) -> str:
    """Version courte, pour le champ « message au recruteur » des formulaires ou un email."""
    poste = nettoyer_intitule(offre.get("intitule", ""))
    interessee = _g(profil, "intéressée", "intéressé")
    domaines = _domaines(profil)
    lignes = [
        "Madame, Monsieur,",
        f"Je suis très {interessee} par votre offre {_elision('de', poste)}."
        + (f" J'ai une solide expérience dans {_liste(domaines)}." if domaines else ""),
    ]
    if profil.get("disponibilite"):
        lignes.append(f"Disponibilités : {_min1(profil['disponibilite'].rstrip('.'))}.")
    lignes.append("Vous trouverez mon CV en pièce jointe. Je reste à votre disposition pour un entretien.")
    signature = f"{profil.get('prenom', '')} {profil.get('nom', '')}".strip()
    if profil.get("telephone"):
        signature += f" – {profil['telephone']}"
    lignes.append(f"Cordialement,\n{signature}")
    return "\n\n".join(lignes)
