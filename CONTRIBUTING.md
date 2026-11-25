# Contribuer au projet Goutte d'eau

## Organisation

* **Méthode** : sprints Scrum de 2 semaines (cadre hybride cycle en V + Scrum + CRISP-DM, voir le cahier des charges).
* **Backlog** : GitHub Projects, vue tableau `À faire → En cours → En revue → Terminé`, une issue par user story.
  Champs personnalisés : priorité MoSCoW, points, sprint, epic.
* **Rituels** : daily de 15 min, revue et rétrospective en fin de sprint, démonstration au comité utilisateurs
  toutes les 6 semaines.
* **Messagerie** : Tchap (messagerie de l'État), salon `#goutte-deau-dev`. Les décisions sont reportées dans l'issue.

## Branches et revues

1. Partir de `main` à jour : `git switch -c feature/<numero-issue>-<sujet>`.
2. Commits courts au présent (`ajoute le contrôle des pluviomètres`), une intention par commit.
3. Ouvrir une pull request liée à l'issue (`Closes #12`) avec le modèle fourni.
4. Fusion sur `main` après **une relecture approuvée** et une **CI verte**. `main` est protégée : pas de push direct.

## Définition de « terminé »

* critères d'acceptation de la story vérifiés ;
* tests ajoutés ou mis à jour, `pytest -q` vert ;
* README ou `docs/` mis à jour si le comportement change ;
* métriques du modèle régénérées (`make entrainement`) si la donnée ou le modèle changent ;
* aucun secret dans le code (jetons dans des variables d'environnement, fichier `.env` ignoré par git).
