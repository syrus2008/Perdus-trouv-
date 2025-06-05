# Rapport d'audit : backend/main.py

## Points forts
- Utilisation de FastAPI avec gestion asynchrone des routes.
- Intégration Cloudinary pour l'upload d'image.
- Export HTML avec images embarquées en base64.
- Sécurisation basique des routes sensibles (suppression).
- Validation Pydantic sur les modèles d'entrée.
- Gestion du CORS et des dossiers dynamiques via variables d'environnement.

## Risques et améliorations
- **Synchronisation JSON/DB** : Risque de désynchronisation si une opération échoue sur l'un des deux supports (ex : suppression ou rendu d'objet). À terme, privilégier la base PostgreSQL seule.
- **Gestion d'erreur Cloudinary** : L'échec d'upload n'est pas toujours remonté côté utilisateur. Ajouter un retour d'erreur explicite.
- **Code de suppression en dur** : Le code "7120" est codé en dur, préférez une variable d'environnement.
- **Mélange synchrone/asynchrone** : Les accès fichiers JSON sont synchrones, les accès DB asynchrones. Peut poser problème sous forte charge.
- **Logs** : Peu de logs pour le suivi en production. Ajouter des logs pour chaque opération critique (upload, suppression, export...)
- **Sécurité** : Pas d'authentification pour les opérations critiques (suppression, rendu). Un code statique n'est pas suffisant en production.
- **Validation côté backend** : Les fichiers images sont validés par extension, mais pas par contenu réel (MIME sniffing possible).
- **Gestion des erreurs HTTP** : Les erreurs sont bien remontées mais parfois peu explicites (ex : 404 générique).
- **Robustesse export HTML** : Si une image Cloudinary est inaccessible, l'image sera cassée dans l'export.

## Suggestions
- Migrer complètement vers PostgreSQL et supprimer la dépendance JSON.
- Externaliser les codes sensibles dans des variables d'environnement.
- Ajouter des tests unitaires et d'intégration.
- Ajouter une authentification (admin ou token) pour les routes sensibles.
- Améliorer la gestion des erreurs et les messages retournés à l'utilisateur.
- Ajouter une gestion de quota/taille d'image côté backend.
- Ajouter des logs structurés (ex : logging Python).
