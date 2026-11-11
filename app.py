"""EnvoieCVAuto - application web locale.

Lancer :  .venv\\Scripts\\python app.py   puis ouvrir http://127.0.0.1:5000
"""
from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from pypdf import PdfReader

from envoiecv import config
from envoiecv.cv_pdf import generer_cv_pdf
from envoiecv.profil import blocs_en_texte, charger_profil, profil_depuis_formulaire, sauver_profil

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 Mo max pour le CV


@app.route("/")
def accueil():
    profil = charger_profil()
    return render_template(
        "index.html",
        profil=profil,
        cv_original=config.CV_ORIGINAL_FILE.exists(),
        gmail_ok=bool(config.GMAIL_ADDRESS and config.GMAIL_APP_PASSWORD),
        france_travail_ok=bool(config.FRANCE_TRAVAIL_CLIENT_ID and config.FRANCE_TRAVAIL_CLIENT_SECRET),
    )


@app.route("/profil", methods=["GET", "POST"])
def profil():
    if request.method == "POST":
        sauver_profil(profil_depuis_formulaire(request.form))
        flash("Profil enregistré.", "ok")
        return redirect(url_for("profil"))

    p = charger_profil()
    return render_template(
        "profil.html",
        p=p,
        experiences_txt=blocs_en_texte(p["experiences"]),
        formations_txt=blocs_en_texte(p["formations"]),
        cv_original=config.CV_ORIGINAL_FILE.exists(),
    )


@app.route("/cv/upload", methods=["POST"])
def upload_cv():
    fichier = request.files.get("cv")
    if not fichier or not fichier.filename:
        flash("Aucun fichier choisi.", "erreur")
        return redirect(url_for("profil"))
    if not fichier.filename.lower().endswith(".pdf"):
        flash("Le CV doit être au format PDF.", "erreur")
        return redirect(url_for("profil"))

    fichier.save(config.CV_ORIGINAL_FILE)
    try:
        PdfReader(config.CV_ORIGINAL_FILE)
    except Exception:
        config.CV_ORIGINAL_FILE.unlink(missing_ok=True)
        flash("Ce fichier n'est pas un PDF valide.", "erreur")
        return redirect(url_for("profil"))

    flash("CV importé.", "ok")
    return redirect(url_for("profil"))


@app.route("/cv/texte")
def texte_cv():
    """Extrait le texte du CV importé (pour aider à remplir le profil)."""
    if not config.CV_ORIGINAL_FILE.exists():
        return "Aucun CV importé.", 404
    reader = PdfReader(config.CV_ORIGINAL_FILE)
    texte = "\n".join(page.extract_text() or "" for page in reader.pages)
    return texte, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/cv/original")
def voir_cv_original():
    if not config.CV_ORIGINAL_FILE.exists():
        flash("Aucun CV importé.", "erreur")
        return redirect(url_for("profil"))
    return send_file(config.CV_ORIGINAL_FILE, mimetype="application/pdf")


@app.route("/cv/genere")
def voir_cv_genere():
    generer_cv_pdf(charger_profil(), config.CV_GENERE_FILE)
    return send_file(config.CV_GENERE_FILE, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
