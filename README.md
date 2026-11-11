# EnvoieCVAuto

Application locale pour automatiser la recherche d'emploi :
importer son CV, trouver des offres (nettoyage, hôtellerie, restauration collective...),
adapter le CV à chaque offre et envoyer les candidatures par email.

## Fonctionnalités

- [x] **Mon CV** : import du CV PDF + saisie du profil + génération d'un CV PDF propre
- [x] **Recherche d'offres** : API France Travail (métiers prédéfinis, ville + rayon ou département,
      type de contrat), recherches enregistrées, tri par statut, ajout manuel d'offres
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

## Obtenir les clés France Travail (gratuit)

1. Créer un compte sur https://francetravail.io
2. Aller dans « Mes applications » puis créer une application
3. Abonner l'application à l'API **« Offres d'emploi v2 »**
4. Copier l'identifiant client et la clé secrète dans `.env` :
   `FRANCE_TRAVAIL_CLIENT_ID=...` et `FRANCE_TRAVAIL_CLIENT_SECRET=...`
5. Relancer l'application

## Données personnelles

Le CV, le profil et la base de données sont stockés dans `data/`, et les mots de passe
dans `.env`. Ces deux emplacements sont exclus de Git : ils ne partent jamais sur GitHub.
