# Rapport d'audit : frontend/listes.html

## Points forts
- Structure HTML claire et sémantique.
- Intégration des modales et des scripts nécessaires.
- Utilisation de classes et d'IDs pour la manipulation JS.

## Risques et améliorations
- **Dépendance forte aux IDs/classes** : Toute modification dans le HTML doit être répercutée dans le JS.
- **Accessibilité** : Peu d'attributs ARIA ou de navigation clavier détectés.
- **Sécurité** : Aucune protection contre l'injection HTML dans les champs affichés (penser à échapper tout contenu utilisateur).

## Suggestions
- Ajouter des attributs d'accessibilité (aria-label, etc.).
- Échapper systématiquement les champs dynamiques injectés dans le HTML.
- Ajouter des tests manuels sur différents navigateurs.
