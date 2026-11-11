"""Base de données SQLite : offres trouvées et recherches enregistrées."""
import json
import sqlite3
from datetime import datetime

from . import config

STATUTS = {
    "nouvelle": "Nouvelle",
    "a_postuler": "À postuler",
    "envoyee": "Candidature envoyée",
    "ignoree": "Ignorée",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS offres (
    id              TEXT PRIMARY KEY,   -- ex: "FT-123ABC" ou "MAN-..." (ajout manuel)
    source          TEXT NOT NULL,      -- "france_travail" ou "manuel"
    intitule        TEXT NOT NULL,
    entreprise      TEXT,
    lieu            TEXT,
    type_contrat    TEXT,
    duree_travail   TEXT,
    salaire         TEXT,
    date_creation   TEXT,
    description     TEXT,
    email_contact   TEXT,               -- email trouvé dans l'offre (pour l'envoi auto)
    url_postulation TEXT,               -- lien pour postuler en ligne
    url_offre       TEXT,               -- lien vers l'offre
    competences     TEXT,               -- JSON : liste de compétences demandées
    mot_cle         TEXT,               -- recherche qui a trouvé l'offre
    statut          TEXT NOT NULL DEFAULT 'nouvelle',
    date_ajout      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recherches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mots_cles   TEXT NOT NULL,          -- un mot-clé par ligne
    departement TEXT,
    commune     TEXT,                   -- code INSEE
    ville       TEXT,                   -- nom affiché
    distance    INTEGER,
    contrats    TEXT,                   -- ex: "CDI,CDD"
    date_ajout  TEXT NOT NULL
);
"""


def connexion() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_FILE)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def enregistrer_offres(offres: list[dict]) -> int:
    """Ajoute les offres absentes de la base. Renvoie le nombre de nouvelles offres.

    Une offre déjà connue n'est pas modifiée (on garde son statut).
    """
    nouvelles = 0
    with connexion() as con:
        for o in offres:
            cur = con.execute(
                """INSERT OR IGNORE INTO offres
                   (id, source, intitule, entreprise, lieu, type_contrat, duree_travail, salaire,
                    date_creation, description, email_contact, url_postulation, url_offre,
                    competences, mot_cle, statut, date_ajout)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'nouvelle',?)""",
                (
                    o["id"], o["source"], o["intitule"], o.get("entreprise"), o.get("lieu"),
                    o.get("type_contrat"), o.get("duree_travail"), o.get("salaire"),
                    o.get("date_creation"), o.get("description"), o.get("email_contact"),
                    o.get("url_postulation"), o.get("url_offre"),
                    json.dumps(o.get("competences", []), ensure_ascii=False),
                    o.get("mot_cle"), _maintenant(),
                ),
            )
            nouvelles += cur.rowcount
    return nouvelles


def lister_offres(statut: str | None = None, avec_email: bool = False) -> list[sqlite3.Row]:
    sql = "SELECT * FROM offres WHERE 1=1"
    params: list = []
    if statut:
        sql += " AND statut = ?"
        params.append(statut)
    if avec_email:
        sql += " AND email_contact IS NOT NULL AND email_contact != ''"
    sql += " ORDER BY date_creation DESC, date_ajout DESC"
    with connexion() as con:
        return con.execute(sql, params).fetchall()


def compter_par_statut() -> dict:
    with connexion() as con:
        rows = con.execute("SELECT statut, COUNT(*) n FROM offres GROUP BY statut").fetchall()
    return {r["statut"]: r["n"] for r in rows}


def get_offre(offre_id: str) -> dict | None:
    with connexion() as con:
        row = con.execute("SELECT * FROM offres WHERE id = ?", (offre_id,)).fetchone()
    if not row:
        return None
    o = dict(row)
    o["competences"] = json.loads(o["competences"] or "[]")
    return o


def changer_statut(offre_id: str, statut: str) -> None:
    if statut not in STATUTS:
        raise ValueError(statut)
    with connexion() as con:
        con.execute("UPDATE offres SET statut = ? WHERE id = ?", (statut, offre_id))


def supprimer_offre(offre_id: str) -> None:
    with connexion() as con:
        con.execute("DELETE FROM offres WHERE id = ?", (offre_id,))


# --- Recherches enregistrées (relancées automatiquement à l'étape "envoi auto") ---

def ajouter_recherche(r: dict) -> int:
    with connexion() as con:
        cur = con.execute(
            """INSERT INTO recherches (mots_cles, departement, commune, ville, distance, contrats, date_ajout)
               VALUES (?,?,?,?,?,?,?)""",
            (r["mots_cles"], r.get("departement"), r.get("commune"), r.get("ville"),
             r.get("distance"), r.get("contrats"), _maintenant()),
        )
        return cur.lastrowid


def lister_recherches() -> list[dict]:
    with connexion() as con:
        return [dict(r) for r in con.execute("SELECT * FROM recherches ORDER BY id").fetchall()]


def get_recherche(rid: int) -> dict | None:
    with connexion() as con:
        r = con.execute("SELECT * FROM recherches WHERE id = ?", (rid,)).fetchone()
    return dict(r) if r else None


def supprimer_recherche(rid: int) -> None:
    with connexion() as con:
        con.execute("DELETE FROM recherches WHERE id = ?", (rid,))
