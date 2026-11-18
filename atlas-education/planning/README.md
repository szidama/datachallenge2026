# Prospective, ressources et interventions

Les écrans privés **Prospective 2050**, **Ressources et contraintes** et **Comparateur d’interventions** utilisent le même moteur Python déterministe. Ses paramètres sont enregistrés dans le dossier de calcul. Le résultat est une simulation exploratoire destinée aux analystes et à la préparation d’un arbitrage.

| Module | Entrées et utilisateurs | Sorties et vérification | Suite du circuit |
|---|---|---|---|
| M07. Projeter les inscriptions | Analyste habilité, série du public national ou régional, cycle, méthode, millésime | 25 trajectoires annuelles de 2026 à 2050 pour le jeu initial, 3 scénarios, tests chronologiques aux horizons 1 et 2 ans, ventilation documentée | M08 pour l’offre et M11 pour l’examen métier |
| M08. Modéliser les stocks | Analyste habilité, salles recensées ou utilisables, enseignants en classe ou personnes simulées, départs, délais et hypothèses budgétaires | Inventaire, sorties et disponibilités par année. Tests de conservation des ressources, de saisie des prix et de contrôle du budget | M09 pour les interventions |
| M09. Comparer les interventions | Analyste habilité, demande M07, stocks M08 et plafonds annuels | Six politiques simulées, gains, écarts de satisfaction, coûts et programmation glissante. Résultats locaux au jalon. Tests de capacité, de transferts et de limites financières | M11 pour décision motivée, M12 pour une éventuelle diffusion |

## Exécution

Le calcul en mémoire utilise la bibliothèque standard Python. Le service privé conserve ses exécutions dans la base SQLite. Le moteur ne crée aucune table supplémentaire. Le service applique les droits sur le type de tâche, le périmètre et les consultations ultérieures. Les modes `projection` et `combined` correspondent respectivement à `projection.run` et `optimization.run`. Les deux modes exposent la même structure de résultat. Les listes d’interventions restent vides en projection seule.

`GET /api/private/planning/defaults` retourne les hypothèses par défaut du primaire. `POST /api/private/jobs` accepte `dataset_id`, `scope`, `kind`, `title` et `parameters`. Pour le calcul, `kind` vaut `projection` ou `optimization`. Le formulaire suit `GET /api/private/jobs/{id}` jusqu’à l’état final, puis lit `GET /api/private/analyses/{result_id}`. L’export JSON avec les hypothèses et la version est soumis à `report.export`. Les paramètres numériques non finis, les valeurs hors limites et les contradictions de marge sont rejetés. Un stock absent laisse l’option indisponible.

Pour reproduire localement avec des sources auxquelles vous avez accès, à partir du dossier de la plateforme :

```sh
python3 -m planning '../DONNEES_STATISTQUES_ PRESCOLAIRE ET PRIMAIRE_2016_2025_DCB.xlsx' --demo ../synthetic_demo.csv --sortie scenario-primaire.json
python3 -m unittest discover -s tests -p 'test_planning*.py' -v
```

L’option `--parametres fichier.json` applique des hypothèses explicites. `--projection` calcule uniquement les inscriptions. `--region centre` restreint la lecture analytique au Centre. La commande écrit un nouveau fichier et refuse de remplacer une sortie existante. La base web conserve en plus l’identifiant de version source, l’acteur, la date, la portée et les états de validation.

## Projection des inscriptions

Le millésime désigne l’année de fin. 2050 représente 2049/2050. L’observation initiale se termine en 2025. Avec une série et des stocks complémentaires vérifiés, `base_year` permet de rejouer le calcul à partir d’un nouveau millésime. Il faut une inscription publique au millésime choisi. Chaque exécution produit une nouvelle version analytique et peut être comparée aux observations acquises ultérieurement.

Le calcul distingue les cycles. Le référentiel provincial couvre les 6–11 ans du primaire entre 2020 et 2035. Les flux de passage, de redoublement, de migration et de sortie restent à documenter dans les projections. La série des inscriptions sert de point de départ à la demande de places publiques.

### Apprendre les trajectoires basse, centrale et haute

Le mode par défaut `ml_auto` ajuste une régression quantile séparément pour chaque cycle et périmètre autorisé. Avec dix millésimes annuels, une pente par trajectoire permet d’utiliser les variations historiques et de vérifier chaque calcul. Le modèle travaille en élèves pour que la variation reste interprétable même avec un effectif initial nul. Le niveau de départ est toujours le dernier effectif de la série. Une rupture affectant ce dernier millésime se répercute sur les trois trajectoires et mérite une vérification de la source.

