# EnvoieCVAuto

Application locale pour automatiser la recherche d'emploi :
importer son CV, trouver des offres (nettoyage, hôtellerie, restauration collective...),
adapter le CV à chaque offre et envoyer les candidatures par email.

## Fonctionnalités

- [x] **Mon CV** : import du CV PDF + saisie du profil + génération d'un CV PDF propre
- [x] **Recherche d'offres** : API Adzuna (métiers prédéfinis, ville + rayon ou département,
      type de contrat, temps partiel), recherches enregistrées, tri par statut, ajout manuel d'offres
- [x] **Recherche automatique** : au démarrage puis toutes les 3 h, à partir des « postes
      recherchés », de la ville et du rayon du CV. Chaque offre reçoit un score de correspondance
      avec le CV ; l'accueil affiche les offres pertinentes, les plus récentes d'abord.
- [x] **Suivi des candidatures** : « J'ai postulé » avec date et preuve, page « Mes candidatures »,
      rappel de relance après 7 jours
- [x] **Lettre de motivation automatique** pour chaque offre (texte à copier, PDF, message court
      pour les formulaires), basée uniquement sur le contenu du CV ; modifiable offre par offre
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

## Obtenir les clés Adzuna (gratuit)

1. Créer un compte sur https://developer.adzuna.com (bouton « Register »)
2. Dans le tableau de bord, copier l'**Application ID** et l'**Application Key** dans `.env` :
   `ADZUNA_APP_ID=...` et `ADZUNA_APP_KEY=...`
3. Relancer l'application

Le compte gratuit permet environ 250 recherches par jour (une par métier coché).

### France Travail (optionnel)

L'API « Offres d'emploi v2 » de France Travail n'est plus ouverte aux nouvelles applications
(accès sur demande via le formulaire de contact de francetravail.io). Si l'accès est accordé,
remplir `FRANCE_TRAVAIL_CLIENT_ID` et `FRANCE_TRAVAIL_CLIENT_SECRET` dans `.env` : la source
s'active automatiquement en plus d'Adzuna.

## Données personnelles

Le CV, le profil et la base de données sont stockés dans `data/`, et les mots de passe
dans `.env`. Ces deux emplacements sont exclus de Git : ils ne partent jamais sur GitHub.
