# Fiche modèle – Goutte d'eau MVP v0.1

| Rubrique | Contenu |
|---|---|
| Usage prévu | Aide à la décision pour les agriculteurs : probabilité de pluie ≥ 0,2 mm dans les 3 h, heure par heure. Ne remplace pas la vigilance officielle. |
| Algorithme | Forêt aléatoire scikit-learn, 200 arbres, profondeur 6, 10 exemples minimum par feuille, sans pondération des classes |
| Données | Infoclimat, 7 stations d'Île-de-France aux pluviomètres contrôlés, 1er–30 septembre 2026, 4 340 heures-station, 4,0 % de positifs |
| Variables | 15 variables horaires (mesures locales, tendances de pression, pluie récente, heure, contexte régional) |
| Évaluation | Validation croisée par jour : ROC-AUC 0,836, PR-AUC 0,437, rappel 0,63, précision 0,39, Brier 0,029. Test temporel 23–30 sept. : F2 0,55 contre 0,39 pour la persistance |
| Seuil d'alerte | 0,11, choisi pour maximiser le F2 (le rappel pèse double) |
| Variables dominantes | pluie moyenne régionale, nombre de stations sous la pluie, pluie locale récente, pression |
| Limites connues | un seul mois et 8 jours de pluie ; aucun orage d'été dans les données ; peu de stations ; en pratique, le modèle repère surtout une pluie déjà présente dans la région, il l'anticipe mal |
| Biais | stations surtout à l'ouest et au nord de la région ; Paris représenté par une station sur 2 jours |
| Sobriété | entraînement complet ≈ 6 s sur CPU, inférence ≈ 40 ms par journée ; modèle de 0,7 Mo |
| Réentraînement | à chaque nouvel historique mensuel, avec comparaison aux métriques de la version précédente (table `entrainements`) |
