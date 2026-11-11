"""Lecture / écriture du profil du candidat (infos du CV)."""
import json

from .config import PROFIL_FILE

PROFIL_VIDE = {
    "prenom": "",
    "nom": "",
    "email": "",
    "telephone": "",
    "adresse": "",
    "ville": "",
    "permis": "",
    "titre": "",
    "accroche": "",
    "competences": [],
    "experiences": [],
    "formations": [],
    "langues": [],
    "qualites": [],
    "disponibilite": "",
    # Recherche automatique
    "postes_recherches": [],
    "rayon_km": 20,
    "contrats_souhaites": [],  # vide = tous (codes : CDI, CDD, MIS, SAI, PARTIEL)
    # "original" = envoyer le PDF uploadé tel quel, "genere" = CV généré par l'appli
    "cv_a_envoyer": "original",
}


def charger_profil() -> dict:
    if not PROFIL_FILE.exists():
        return dict(PROFIL_VIDE)
    with open(PROFIL_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {**PROFIL_VIDE, **data}


def sauver_profil(profil: dict) -> None:
    with open(PROFIL_FILE, "w", encoding="utf-8") as f:
        json.dump(profil, f, ensure_ascii=False, indent=2)


def lignes(texte: str) -> list[str]:
    """Transforme un texte multi-lignes en liste (lignes vides ignorées)."""
    return [l.strip(" -•\t") for l in texte.splitlines() if l.strip(" -•\t")]


def parser_blocs(texte: str) -> list[dict]:
    """Parse les expériences / formations saisies dans un textarea.

    Format attendu (un bloc par expérience, séparés par une ligne vide) :
        Poste | Entreprise | Ville | Dates
        - tâche 1
        - tâche 2
    """
    blocs = []
    for bloc in texte.replace("\r\n", "\n").split("\n\n"):
        ls = [l for l in bloc.split("\n") if l.strip()]
        if not ls:
            continue
        champs = [c.strip() for c in ls[0].split("|")] + ["", "", "", ""]
        blocs.append({
            "titre": champs[0],
            "structure": champs[1],
            "lieu": champs[2],
            "dates": champs[3],
            "details": lignes("\n".join(ls[1:])),
        })
    return blocs


def blocs_en_texte(blocs: list[dict]) -> str:
    """Inverse de parser_blocs, pour réafficher dans le formulaire."""
    out = []
    for b in blocs:
        entete = " | ".join(
            [b.get("titre", ""), b.get("structure", ""), b.get("lieu", ""), b.get("dates", "")]
        ).rstrip(" |")
        details = "\n".join(f"- {d}" for d in b.get("details", []))
        out.append(entete + ("\n" + details if details else ""))
    return "\n\n".join(out)


def profil_depuis_formulaire(form) -> dict:
    return {
        "prenom": form.get("prenom", "").strip(),
        "nom": form.get("nom", "").strip(),
        "email": form.get("email", "").strip(),
        "telephone": form.get("telephone", "").strip(),
        "adresse": form.get("adresse", "").strip(),
        "ville": form.get("ville", "").strip(),
        "permis": form.get("permis", "").strip(),
        "titre": form.get("titre", "").strip(),
        "accroche": form.get("accroche", "").strip(),
        "competences": lignes(form.get("competences", "")),
        "experiences": parser_blocs(form.get("experiences", "")),
        "formations": parser_blocs(form.get("formations", "")),
        "langues": lignes(form.get("langues", "")),
        "qualites": lignes(form.get("qualites", "")),
        "disponibilite": form.get("disponibilite", "").strip(),
        "postes_recherches": lignes(form.get("postes_recherches", "")),
        "rayon_km": int(form.get("rayon_km") or 20) if str(form.get("rayon_km", "20")).isdigit() else 20,
        "contrats_souhaites": form.getlist("contrats_souhaites"),
        "cv_a_envoyer": form.get("cv_a_envoyer", "original"),
    }