Pour chaque paire d’années renseignées séparées de **h = 1 ou 2 ans**, la cible d’apprentissage est la variation **d = y(t+h) − y(t)**. Aucune valeur manquante n’est interpolée. Sur dix années complètes, on dispose de 9 paires à un an et 8 à deux ans. Ces 17 variations partagent des observations. L’ajustement exige au moins trois années de départ distinctes, suivies d’une observation à l’un des deux horizons.

1. **Durée effective.** Le prédicteur est **x(h) = (1 − φʰ)/(1 − φ) = 1 + φ + … + φʰ⁻¹**. La variation de la première année compte intégralement. Chaque variation suivante pèse φ fois la précédente. Le cumul reste borné par 1/(1 − φ), hypothèse de prudence pour une extrapolation de 25 ans. Deux hypothèses de persistance sont comparées, φ = 0,80 et φ = 0,95.
2. **Trois pentes apprises.** Pour τ = 0,20 (basse), 0,50 (centrale) et 0,80 (haute), on choisit **βτ** qui minimise **Σ ρτ(d − βτ x)**. Avec **ρτ(u) = max(τu, (τ − 1)u)**, une sous-estimation coûte davantage dans la trajectoire haute et une surestimation coûte davantage dans la basse. Pour la centrale, le coût est symétrique. Le choix de quantiles intérieurs limite la dépendance aux observations extrêmes sur ces petites séries. Comme x est positif, chaque terme vaut x × ρτ(d/x − βτ). La solution exacte est le quantile de d/x pondéré par x. Le calcul prend la première pente dont le poids cumulé atteint τ fois le poids total. Les trois pentes sont donc ordonnées.
3. **Effectif annuel.** Depuis le millésime T, **Nτ(T+h) = max(0, arrondi[y(T) + βτ x(h)])**. L’arrondi donne un nombre entier d’élèves, le plancher évite les effectifs négatifs, et les années touchées sont signalées dans `floor_applied_years`. Des profils historiques identiques peuvent donner des trajectoires confondues. Le dossier exporté contient le dernier effectif, les trois pentes, φ et les scores.
4. **Choix du modèle.** À chaque date de test, le moteur réajuste les pentes sur les seuls millésimes déjà disponibles, puis prédit les observations situées un et deux ans plus tard. Il compare la moyenne des pertes ρτ(observation − projection) sur les trois scénarios et tous les couples origine/horizon testables. Le plus petit score détermine φ en mode automatique. Une égalité ou l’absence de test départage en faveur de 0,80. L’absence de test est signalée. Les scores utilisés pour ce choix ne constituent pas une évaluation indépendante du modèle sélectionné.

Les références de comparaison sont la dernière observation, la tendance des moindres carrés ancrée au dernier millésime et cette même tendance amortie avec φ = 0,80. Pour la trajectoire centrale et les références, l’erreur absolue moyenne vaut **Σ |prévision − observation| / n** et le biais vaut **Σ (prévision − observation) / n**. Le tableau de validation donne le nombre de tests à chaque horizon. Un meilleur score sur les trois quantiles peut coexister avec une erreur centrale supérieure à la dernière observation.

