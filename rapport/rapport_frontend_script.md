# Rapport d'audit : frontend/script.js

## Points forts
- Gestion dynamique des listes, recherche, modales et formulaires.
- Vérification de la présence des éléments DOM avant manipulation.
- Gestion des erreurs lors des exports (alertes utilisateur).
- Aperçu photo avant upload.

## Risques et améliorations
- **Dépendance forte aux IDs HTML** : Si un ID change, certaines fonctionnalités JS ne fonctionneront plus.
- **Peu de validation côté client** : Les formulaires pourraient être mieux validés avant envoi (taille, format, champs obligatoires).
- **Gestion d'erreur Cloudinary/Backend** : Les erreurs d'upload ou de réponse API ne sont pas toujours affichées à l'utilisateur.
- **Sécurité** : Pas de contrôle d'accès côté JS (normal, mais attention à l'exposition des routes sensibles côté backend).

## Suggestions
- Ajouter plus de validations côté JS.
- Centraliser la gestion d'erreur des requêtes fetch.
- Modulariser le code JS pour une meilleure maintenabilité.
