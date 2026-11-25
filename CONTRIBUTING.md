# Contribuer au projet Goutte d'eau

## Organisation

On travaille en sprints Scrum de 2 semaines, dans un cadre hybride cycle en V + Scrum + CRISP-DM (le détail est
dans le cahier des charges).

Le backlog est dans GitHub Projects, en vue tableau `À faire → En cours → En revue → Terminé`, avec une issue par
user story. On y a ajouté quelques champs : priorité MoSCoW, points, sprint et epic.

Côté rituels : un daily de 15 min, une revue et une rétro en fin de sprint, et une démo au comité utilisateurs
toutes les 6 semaines.

Pour échanger, on utilise Tchap (la messagerie de l'État), salon `#goutte-deau-dev`. Quand une décision est prise,
on la note dans l'issue concernée.

## Branches et revues

1. Partir de `main` à jour : `git switch -c feature/<numero-issue>-<sujet>`.
2. Commits courts au présent (`ajoute le contrôle des pluviomètres`), une intention par commit.
3. Ouvrir une pull request liée à l'issue (`Closes #12`) avec le modèle fourni.
4. On fusionne sur `main` une fois la relecture approuvée et la CI au vert. `main` est protégée, donc pas de push direct.

## Définition de « terminé »

Une story est terminée quand :


* critères d'acceptation de la story vérifiés ;
* tests ajoutés ou mis à jour, `pytest -q` vert ;
* README ou `docs/` mis à jour si le comportement change ;
* métriques du modèle régénérées (`make entrainement`) si la donnée ou le modèle changent ;
* aucun secret dans le code (jetons dans des variables d'environnement, fichier `.env` ignoré par git).
