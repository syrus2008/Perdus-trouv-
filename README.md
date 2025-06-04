# Plateforme Objets Perdus & Trouvés – Festival

Plateforme professionnelle pour déclarer et consulter les objets trouvés ou perdus lors d’un événement (prête pour Railway).

## Fonctionnalités
- Déclaration d’objets trouvés (avec photo, description, date/heure, infos)
- Déclaration d’objets perdus (sans photo, description, date/heure estimée, infos)
- Affichage moderne et responsive sous forme de cartes
- Validation et feedback utilisateur (frontend & backend)
- Compatible Railway (déploiement facile)

## Démarrage local

1. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```
2. **Copier le fichier d’exemple d’environnement**
   ```bash
   cp backend/.env.example backend/.env
   ```
   (ou créez `backend/.env` à partir du modèle)
3. **Lancer le serveur**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
4. **Accéder à l’application**
   Ouvrir [http://localhost:8000](http://localhost:8000)

## Déploiement Railway

- Le `Procfile` et `.env.example` sont prêts.
- Déployer le repo sur Railway, configurer les variables d’environnement si besoin.
- Le port est automatiquement géré par Railway (`$PORT`).

## Variables d’environnement
Voir `backend/.env.example` pour la configuration (dossiers, taille max upload, etc).

---

Design & développement : Carte blanche, UI/UX pro, accessibilité renforcée.