Les quantiles décrivent les variations apprises à court terme. Leur extrapolation suppose que la dynamique historique reste informative, sous l’amortissement choisi. La probabilité de se situer entre les scénarios en 2050 reste inconnue. La régression et la validation suivent les principes de [Koenker et Hallock](https://www.aeaweb.org/articles?id=10.1257/jep.15.4.143) et de [Hyndman et Athanasopoulos](https://otexts.com/fpp3/toolbox.html). Le choix de la durée effective s’inspire des [tendances amorties](https://otexts.com/fpp3/exponential-smoothing.html).

Les anciens dossiers conservent les résultats de leur exécution. Pour rejouer la méthode antérieure via l’API, les valeurs explicites `auto`, `last`, `trend` et `damped` gardent la fourchette paramétrée par `scenario_spread`. La sélection historique `auto` minimise l’erreur absolue centrale des trois références.

La portée nationale s’appuie sur les valeurs de PRI02 ou PRE02 au statut Public. La méthode `demo` du primaire utilise les croisements régionaux du fichier de démonstration réconcilié avec les marges du classeur. Le mélange réglable interpole cette ventilation et un prorata des inscriptions tous statuts. `proportional` demande explicitement le prorata, y compris au préscolaire. `none` conserve uniquement les croisements collectés et validés. Le niveau national garde la série publique observée quelle que soit l’option. Un utilisateur régional ne reçoit ni marge nationale ni poids d’une autre région. Une collecte partielle remplace localement la démonstration et la marge résiduelle est distribuée aux autres régions, dans les limites des effectifs tous statuts. Les restes entiers sont attribués dans un ordre stable. Ces trois modes conservent les poids de base dans les projections.

La validation chronologique mesure une capacité de prédiction à court terme. Les perspectives à 25 ans restent conditionnelles. Le changement de part du privé, d’accès et de scolarisation n’est pas identifié séparément dans la série.

Dans les modes à poids fixes, la part d’une région est son effectif à l’année de base divisé par la somme des effectifs du périmètre à la même date. Les arrondis réconcilient chaque total national et, en cas d’inversion d’une unité, respectent l’ordre basse ≤ centrale ≤ haute dans chaque région. Une projection lancée directement sur un périmètre régional apprend sur sa propre série. Avec une série régionale générée, les variations apprises reflètent aussi les hypothèses du générateur.

### Annuaire du primaire et démographie provinciale

Le formulaire du primaire propose par défaut `regional_mix = "annuaire"` sur la base 2025. Pour les appels programmatiques, passer cette valeur explicitement. Le référentiel conserve les inventaires et les équipements de 45 provinces, les 6–11 ans de 2020 à 2035, les pages du fichier des localités et les empreintes des trois PDF. Les enseignants, salles et inscriptions du primaire proviennent des tableaux I.1 et V.4.1 de l’annuaire. Les écoles équipées sont comptées par type d’équipement. Un conflit avec un effectif régional collecté doit être résolu avant de calculer ce mode.

Pour la province *p* et l’année *t*, le poids est égal aux inscriptions publiques de 2025 multipliées par le rapport de la population des 6–11 ans en `min(t, 2035)` à celle de 2025. La répartition entière alloue la demande basse puis les deux incréments de demande par les plus forts restes. Les régions reçoivent la somme de leurs provinces. Après 2035, les parts sont figées. La population à l’horizon est laissée vide, tandis que la projection des inscriptions continue à évoluer. L’Oudalan comporte un écart entre le total imprimé de 2031 et la somme par sexe. Les deux valeurs et la page sont conservées.

La vue provinciale utilise les déficits à parc 2025 constant et sert au repérage. Le comparateur régional fait vieillir les stocks disponibles et applique les interventions annuelles. Le classeur et les captures du rapport couvrent les deux échelles.

## Ressources et financement

Les hypothèses du primaire et du préscolaire sont distinctes. Les tailles de classe illustratives sont respectivement 45 et 30 élèves. Toute modification est attachée à l’exécution. Les disponibilités initiales sont appliquées aux stocks inventoriés. Les compléments validés `salles_utilisables` et `enseignants_disponibles` sont déjà nets de disponibilité au départ. Au préscolaire, PRE08 couvre les salles publiques recensées. Le personnel reste inconnu, sauf collecte ou ratio facultatif d’élèves par personne explicitement saisi.

Chaque année, le modèle retire des salles et du personnel et peut rendre des salles temporairement indisponibles. Chaque flux est arrondi à l’entier inférieur par région et par année. Les remplacements ordinaires implicites sont nuls. Une réhabilitation transfère une salle existante du stock fermé au stock ouvert. Une salle neuve accroît l’inventaire. Un recrutement livré ajoute une personne disponible au terme du délai initial. Le taux de départ s’applique ensuite aux personnes en classe et indisponibles. Le modèle retient un délai paramétré avant les premières livraisons puis une cadence annuelle de livraisons, dans les plafonds. Les profils détaillés d’absentéisme, de qualification, de durée de vie et de chantier exigent des fichiers complémentaires.

Le service pédagogique illustratif d’un groupe vaut `max(1, floor(class_size × match_factor))`. La capacité théorique est ce service multiplié par le minimum des salles utilisables et des enseignants disponibles. `match_factor` représente une pénalité de correspondance hypothétique au niveau régional. Un inventaire par établissement reste nécessaire pour mesurer la capacité effectivement accessible. La satisfaction est la demande servie divisée par la demande modélisée. Un dénominateur nul produit une valeur indisponible.

Pour chacune des trois demandes, le nombre de groupes requis dans la région vaut **G = plafond(demande / places effectives par groupe)**. Les besoins résiduels sont **max(0, G − salles utilisables)** et **max(0, G − enseignants disponibles)**. Les plafonds arrondissent vers le haut pour accueillir le dernier groupe incomplet. La demande du scénario sélectionné alimente aussi l’allocation annuelle des interventions.

L’investissement cumulé comprend les salles neuves et les réhabilitations. Le fonctionnement de l’année comprend les rémunérations du personnel en stock et la maintenance des salles utilisables. Les enveloppes paramétrées couvrent les dépenses additionnelles. Pour le plafond de fonctionnement, chaque recrutement et chaque salle ouverte consomment un crédit annuel réservé pour le reste du scénario, y compris après un retrait ultérieur. Cette hypothèse prudente figure dans le résultat. Une absence de coût unitaire produit une dépense inconnue dès qu’il existe une quantité positive à valoriser. Les montants sont exprimés en F CFA constants de `price_year`, sans actualisation.

Pour un complément de collecte validé (`COLLECTE`), les codes financiers sont `cout_salle`, `cout_rehabilitation`, `cout_enseignant`, `cout_maintenance`, `budget_investissement` et `budget_fonctionnement`. Dans chaque région, le dernier tarif de l’exercice ou d’un exercice antérieur à la même année de prix prévaut sur le prix de scénario. Un tarif d’une autre année de prix est signalé et écarté. Une enveloppe régionale est disponible uniquement pour son exercice. Les enveloppes saisies au formulaire plafonnent le périmètre agrégé. L’algorithme vérifie simultanément les contraintes locales et agrégées, y compris les réservations récurrentes des exercices ultérieurs jusqu’en 2050. Les établissements ne se partagent pas tacitement une enveloppe régionale avec une autre région. Les montants effectivement retenus, leur cellule et version figurent dans `meta.financial_sources`. Un enseignant transféré conserve l’origine comptable de sa rémunération. Les primes de mobilité, indemnités et contraintes de qualification requièrent des collectes additionnelles.

## Allocation discrète et sensibilité

Pour chaque région et année, les décisions entières portent sur les recrutements, arrivées et départs par transfert, réhabilitations et ajouts de salles. Les variables sont positives ou nulles. Chaque sortie par transfert a une entrée dans le même périmètre. Le donneur conserve assez de personnel pour le service actuel. La somme de la demande servie et de la demande résiduelle retrouve exactement la demande projetée.

L’heuristique construit des groupes entiers dans les limites de personnel, salles, cadences, délais et budgets. Elle compare d’abord le gain de places du prochain groupe, puis le déficit relatif de couverture avant affectation, puis le nombre de moyens nécessaires. Pour les options équivalentes, elle privilégie les dépenses d’investissement les plus faibles lorsqu’elles sont connues, puis la remise en service. Les règles départagent les interventions à l’intérieur de l’année sans garantie d’optimalité globale sur 25 ans. Le statut retourné est « faisable ». Aucun écart certifié à l’optimum ni délai de solveur ne sont annoncés.

Le programme quinquennal démarre à `programme_start` et s’arrête au plus tard en 2050. Il distingue les volumes annuels programmables et les décisions administratives, qui suivent le circuit séparé du service. L’option de nouvel établissement attend des sites candidats et des coûts de site. Les temps d’accès attendent des coordonnées et une méthode de trajet documentée.

La sensibilité recalcule le besoin résiduel et les trois plus grands déficits en gardant les moyens du plan combiné fixes. Elle croise trois hypothèses de demande et trois tailles de groupe. Lorsque les observations le permettent, une table compare aussi la ventilation d’origine au prorata intégral.

## Recette

Les tests de module couvrent la séparation chronologique, les horizons, la fermeture des marges, les droits territoriaux dans le calcul, l’absence de stocks, les paramètres invalides, le maintien du service des donneurs, le respect des plafonds physiques et budgétaires, les compléments collectés et le changement de millésime. Les tests du serveur couvrent l’accès aux versions et résultats. Les prérequis de l’ouverture au public et de la validation institutionnelle restent gérés par les modules de publication.

Les principes de validation temporelle et de scénarios sont détaillés par Hyndman et Athanasopoulos. [Boîte à outils de prévision](https://otexts.com/fpp3/toolbox.html) · [Scénarios de prévision](https://otexts.com/fpp3/judgmental.html#scenario-forecasting).
