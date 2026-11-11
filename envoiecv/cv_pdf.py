"""Génération d'un CV PDF propre à partir du profil."""
from pathlib import Path

from fpdf import FPDF

BLEU = (31, 78, 121)
GRIS = (90, 90, 90)

# Les polices intégrées de PDF ne gèrent que le latin-1 : on remplace
# les caractères typographiques courants (apostrophe courbe, œ, €...).
REMPLACEMENTS = {
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", "œ": "oe",
    "Œ": "OE", "€": "EUR", "•": "-", " ": " ",
}


def _t(texte: str) -> str:
    texte = str(texte or "")
    for k, v in REMPLACEMENTS.items():
        texte = texte.replace(k, v)
    return texte.encode("latin-1", "replace").decode("latin-1")


class _CV(FPDF):
    def section(self, titre: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*BLEU)
        self.cell(0, 7, _t(titre.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BLEU)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def puce(self, texte: str):
        self.set_font("Helvetica", "", 10)
        self.set_x(self.l_margin + 3)
        self.multi_cell(0, 5, _t("- " + texte), new_x="LMARGIN", new_y="NEXT")

    def bloc(self, b: dict):
        self.set_font("Helvetica", "B", 10.5)
        self.cell(0, 5.5, _t(b.get("titre", "")), new_x="LMARGIN", new_y="NEXT")
        sous = " - ".join(x for x in [b.get("structure"), b.get("lieu"), b.get("dates")] if x)
        if sous:
            self.set_font("Helvetica", "I", 9.5)
            self.set_text_color(*GRIS)
            self.cell(0, 5, _t(sous), new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
        for d in b.get("details", []):
            self.puce(d)
        self.ln(1.5)


def generer_lettre_pdf(profil: dict, offre: dict, texte: str) -> bytes:
    """Lettre de motivation au format courrier (coordonnées, destinataire, texte)."""
    pdf = FPDF(format="A4")
    pdf.set_margins(22, 20, 22)
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()

    # Expéditeur (en haut à gauche)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 5.5, _t(f"{profil.get('prenom', '')} {profil.get('nom', '')}".strip()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for ligne in [profil.get("adresse") or profil.get("ville"), profil.get("telephone"), profil.get("email")]:
        if ligne:
            pdf.cell(0, 5, _t(ligne), new_x="LMARGIN", new_y="NEXT")

    # Destinataire (à droite)
    dest = [x for x in [offre.get("entreprise"), offre.get("lieu")] if x]
    if dest:
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 10.5)
        for i, ligne in enumerate(dest):
            if i == 1:
                pdf.set_font("Helvetica", "", 10)
            pdf.set_x(pdf.w / 2 + 5)
            pdf.multi_cell(0, 5, _t(ligne), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    paragraphes = [p.strip() for p in texte.replace("\r\n", "\n").split("\n\n") if p.strip()]
    for i, para in enumerate(paragraphes):
        if i == 0 and ", le " in para:  # "Ville, le 11 novembre 2026" aligné à droite
            pdf.set_font("Helvetica", "", 10.5)
            pdf.multi_cell(0, 5.5, _t(para), align="R", new_x="LMARGIN", new_y="NEXT")
        elif para.lower().startswith("objet"):
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.multi_cell(0, 5.5, _t(para), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "", 10.5)
            pdf.multi_cell(0, 5.5, _t(para), align="J", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
    return bytes(pdf.output())


def generer_cv_pdf(profil: dict, chemin: Path) -> Path:
    pdf = _CV(format="A4")
    pdf.set_margins(16, 14, 16)
    pdf.set_auto_page_break(True, margin=14)
    pdf.add_page()

    # En-tête : nom + titre
    nom = f"{profil.get('prenom', '')} {profil.get('nom', '').upper()}".strip()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*BLEU)
    pdf.cell(0, 10, _t(nom or "Mon CV"), new_x="LMARGIN", new_y="NEXT")
    if profil.get("titre"):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 7, _t(profil["titre"]), new_x="LMARGIN", new_y="NEXT")

    contact = " | ".join(x for x in [
        profil.get("telephone"), profil.get("email"), profil.get("adresse") or profil.get("ville"),
        f"Permis {profil['permis']}" if profil.get("permis") else "",
    ] if x)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*GRIS)
    pdf.cell(0, 6, _t(contact), new_x="LMARGIN", new_y="NEXT")
    if profil.get("disponibilite"):
        pdf.cell(0, 5, _t("Disponibilité : " + profil["disponibilite"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    if profil.get("accroche"):
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _t(profil["accroche"]), new_x="LMARGIN", new_y="NEXT")

    if profil.get("experiences"):
        pdf.section("Expériences professionnelles")
        for b in profil["experiences"]:
            pdf.bloc(b)

    if profil.get("competences"):
        pdf.section("Compétences")
        for c in profil["competences"]:
            pdf.puce(c)

    if profil.get("formations"):
        pdf.section("Formations")
        for b in profil["formations"]:
            pdf.bloc(b)

    if profil.get("qualites"):
        pdf.section("Qualités")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _t(" - ".join(profil["qualites"])), new_x="LMARGIN", new_y="NEXT")

    if profil.get("langues"):
        pdf.section("Langues")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _t(" - ".join(profil["langues"])), new_x="LMARGIN", new_y="NEXT")

    chemin = Path(chemin)
    pdf.output(str(chemin))
    return chemin
