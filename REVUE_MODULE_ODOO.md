# Revue du module Odoo `oui_allo_rdv_pro`

## Objectif
Reconstituer un module installable en se basant sur le manifeste (`__manifest__.py`) et relever les écarts bloquants.

## Vérifications effectuées
- Vérification de la présence des fichiers déclarés dans `data`.
- Vérification de la présence des assets déclarés dans `web.assets_backend`.
- Contrôle de la structure Python du module (`__init__.py` et sous-modules).
- Nettoyage des artefacts non source (`__pycache__`, `*.pyc`).

## Résultat de la revue

### ✅ Conformités
- Tous les fichiers XML/CSV listés dans `data` existent.
- Le code Python est correctement importé via les `__init__.py` (models, wizard, controllers).
- Le module est marqué `installable=True` et `application=True`.

### ❗ Écart corrigé
1. **Asset CSS manquant selon manifeste**
   - Le manifeste référence: `static/src/css/executive_dashboard.css`
   - Le fichier présent était: `static/src/css/executive_dashboard.cs`
   - **Correction appliquée:** renommage en `.css` pour correspondre exactement au manifeste.

### 🧹 Hygiène du dépôt
- Suppression des dossiers `__pycache__` et des fichiers compilés `*.pyc` qui ne doivent pas être versionnés dans un module Odoo source.

## Recommandations complémentaires
- Ajouter un `.gitignore` pour éviter la réintroduction de `__pycache__/` et `*.pyc`.
- Ajouter un test de cohérence CI qui valide que chaque chemin du manifeste existe réellement.
