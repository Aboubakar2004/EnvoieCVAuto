"""EnvoieCVAuto - application web locale.

Lancer :  .venv\\Scripts\\python app.py   puis ouvrir http://127.0.0.1:5000
"""
import os
from datetime import date, timedelta

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for
from pypdf import PdfReader

from envoiecv import config, db
from envoiecv.sources import CATEGORIES, TYPES_CONTRAT, SourceErreur, sources_actives
from envoiecv.cv_pdf import generer_cv_pdf
from envoiecv.profil import blocs_en_texte, charger_profil, profil_depuis_formulaire, sauver_profil
from envoiecv.recherche import (ajouter_offre_manuelle, lancer_recherche, preparer_recherche,
                                recalculer_scores)
from envoiecv import auto
from envoiecv.pertinence import SEUIL_PERTINENT, mots_cles_depuis_profil

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 Mo max pour le CV

JOURS_RECENTS = 30  # les offres plus anciennes ne sont plus proposées sur l'accueil


@app.template_filter("date_iso")
def date_iso(texte: str) -> date:
    return date.fromisoformat(texte)


def _date_limite() -> str:
    return (date.today() - timedelta(days=JOURS_RECENTS)).isoformat()


@app.route("/")
def accueil():
    profil = charger_profil()
    return render_template(
        "index.html",
        profil=profil,
        offres=db.lister_offres("nouvelle", score_min=SEUIL_PERTINENT, depuis=_date_limite(), limite=30),
        compteurs=db.compter_par_statut(SEUIL_PERTINENT),
        derniere=db.get_meta("derniere_recherche_auto"),
        prochaine=auto.prochaine_recherche(),
        recherche_en_cours=auto.en_cours(),
        mots_cles=mots_cles_depuis_profil(profil),
        cv_original=config.CV_ORIGINAL_FILE.exists(),
        gmail_ok=bool(config.GMAIL_ADDRESS and config.GMAIL_APP_PASSWORD),
        sources=[s.NOM for s in sources_actives()],
    )


@app.route("/recherche-auto", methods=["POST"])
def lancer_recherche_auto():
    if auto.lancer_en_arriere_plan():
        flash("Recherche lancée : les nouvelles offres apparaîtront dans moins d'une minute.", "ok")
    else:
        flash("Une recherche est déjà en train de tourner : la page se mettra à jour toute seule.", "ok")
    return redirect(url_for("accueil"))


@app.route("/offres/<offre_id>/postule", methods=["POST"])
def postule(offre_id):
    o = db.get_offre(offre_id) or abort(404)
    db.marquer_postule(offre_id, request.form.get("preuve", ""))
    flash(f"Candidature enregistrée : « {o['intitule']} ». Tu la retrouves dans Mes candidatures.", "ok")
    if request.form.get("retour") == "detail":
        return redirect(url_for("detail_offre", offre_id=offre_id))
    return redirect(request.referrer or url_for("accueil"))


@app.route("/candidatures")
def candidatures():
    return render_template("candidatures.html", candidatures=db.lister_candidatures(),
                           aujourd_hui=date.today())


@app.route("/profil", methods=["GET", "POST"])
def profil():
    if request.method == "POST":
        sauver_profil(profil_depuis_formulaire(request.form))
        recalculer_scores()
        flash("Profil enregistré.", "ok")
        return redirect(url_for("profil"))

    p = charger_profil()
    return render_template(
        "profil.html",
        p=p,
        experiences_txt=blocs_en_texte(p["experiences"]),
        formations_txt=blocs_en_texte(p["formations"]),
        cv_original=config.CV_ORIGINAL_FILE.exists(),
        types_contrat=TYPES_CONTRAT,
        mots_cles=mots_cles_depuis_profil(p),
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


# ---------------------------------------------------------------- Offres

def _afficher_resultat(trouvees: int, nouvelles: int, erreurs: list[str]) -> None:
    for e in erreurs:
        flash(e, "erreur")
    if trouvees or not erreurs:
        flash(f"{trouvees} offre(s) trouvée(s), dont {nouvelles} nouvelle(s).", "ok")


@app.route("/offres")
def offres():
    statut = request.args.get("statut", "nouvelle")
    if statut not in db.STATUTS and statut != "toutes":
        statut = "nouvelle"
    avec_email = request.args.get("email") == "1"
    tout = request.args.get("tout") == "1"  # inclure les offres qui ne correspondent pas au CV
    score_min = 0 if tout else SEUIL_PERTINENT
    return render_template(
        "offres.html",
        offres=db.lister_offres(None if statut == "toutes" else statut, avec_email, score_min),
        statut=statut,
        avec_email=avec_email,
        tout=tout,
        statuts=db.STATUTS,
        compteurs=db.compter_par_statut(score_min),
        recherches=db.lister_recherches(),
        categories=CATEGORIES,
        types_contrat=TYPES_CONTRAT,
        sources=[s.NOM for s in sources_actives()],
    )


@app.route("/offres/recherche", methods=["POST"])
def rechercher_offres():
    f = request.form
    mots = f.getlist("metiers") + f.get("autres_mots", "").replace(",", "\n").splitlines()
    try:
        r = preparer_recherche(mots, f.get("lieu", ""), f.get("distance"), f.getlist("contrats"))
        if f.get("enregistrer"):
            db.ajouter_recherche(r)
            flash("Recherche enregistrée : elle pourra être relancée automatiquement.", "ok")
        _afficher_resultat(*lancer_recherche(r, int(f.get("publiee_depuis", 31))))
    except (ValueError, SourceErreur) as e:
        flash(str(e), "erreur")
    return redirect(url_for("offres"))


@app.route("/recherches/<int:rid>/lancer", methods=["POST"])
def relancer_recherche(rid):
    r = db.get_recherche(rid) or abort(404)
    try:
        _afficher_resultat(*lancer_recherche(r))
    except SourceErreur as e:
        flash(str(e), "erreur")
    return redirect(url_for("offres"))


@app.route("/recherches/<int:rid>/supprimer", methods=["POST"])
def supprimer_recherche(rid):
    db.supprimer_recherche(rid)
    flash("Recherche supprimée.", "ok")
    return redirect(url_for("offres"))


@app.route("/offres/ajout", methods=["POST"])
def ajouter_offre():
    try:
        oid = ajouter_offre_manuelle(request.form)
    except ValueError as e:
        flash(str(e), "erreur")
        return redirect(url_for("offres"))
    flash("Offre ajoutée.", "ok")
    return redirect(url_for("detail_offre", offre_id=oid))


@app.route("/offres/<offre_id>")
def detail_offre(offre_id):
    o = db.get_offre(offre_id) or abort(404)
    return render_template("offre.html", o=o, statuts=db.STATUTS)


@app.route("/offres/<offre_id>/statut", methods=["POST"])
def statut_offre(offre_id):
    db.changer_statut(offre_id, request.form["statut"])
    retour = request.form.get("retour")
    if retour == "detail":
        return redirect(url_for("detail_offre", offre_id=offre_id))
    return redirect(request.referrer or url_for("offres"))


@app.route("/offres/<offre_id>/supprimer", methods=["POST"])
def supprimer_offre(offre_id):
    db.supprimer_offre(offre_id)
    flash("Offre supprimée.", "ok")
    return redirect(url_for("offres"))


if __name__ == "__main__":
    # En mode debug, Flask lance 2 processus : on ne démarre la recherche auto que dans le bon.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        auto.demarrer_planificateur()
    app.run(debug=True)
