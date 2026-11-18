# Cadrage fonctionnel et recette de la plateforme Atlas Éducation

**Version du 17 novembre 2026.** Ce dossier relie la question du Data Challenge Burkina aux fonctions livrées. Il précise ce que les données permettent de mesurer, les règles d’interprétation et les contrôles techniques effectués sur le prototype local.

## Mandat et arbitrages documentaires

La note d’intention propose de localiser les tensions du primaire public, de projeter la demande et d’arbitrer entre ouverture de salles, redéploiement et recrutement. Elle envisage les 12 arrondissements de Ouagadougou et une échéance en 2030. La spécification étend le mandat au **périmètre des 13 régions historiques du classeur** et à l’année scolaire **2049/2050**. La plateforme applique ces deux paramètres à la carte, aux permissions, aux calculs, aux décisions et aux exports. Elle garde 2030 comme premier jalon quinquennal. Toute ventilation infrarégionale future nécessitera une source et des correspondances documentées.

Les identifiants stables correspondent à Boucle du Mouhoun, Cascades, Centre, Centre-Est, Centre-Nord, Centre-Ouest, Centre-Sud, Est, Hauts-Bassins, Nord, Plateau Central, Sahel et Sud-Ouest. La variante source « HAUT-BASSINS » se rattache à Hauts-Bassins et son libellé original est conservé. Les cartes reprennent les géométries ADM1 de 2017. [Métadonnées geoBoundaries et Banque mondiale](https://www.geoboundaries.org/api/current/gbOpen/BFA/ADM1/)

Le primaire public est prioritaire. Le préscolaire a ses propres tableaux, modalités de statut, stocks de salles et hypothèses de calcul. Une année affichée est l’année de fin. L’historique s’étend de 2015/2016 à 2024/2025, avec un début en 2017/2018 pour le milieu au préscolaire. Les colonnes de réussite au CEP correspondent aux sessions 2016 à 2025. Pour le classeur fourni, toutes les années 2025/2026 à 2049/2050 relèvent de la prospective, y compris lorsqu’une année est écoulée à la date de consultation.

### Documents et preuve disponible

| Pièce vérifiée | Usage dans le projet | Éléments contrôlés |
|---|---|---|
| Note d’intention du Data Challenge Burkina 2026 | Question de décision et articulation demande, capacité et accès | Objectifs reportés dans la matrice ci-dessous |
| Prompt de planification à 2050 | Périmètre, cycles, obligation du portail public et du back-office, circuits et critères de recette | Modules M00 à M14 et limites consignées dans ce dossier |
| Classeur statistique du projet | Source observée initiale | 14 feuilles, 21 tableaux, 6 636 cellules de données, 420 formules et provenance à la cellule |
| CSV de démonstration fourni | Essais exploratoires sur trois lacunes du primaire public | 650 valeurs, préservation de 30 marges publiques nationales, ratios illustratifs et statut synthétique |
| Documents de présentation du challenge | Contexte du défi « infrastructures et personnel » | Documentation, prototype et données de travail organisés pour la restitution |

Le fichier statistique local est identifié par l’empreinte SHA-256 `3b87d432c99a83d935003fa8d89083e2ada851791eb7eb6ddecbdaf8759fe4e8`. Les extractions et la recette portent sur cette copie. La plateforme qualifie chaque résultat selon son origine. Une observation conserve sa cellule ou sa ligne de collecte. Une simulation conserve ses paramètres. Une priorité calculée invite à instruire une option. Seul le dossier de décision porte l’orientation administrative motivée, son auteur et son calendrier.

## Matrice de couverture des objectifs de la note

| Objectif de la note | Problématique et données | Fonction et méthode mises en œuvre | Critère de recette vérifiable |
|---|---|---|---|
| Contrôler et rapprocher les sources | Cohérence entre territoires, secteurs, sexes, niveaux et périodes | Prévisualisation, identifiants stables, empreintes, marges, formules enregistrées et anomalies M03–M05 | Réimport identique, somme filles + garçons, sommes régionales, signalement de l’IPS source du Centre |
| Diagnostiquer l’offre | Écoles publiques observées, salles préscolaires recensées, enseignants et salles primaires en complément | Exploration régionale, carte et version des stocks M06, M08, M10 | PRI13 s’affiche en écoles, PRE08 en salles. Les stocks manquants restent indisponibles |
| Estimer la demande future | Inscriptions publiques observées au national, croisement public/région collecté ou simulé | Trois extrapolations simples confrontées à l’historique, trois scénarios annuels par cycle M07 | Base 2025, 25 années prospectives, tests à origine glissante, marges régionales réconciliées |
| Situer les tensions territoriales | Demande, capacité et disponibilité par région. Déplacements et bâti absents | Déficits, charge et écarts de satisfaction de la demande modélisée. Carte historique M06–M10 | Correspondance exacte des 13 clés. Résidu et places servies retrouvent la demande régionale |
| Examiner l’accessibilité physique | Origines de résidence, écoles géolocalisées, voirie, temps de marche | Prérequis signalés dans la méthode et dans les résultats d’intervention M09–M10 | En l’absence du réseau et des points, aucun temps de trajet ni site d’ouverture n’est produit |
| Tester des interventions à moyens limités | Ressources actuelles, sorties, calendriers, enveloppes annuelles et capacité d’exécution | Référence, réhabilitation, extension, recrutement, redéploiement et combinaison M08–M09 | Les transferts conservent les effectifs nationaux. Les calendriers et enveloppes saisies s’appliquent aux options |
| Apprécier les gains et leur robustesse | Demande commune aux options, variation des normes et de la ventilation régionale | Comparateur de places servies, écarts de couverture, besoins résiduels, sensibilité et validation temporelle M07–M09 | Les options utilisent la même demande. Les scénarios portent leur hypothèse et leur millésime |
| Préparer un programme et communiquer les résultats | Résultats validés, justification, niveau d’engagement, millésime des prix | Programme glissant, décision séparée, rapport exportable, autorisation et publication figée M11–M13 | Une version retirée disparaît du portail et de son point de téléchargement. Une correction déclenche le réexamen des dépendances |

## Inventaire des manques et usages autorisés

Le diagnostic observé s’appuie sur les marges nationales publiques, les inscriptions régionales tous statuts, les effectifs par sexe, les entrées au CP1, les taux et indices, les écoles primaires, les structures et salles préscolaires. L’inventaire détaillé garde les 21 plages et leurs dimensions. [Dictionnaire et recette des données](../ingestion/README.md)

| Besoin | Usage exploratoire possible | Collecte pour une orientation opérationnelle |
|---|---|---|
| Effectifs publics de chaque région | Ventilation explicite de la marge nationale, variante de pondération et analyse de sensibilité | Relevés par région, statut, cycle, sexe et année scolaire, harmonisés avec les marges officielles |
| Salles du primaire public | Stocks hypothétiques calculés à partir des inscriptions simulées et de ratios illustratifs | Inventaire par établissement, statut utilisable, capacité, fermetures et dates des travaux |
| Enseignants | Personnes simulées du primaire, disponibilité paramétrable. Au préscolaire, hypothèse séparée si renseignée | Personnel en classe, qualification, quotité, absences, mouvements et dates des affectations |
| Disponibilité des salles préscolaires | Application d’un taux illustratif aux salles recensées, ou saisie de salles utilisables | Vérification fonctionnelle dans chaque structure et distinction du communautaire |
| Démographie et flux de parcours | Extrapolation des inscriptions sous scénarios identifiés | Population par âge et par région, entrées, passages, redoublements, migrations et sorties |
| Accès spatial | Comparaison des besoins et moyens par région | Coordonnées des écoles, bassins de résidence, capacités locales et réseau de marche daté |
| Financement et délais | Prix et enveloppes saisis avec année de prix, plafonds physiques, hypothèses de délais | Coûts d’investissement, maintenance, salaires, budgets votés et calendriers territoriaux sourcés |
| Résilience | Sensibilité à des indisponibilités ou départs explicitement paramétrés | Historique local des fermetures, des réouvertures et des déplacements pour calibrer les chocs |

La simulation fournie comporte un total par sexe et région, des salles et des personnes. Pour 2024/2025, le total national des inscriptions publiques se rattache à la cellule `Feuil2!L5`. Les ventilations régionales produisent exactement cette marge. Les inventaires du personnel et des salles primaires demandent toujours une collecte avant une allocation réelle. Les gabarits de collecte privée portent un identifiant régional, l’année de fin, le cycle, l’indicateur, la valeur, l’unité, la référence et l’année de prix lorsque nécessaire.

## Dix fiches analytiques

Chaque fiche ci-dessous identifie la décision à éclairer, les mesures utilisables, la méthode et la limite à examiner avec le service compétent.

| Problématique et question | Indicateurs et sources disponibles | Méthode et décision éclairée | Limite et condition de confirmation |
|---|---|---|---|
| **Demande et démographie.** Quel volume d’inscriptions publiques préparer en 2050 ? | Séries publiques nationales PRI02/PRE02, effectifs tous statuts PRI01/PRE01, croisement régional selon provenance | Tester dernière valeur, tendance et tendance amortie. Comparer trois trajectoires d’inscriptions pour choisir l’enveloppe de demande à instruire | Les données par âge et les paramètres de scolarisation manquent pour estimer la totalité des enfants scolarisables |
| **Accès et couverture.** Quelles demandes de places resteraient sans offre ? | Demande projetée, salles utilisables, enseignants disponibles, effectif servi et résiduel | Appliquer la capacité effective simplifiée et un facteur d’appariement. Examiner la région dans laquelle une enquête de capacité est prioritaire | La satisfaction de la demande simulée et l’accès physique appellent des indicateurs distincts. Les temps de marche demandent un réseau |
| **Disparités territoriales.** Quelles régions présentent les écarts les plus marqués ? | Inscriptions et taux par région, carte historique, taux de satisfaction simulés | Comparer un même indicateur au même millésime. Dans le simulateur, mesurer l’écart maximal de satisfaction et examiner les priorités récurrentes | Les différences locales au sein d’une région restent invisibles et le contrôle du découpage de toute source future est nécessaire |
| **Équité.** Les variations concernent-elles davantage un sexe ou un milieu ? | Effectifs par sexe, TBA, TBS, TAP, IPS et marges urbain/rural. Le préscolaire conserve le milieu indéterminé | Comparer les sexes dans une même cellule de périmètre. Examiner le rapport féminin/masculin, puis les effectifs avant de demander une enquête ciblée | Le milieu est principalement national. Un croisement supplémentaire requiert sa propre source. Les taux de participation peuvent dépasser 100 % |
| **Infrastructures.** Réhabiliter, étendre ou ouvrir un établissement ? | Écoles PRI13, infrastructures PRE07/PRE08, stocks complémentaires, réhabilitations et salles additionnelles simulées | Suivre l’évolution annuelle du stock et comparer les options avec la référence. Instruire en premier les sites où l’état des locaux est vérifiable | Chaque implantation nouvelle doit disposer d’un site justifié. L’addition de salles et la remise en service d’une salle existante sont deux flux |
| **Enseignants.** Quand recruter ou redéployer ? | Effectifs du personnel collectés ou simulés, départs, absences, mouvements, enveloppe de postes | Répartir des volumes entiers de postes sous délai de formation et conserver les ressources lors d’un transfert. Instruire les mouvements envisagés | Disponibilité géographique, niveau d’enseignement, qualification et accord d’affectation sont à vérifier par les services |
| **Parcours scolaires.** Où l’admission, l’achèvement ou la réussite évoluent-ils ? | PRI05–PRI12, CP1 à CM2 dans PRI04, sections préscolaires dans PRE04 | Suivre les séries comparables par sexe, région et cycle. Repérer un changement qui appelle une analyse du fonctionnement scolaire | Les séries agrégées ne suivent aucune cohorte. Une mesure complète des apprentissages exige d’autres évaluations |
| **Résilience.** Quels moyens préserver face à une perturbation ? | Écarts historiques descriptifs, stocks initiaux et hypothèses annuelles de fermeture ou départ | Modifier les paramètres d’indisponibilité puis comparer le résidu à demande constante. Dimensionner une marge de capacité à examiner | Les variations du classeur ne renseignent pas leurs causes. Les scénarios de choc demandent des événements sourcés pour être calibrés |
| **Financement.** Quelles charges les options engagent-elles ? | Coûts unitaires, enveloppes, salaires, maintenance et coûts d’investissement saisis ou collectés | Calculer par année en FCFA à prix de référence déclaré. Séparer investissement et fonctionnement. Préparer un programme glissant sur cinq ans | Une dépense dont le prix manque reste indisponible. Les conventions de prix et le caractère mobilisable des enveloppes exigent une validation |
| **Gouvernance.** Qui a produit, vérifié et autorisé une orientation ? | Version source, cellule, anomalie, auteur du calcul, hypothèses, états, motifs et journal | Remonter d’une publication vers son analyse et son jeu de données, puis vérifier les droits, les dates et la séparation des actes | Les profils réels, mandats et procédures doivent être établis par l’institution avant l’utilisation décisionnelle |

## Architecture, modèle et habilitations

Le service local est un monolithe modulaire Python, avec une base SQLite privée et deux entrées web en même origine. Une transaction conserve l’état de chaque dossier. L’interface publique reçoit un paquet de publication via les routes de consultation. Les interfaces statiques, la base, les archives de sources et les secrets possèdent des emplacements distincts. Le schéma initial se trouve dans `server/storage.py` avec `user_version=1`. Les modules métier réutilisent ce schéma. Une évolution incompatible demande une migration versionnée et une répétition de la restauration sur une copie.

Le modèle relationnel relie comptes, rôles, demandes d’habilitation, justificatifs de connexion, sessions, archives, jeux versionnés, analyses, travaux, décisions, publications et audit. Les référentiels, observations, anomalies, scénarios, résultats, sources de calcul et flux de ressources sont sérialisés dans les charges JSON versionnées de ces dossiers. Les rapprochements restent possibles par version, table, cellule, année et identifiant régional. Les routes de dépendances filtrent les dossiers accessibles.

| Profil | Actions du catalogue utilisées | Limites techniques du rôle par défaut |
|---|---|---|
| Administrateur | Toutes les permissions du catalogue | Le périmètre du compte, les étapes de validation et les contrôles indépendants s’appliquent à chaque dossier |
| Gestionnaire de données | `data.import`, `data.edit`, `report.export` | Import du classeur national avec habilitation nationale explicite. Une correction crée une version |
| Analyste | `analysis.run`, `projection.run`, `optimization.run`, `report.export` | Calculs dans le périmètre habilité, avec droits vérifiés de nouveau lors des consultations |
| Validateur métier | `data.validate`, `analysis.validate`, `report.export` | Revue indépendante de l’auteur, motivée et limitée au territoire |
| Décideur | `decision.record`, `publication.approve`, `report.export` | Orientation appuyée sur une analyse éligible. Autorisation distincte de la vérification du contenu |
| Responsable de publication | `publication.publish`, `publication.withdraw`, `report.export` | Diffusion d’un contenu vérifié et autorisé, retrait journalisé |
| Visiteur | Consultation des routes publiques | Accès aux versions effectivement diffusées et à leur export public |

L’autorisation côté serveur combine permission, territoire, identité de l’auteur et état de l’objet. Les agrégats nationaux demandent un périmètre national explicite. La politique de contrôle prend pour référence les principes d’autorisation à chaque requête et de moindre privilège. [Recommandations OWASP sur l’autorisation](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

## Fiches de livraison et de recette M00 à M14

Les chemins d’API privés indiqués ci-dessous sont relatifs à `/api/private/`. Le serveur journalise les accès et mutations autorisés ou refusés. Les résultats de tests décrivent les essais sur le jeu fourni et sur des cas de contrôle isolés. La recette institutionnelle appartient au service mandaté.

### Complément provincial et horizon 2050

Le chemin « Annuaire du primaire 2024–2025 et démographie provinciale » utilise l’inventaire DGESS I.1 et V.4.1, les 6–11 ans du RGPH 2019 (volume 4) et les pages du fichier des localités. Les contrôles de M03/M04 vérifient les 45 identifiants, les 720 valeurs de population, les totaux imprimés et la correction documentée de l’Oudalan en 2031. Les trois scénarios de M07 conservent chaque année les marges nationale et régionales. Les poids de 2035 servent jusqu’en 2050. M08/M09 distinguent les besoins provinciaux à inventaire constant et les stocks régionaux évolutifs. M10 et M13 affichent la province dans les versions publiées qui contiennent le référentiel. Les recalculs et la recette individuelle des quinze modules sont décrits dans le README.

### M00 · Cadrage et audit

**Usage et livrable.** Le responsable de projet et le statisticien disposent de la présente matrice, des dix fiches, des 13 identifiants et du relevé des sources initiales. Le portail présente aussi le périmètre et la méthode au visiteur.

**Entrées, code et contrôles.** La note d’intention, la spécification 2050, le classeur, le CSV et les métadonnées géographiques alimentent le dictionnaire `ingestion/referentiel.py`. Le manifeste d’import énumère les tables et les périodes. La date du titre est confrontée aux en-têtes réels. Le test `test_dimensions_and_periods` vérifie notamment la session initiale du CEP et le début du préscolaire par milieu.

**État et suite.** Cadrage documenté et sources locales examinées. Les attestations de provenance institutionnelles et les sources démographiques complémentaires relèvent de la collecte. Ces résultats alimentent M01 et M03.

### M01 · Socle technique

**Usage et livrable.** L’exploitant initialise l’instance et son stockage privé. L’utilisateur démarre depuis le portail `/` ou le back-office `/admin`. Le service renvoie des listes paginées, des détails et des erreurs structurées.

**Entrées, code et contrôles.** `python -m server` initialise ou sert la base configurée. `server/http.py`, `server/storage.py` et les deux pages dans `web/` matérialisent les séparations. `GET /api/public/publications` fonctionne en consultation. `GET me` demande une session privée. Le démarrage vérifie l’emplacement de l’état privé et la version du schéma. Les essais du gestionnaire HTTP vérifient les cookies de session, le jeton CSRF et l’absence d’accès privé anonyme.

**État et suite.** Socle local exercé par les tests serveur. Le raccordement à une infrastructure HTTPS supervisée et le dimensionnement multi-utilisateur restent à effectuer par l’équipe d’exploitation. M02, M03 et M13 réutilisent ce socle.

### M02 · Comptes et habilitations

**Usage et livrable.** L’administrateur gère les comptes, territoires, rôles et demandes d’attribution dans « Habilitations et audit ». La démonstration locale utilise l’identifiant et le mot de passe. L’instance standard demande aussi le code temporaire. Activation, suspension, désactivation, récupération et révocation des sessions disposent d’opérations dédiées.

**Entrées, code et contrôles.** Comptes, catalogue des permissions, rôles, sessions et journal figurent dans `server/storage.py`. `server/admin.py` applique directement les habilitations de l’administrateur et journalise les droits avant et après. Les demandes déléguées et les récupérations suivent le double contrôle. Routes principales `POST /api/login`, `GET users`, `GET roles`, `POST users/{id}/actions`, `POST grants/{id}/approve` et `GET audit`. Un utilisateur suspendu perd sa session. Les tests d’authentification, de révocation, d’attribution et d’accès aux résultats vérifient ces règles ainsi que le rejet d’un dossier d’un autre périmètre.

**État et suite.** Contrôles testés sur des comptes de recette. L’institution doit identifier les personnes titulaires, organiser la remise des facteurs et la revue des habilitations. M04 à M14 s’appuient sur ces contrôles.

### M03 · Référentiels et indicateurs

**Usage et livrable.** Le gestionnaire et l’analyste consultent dans « Données et qualité » la fiche d’un KPI, les axes disponibles et le manifeste des sources. Un même identifiant régional relie la carte, l’historique et la prospective.

**Entrées, code et contrôles.** `ingestion/referentiel.py` décrit les années de fin, cycles, axes, unités et 21 tableaux. `GET datasets/{id}` retourne le catalogue et les informations permises pour le territoire. Le lecteur conserve libellé original et code normalisé. Une modalité inconnue déclenche une erreur de gabarit. Les tests vérifient entre autres écoles/salles, statuts communautaires, ratios de parité et alias « HAUT-BASSINS ».

**État et suite.** Référentiel et unités vérifiés sur les sources initiales. Toute nouvelle source utilisant d’autres territoires nécessite une correspondance documentée avant M04/M10.

### M04 · Import et qualité

**Usage et livrable.** Le gestionnaire national prévisualise le classeur, examine les contrôles et crée un brouillon. La source et son empreinte sont archivées. Un complément synthétique, s’il est choisi, garde sa propre collection et son origine.

**Entrées, code et contrôles.** `POST imports/preview` puis `POST datasets` appellent `ingestion/lecture.py`, `qualite.py`, `demo.py` et l’archivage du service. Le CSV réel relève de `POST datasets/{id}/revise` avec la propriété `csv`. Le lecteur limite les fichiers, contrôle en-têtes, doublons, cache des formules, marges et unités. Une structure incompatible empêche l’import. Les écarts statistiques rejoignent le journal. Le fichier fourni contient 6 621 valeurs disponibles, 15 cellules vides et 18 textes étrangers isolés. Le contrôle de `PRESCOLAIRE!F77` conserve 1 et consigne le rapport concurrent 0,9114263.

**État et suite.** Imports du classeur et des 650 valeurs simulées reproduits. Le réimport identique retrouve la version existante. Les prix et stocks additionnels exigent une collecte distincte. M05 traite la recevabilité métier.

### M05 · Validation des données

**Usage et livrable.** Le gestionnaire soumet sa version et un validateur indépendant examine les anomalies dans le circuit « Validation et publication ». Une révision motivée ouvre un nouveau brouillon lié à son prédécesseur.

**Entrées, code et contrôles.** `POST datasets/{id}/actions` accepte les transitions pertinentes avec motif. `POST datasets/{id}/revise` applique une correction par identifiant ou ajoute un complément. `server/domain.py` gère les états et les dépendances. L’auteur d’une production ne peut pas en assurer la validation, même avec un rôle personnalisé. Les tests exercent le réimport, l’auto-validation refusée, la correction de l’IPS, la propagation d’un réexamen et l’ajout d’une valeur de terrain.

**État et suite.** Circuit technique vérifié. La décision sur l’écart de parité et la validation effective des observations relèvent des personnes habilitées. Une version éligible alimente M06 à M12.

### M06 · Analyses et tableau de bord

**Usage et livrable.** L’analyste explore par cycle, série et dimensions, compare les régions, consulte les valeurs exactes et conserve les filtres d’une analyse. Les exports autorisés reprennent le périmètre accessible.

**Entrées, code et contrôles.** `GET datasets/{id}/observations`, `POST analyses` de type `exploration` et `GET analyses/{id}/export` s’appuient sur `server/domain.py` et `web/assets/analysis-screen.js`. Un indicateur est lu dans une table identifiée pour éviter les doubles comptes. Les contrôles de marges vérifient la cohérence des données. Les tests d’accès vérifient le rejet d’un identifiant d’analyse national depuis un compte régional et le filtrage des exports.

**État et suite.** Consultation, enregistrement et exports implémentés. Une analyse par sexe, milieu et statut combinés exige que la table comporte réellement ces trois axes. Les résultats peuvent suivre M11.

### M07 · Prospective 2050

**Usage et livrable.** L’analyste fixe le cycle, la base, la méthode et l’hypothèse de demande. L’écran « Prospective 2050 » présente la trajectoire annuelle, les trois scénarios, les jalons et les erreurs historiques.

**Entrées, code et contrôles.** `planning/forecast.py` lit les séries publiques compatibles. Le module de régression quantile apprend trois trajectoires et compare deux amortissements sur les pertes quantiles à un et deux ans. La dernière observation, la tendance et la tendance amortie servent de références pour comparer la précision de la centrale. `POST jobs` avec `kind=projection`, `GET jobs/{id}` et `GET analyses/{id}` conservent les paramètres et le résultat. Une base sans observation pertinente laisse la série indisponible. Les tests contrôlent l’antériorité des données d’entraînement, les 25 années, les marges régionales, les autorisations et le changement de base.

**État et suite.** Modèle d’inscriptions vérifié sur des trajectoires conditionnelles. Les marges de scénario représentent des hypothèses. Une projection démographique par cohortes exige des effectifs par âge et des flux documentés. M08/M09 reprennent une demande commune, M11 peut examiner la trajectoire. [Principes de validation temporelle](https://otexts.com/fpp3/toolbox.html) · [Construction de scénarios](https://otexts.com/fpp3/judgmental.html#scenario-forecasting)

### M08 · Ressources et budgets

**Usage et livrable.** L’analyste renseigne dans « Ressources et contraintes » les normes de classe, parts de disponibilité, départs, délais, coûts et budgets annuels. Chaque cycle garde ses paramètres.

**Entrées, code et contrôles.** Le gabarit `COLLECTE` alimente les ressources réelles. Les hypothèses et stocks synthétiques restent déclarés comme tels. `planning/resources.py`, `planning/finance.py` et `GET planning/defaults` définissent les stocks et flux, la séparation construction/réhabilitation et les enveloppes en FCFA. Les prix portent une année de référence. Une enveloppe requiert les coûts permettant de tester sa contrainte. Les valeurs financières absentes demeurent indisponibles. Les tests contrôlent les stocks, la priorité des ressources collectées, les paramètres et les plafonds.

**État et suite.** Comptabilité physique et règles de budget testées. Les prix unitaires réellement négociés, les crédits et la disponibilité effective du personnel doivent être documentés par le gestionnaire avant un arbitrage opérationnel. M09 consomme ces entrées.

### M09 · Comparaison et allocation des interventions

**Usage et livrable.** L’analyste et le décideur comparent référence, réouverture, extension dans l’existant, recrutement, redéploiement et combinaison. Les sorties comprennent les places servies, les besoins résiduels, les écarts de satisfaction et le programme quinquennal.

**Entrées, code et contrôles.** `POST jobs` de type `optimization` lance l’allocation entière de `planning/resources.py`. Les règles de priorité, plafonds par année, service minimal du donneur et hypothèses de capacité sont explicites dans le moteur. La capacité utilise le minimum de salles et de postes disponibles avec un facteur d’appariement paramétrable. Une option faisable porte son statut. Les tests vérifient conservation lors des transferts, budgets, cohérence de la demande et états indisponibles.

**État et suite.** Comparateur vérifié sous hypothèses. L’heuristique ne fournit pas de certificat d’optimalité globale. La construction d’un établissement neuf exige une localisation justifiée. Un plan local doit aussi vérifier l’appariement des ressources au sein de chaque école. M10 apporte la lecture territoriale et M11 l’arbitrage.

### M10 · Cartographie et accès

**Usage et livrable.** L’analyste et le visiteur consultent la carte et les fiches des 13 régions historiques. Le niveau géographique du résultat et la légende accompagnent la carte.

**Entrées, code et contrôles.** `web/assets/regions.json` contient les contours simplifiés et `shared.js` les associe aux indicateurs autorisés. La lecture privée passe par la ressource de données filtrée. La lecture publique passe par `/api/public/publications`. Un contrôle local a comparé les clés cartographiques à `ingestion.REGIONS` et vérifié la présence des 13 tracés fermés. Les liens de licence et de provenance figurent dans la méthodologie publique.

**État et suite.** Jointure des 13 régions vérifiée. Les contours représentent des limites administratives historiques. Le calcul d’isochrones, l’affectation à une école et les recommandations d’implantation locale sont conditionnés aux coordonnées, origines et réseaux de déplacement. La carte peut accompagner un dossier M11 ou une publication M12.

### M11 · Validation des analyses, décisions et rapports

**Usage et livrable.** Le validateur examine un calcul, puis le décideur retient une option motivée et datée. Le registre conserve son niveau d’engagement et permet l’export du dossier dans le périmètre autorisé.

**Entrées, code et contrôles.** `POST analyses/{id}/actions` gère examen, retour et validation indépendante. `POST decisions` demande une analyse validée et actuelle, une année, une option, une classification et un motif. Les décisions et analyses sont distinctes en base. `GET analyses/{id}/dependencies` relie le calcul aux décisions et diffusions autorisées. Le code se trouve dans `server/domain.py`, `server/http.py` et `workflow-screen.js`. Les essais serveur exercent la validation, l’accès aux résultats, les dépendances et les exports, et les essais de planification contrôlent le programme glissant.

**État et suite.** Registres, contrôles et rapports implémentés. Les essais techniques ne constituent aucune décision d’affectation, de recrutement ou de dépense réelle. Les contenus éligibles peuvent être préparés en M12.

### M12 · Autorisation et publication

**Usage et livrable.** Le responsable prépare le paquet figé, le validateur le vérifie et le décideur autorise sa diffusion. Le responsable peut ensuite le publier, le remplacer ou le retirer.

**Entrées, code et contrôles.** `POST publications` reçoit les versions exactes et la méthode. `POST publications/{id}/actions` traite les transitions en base. La validation métier d’une version corrigée marque les dépendances de sa version parente pour réexamen et suspend la diffusion concernée, jusqu’à maintien motivé avec avertissement, remplacement ou retrait. La route publique sert exclusivement un paquet en état publié. Les tests vérifient la séparation des acteurs, les données publiques filtrées, le réexamen d’une source et le refus de téléchargement après retrait.

**État et suite.** Cycle technique testé sur une publication de recette. Les téléchargements déjà effectués par des tiers restent hors du contrôle du serveur. La désignation de véritables responsables de diffusion et l’autorisation des contenus sont institutionnelles. M13 présente les paquets approuvés.

### M13 · Portail public

**Usage et livrable.** Le visiteur consulte le panorama national, les fiches régionales, la méthode, les indicateurs et les trajectoires effectivement diffusés. Le comparateur utilise les analyses publiées. Un état vide explique l’absence de contenu approuvé.

**Entrées, code et contrôles.** `web/index.html`, `public.js` et les routes `GET /api/public/publications`, `/{id}` et `/{id}/export` présentent la copie figée. Les graphiques sont accompagnés de tables. Une ressource retirée ou inexistante renvoie 404. La recette serveur vérifie visibilité, retrait et séparation des champs internes. Les consultations publiques lisent des résultats stockés.

**État et suite.** Portail implémenté et contrat public testé côté serveur. Le contenu initial dépend de l’état de publication de l’instance. Une validation de l’accessibilité par des utilisateurs assistés et une qualification sur les appareils cibles complètent M14.

### M14 · Exploitation et transfert

**Usage et livrable.** L’exploitant démarre le service, consulte le journal, sauvegarde la base et la restaure dans un nouvel emplacement. Les agents habilités peuvent reproduire l’import et les modèles via les commandes documentées.

**Entrées, code et contrôles.** `server/__main__.py` fournit les commandes `init`, `account`, `serve`, `backup`, `restore` et `recover`. Le serveur signale les travaux interrompus au redémarrage et permet leur relance. La restauration vérifie intégrité et clés étrangères, conserve archives et dossiers et révoque les sessions. Les tests sont répartis dans `tests/test_import.py`, `test_planning.py` et `test_server.py`. La recette de restauration compare l’empreinte de l’archive et le nombre de dossiers dans la copie rétablie.

**État et suite.** Sauvegarde et restauration testées dans un environnement isolé. La recette de charge multi-utilisateur, la supervision de l’hébergement réel, le plan de continuité, la rotation des secrets et la certification institutionnelle restent à organiser avant la mise en service gouvernementale.

## Mesures et limites de la recette technique

Une exécution de la suite `python -m unittest discover -s tests -q` sur ce poste le 17 novembre 2026 a réussi les **31 tests** en 7,695 s. La suite comprend 10 tests d’import, 10 de planification et 11 du serveur. L’exécution couvre l’import réel, des cas de cohérence de modèle, les droits et les circuits du service. Une partie des tests du serveur injecte des requêtes HTTP en mémoire. Le guide d’exploitation complète ces contrôles avec le parcours de démarrage et la recette de bout en bout.

Une mesure répétée cinq fois sur le même poste a donné une médiane de **0,361 s** pour `import_workbook` suivi de `import_demo` sur 6 636 cellules et 650 compléments. Le calcul national primaire `run_plan` avec les paramètres initiaux et le jeu déjà en mémoire a pris **0,048 s** en médiane. Ces mesures couvrent le traitement Python local, hors transfert, persistance, chiffrement réseau et rendu du navigateur.

Pour la prochaine recette locale sur le même jeu, les **objectifs techniques proposés** sont une médiane sous 2 s pour l’import et sous 1 s pour le calcul national par défaut sur cinq répétitions, à poste comparable. Avant déploiement, l’exploitant devra fixer les objectifs multi-utilisateur à partir de sa volumétrie réelle et mesurer la latence de bout en bout, les demandes concurrentes, les délais de file et la durée d’une restauration complète. Aucun résultat de charge sur un hébergement institutionnel n’est disponible dans cette recette.

Le suivi annuel consiste à archiver les nouvelles observations, comparer le millésime reçu aux projections antérieures, valider une nouvelle version, rejouer les hypothèses et examiner les publications affectées. Les deux références d’implémentation détaillent les variables, erreurs et procédures de reproduction. [Import et compléments](../ingestion/README.md) · [Prospective, ressources et interventions](../planning/README.md)

La recette en navigateur a parcouru une instance temporaire avec deux versions autorisées pour le test. Elle a vérifié la fiche du Centre et ses projections, la comparaison publique, le catalogue et le téléchargement, la prévisualisation du classeur par le gestionnaire, l’écran des habilitations, le calcul par un analyste et la réouverture des treize lignes régionales du résultat. Le portail a également été vérifié à 390 pixels de large. Une sauvegarde de l’instance de démonstration a été restaurée en répertoire temporaire avec ses 6 636 observations, ses 650 compléments et ses sessions révoquées.
