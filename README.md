# EnvoieCVAuto

Application locale pour automatiser la recherche d'emploi :
importer son CV, trouver des offres (nettoyage, hôtellerie, restauration collective...),
adapter le CV à chaque offre et envoyer les candidatures par email.

## Fonctionnalités

- [x] **Mon CV** : import du CV PDF + saisie du profil + génération d'un CV PDF propre
- [ ] Recherche d'offres (API France Travail)
- [ ] Adaptation du CV à l'offre
- [ ] Envoi automatique des candidatures via Gmail

## Installation (Windows)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env      # puis remplir .env
.venv\Scripts\python app.py
```

Ouvrir ensuite http://127.0.0.1:5000

## Données personnelles

Le CV, le profil et la base de données sont stockés dans `data/`, et les mots de passe
dans `.env`. Ces deux emplacements sont exclus de Git : ils ne partent jamais sur GitHub.
