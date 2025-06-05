# Rapport d'audit : backend/db.py

## Points forts
- Utilisation de SQLAlchemy async pour la gestion de la base PostgreSQL.
- Modèles ORM clairs pour `ObjetTrouve` et `ObjetPerdu`.
- Utilisation d'index sur les IDs pour accélérer les requêtes.

## Risques et améliorations
- **Aucune gestion d'intégrité référentielle** : Les suppressions d'objets trouvés ou perdus ne vérifient pas l'existence de dépendances.
- **Peu de validations côté modèle** : Les contraintes sont principalement gérées côté API, pas côté base.
- **Pas de migration automatique** : Pas d'outils de migration détectés (ex : Alembic). Peut poser problème lors de l'évolution du schéma.
- **Sécurité** : Pas de contrôle d'accès ou d'authentification sur la base.

## Suggestions
- Ajouter des migrations pour la base (Alembic).
- Ajouter des contraintes d'unicité ou de validation côté base si pertinent.
- Prévoir des outils de backup/restore.
