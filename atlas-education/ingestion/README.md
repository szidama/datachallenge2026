# Données, contrôles et compléments du prototype

Cette documentation couvre les référentiels et l’ingestion de M03–M05. Le service privé gère la conservation du fichier original, les versions en base, les corrections motivées et les transitions de validation. Le catalogue des fiches KPI est fourni par `ingestion.CATALOGUE` et dans chaque résultat d’import.

## Parcours reproductible

Depuis le répertoire `atlas-education`, utiliser l’environnement Python du projet avec openpyxl 3.1.5. Le contrôle peut se faire hors ligne.

```sh
python -m ingestion controler "../DONNEES_STATISTQUES_ PRESCOLAIRE ET PRIMAIRE_2016_2025_DCB.xlsx" --complements ../synthetic_demo.csv
python -m unittest discover -s tests -p 'test_import.py' -v
```

Le gestionnaire lit la prévisualisation privée et son rapport d’anomalies. L’enregistrement rattache la version au fichier original. Le validateur examine le dossier et motive son choix dans le circuit métier. Les contrôles mathématiques constituent des éléments pour cette décision. La publication utilise son propre circuit d’autorisation.

Les imports de classeurs suivent les intitulés de feuilles, les ancres et les axes du modèle fourni. Les colonnes de période sont lues dans la table, y compris pour une actualisation annuelle dans le même gabarit jusqu’en 2050. Une refonte des lignes ou une modification du découpage exige l’adaptation explicite du gabarit et de ses contrôles. La lecture avec et sans `data_only` permet d’examiner simultanément la formule conservée et la valeur mise en cache lors du dernier enregistrement du classeur. [Documentation officielle d’openpyxl](https://openpyxl.readthedocs.io/en/stable/tutorial.html#loading-from-a-file)

## Périmètres et unités

Les identifiants régionaux stables figurent dans `referentiel.py`. Le niveau `national` représente une marge nationale publiée. L’attribut `year=2025` désigne l’année scolaire 2024/2025. Pour la réussite au CEP, le millésime est celui de la session d’examen. Le manifeste de chaque import énumère les années effectivement présentes.

| Tableau | Cycle et contenu | Granularité disponible |
|---|---|---|
| PRE01 | Effectifs préscolaires | Région, sexe |
| PRE02 | Effectifs préscolaires | National, statut, sexe |
| PRE03 | Effectifs préscolaires | National, milieu, sexe, années de fin 2018 à 2025 |
| PRE04 | Effectifs préscolaires | National, statut, section, sexe |
| PRE05 et PRE06 | TBS et indice de parité préscolaires | Région, sexe pour le TBS |
| PRE07 et PRE08 | Structures et salles recensées | Région, statut |
| PRI01 | Effectifs primaires | Région, sexe |
| PRI02 et PRI03 | Effectifs primaires | National, statut ou milieu, sexe |
| PRI04 | Effectifs primaires | National, statut, niveau, sexe |
| PRI05 | Nouveaux inscrits au CP1 | Région, sexe |
| PRI06 à PRI09 | TBA, TBS, TAP, réussite au CEP | Région, sexe |
| PRI10 à PRI12 | Indices de parité du TBA, du TBS et du TAP | Région |
| PRI13 | Écoles primaires | Région, statut |

Les taux sont exprimés en points de pourcentage. Les indices de parité sont des rapports. Le dénominateur de chaque fiche est accessible dans le catalogue. Le TBA et le TBS peuvent dépasser 100. Les taux nationaux se lisent dans leur cellule nationale publiée. Une ventilation des taux requiert leurs dénominateurs. Les effectifs du privé et du communautaire conservent leur propre modalité.

## Contrat du lecteur

`import_workbook(path)` renvoie un dictionnaire JSON comportant les observations, le catalogue KPI, le manifeste des tables, les anomalies et les métadonnées. `import_demo(path, observed_payload)` renvoie la même enveloppe pour un CSV synthétique. `import_synthetic(path, observations)` fournit les seules lignes de ce complément. Les erreurs structurelles ou les incohérences de marge du CSV lèvent `ValueError`. Les divergences statistiques du classeur sont conservées et signalées dans le brouillon.

| Champ | Signification |
|---|---|
| `version`, `source`, `sheet`, `cell`, `table`, `id` | Empreinte SHA-256, fichier, feuille, cellule/ligne, tableau, identifiant interne stable dans une version |
| `indicator`, `cycle`, `unit` | Clé du catalogue, cycle éducatif et unité normalisée |
| `region`, `sex`, `status`, `area`, `level` | Dimensions normalisées de la valeur |
| `raw_dimensions`, `year`, `period_header` | Modalités du classeur, année de fin, en-tête d’année retenu |
| `raw`, `cached_value`, `value`, `transforms` | Valeur ou formule originale, valeur enregistrée d’une formule, valeur standardisée, traitements appliqués |
| `state`, `origin` | État de disponibilité et nature observée ou simulée |
| `method`, `generator_version`, `seed`, `official` | Méthode, version, graine, statut documentaire de chaque ligne synthétique |

Une dimension absente prend la valeur JSON `null`. Un total explicite dispose du code `total`. Une catégorie de milieu indéterminée dispose du code `indetermine`. Un zéro observé est un nombre disponible. Une cellule vide donne `state=missing` et `value=null`. Un marqueur indiquant « sans objet » donne `not_applicable`. Une donnée hors domaine donne `invalid`. Les nombres omis des tableaux ne sont pas imputés.

Les références de provenance et la clé du tableau évitent d’additionner plusieurs représentations de la même marge. Notamment, les effectifs nationaux tous statuts se retrouvent dans plusieurs tableaux. Les lignes du fichier synthétique restent dans la collection privée dédiée. Les clés de session et droits ne sont pas stockés dans le module d’import.

## Recette sur le classeur fourni

Le classeur dont l’empreinte commence par `3b87d432c99a83d9` contient 14 feuilles, 21 tableaux et 6 636 cellules de données. Le lecteur a importé 6 621 valeurs disponibles et 15 valeurs manquantes. Il a vérifié les 420 valeurs enregistrées des formules de parité du primaire. Les 18 textes étrangers isolés restent localisables dans le fichier source par cellule et empreinte. Les trois suffixes d’en-tête concernés ont été séparés de leurs années.

L’IPS du TBS du Centre pour l’année 2019/2020 figure à 1 en `PRESCOLAIRE!F77`. Le rapport des taux féminin et masculin vaut 24,4538729246 / 26,8303348961 = 0,9114263023 dans `O59/N59`. L’écart déclenche un signalement avec les deux références. La valeur enregistrée reste 1. Une révision nécessite une nouvelle version motivée et une validation.

Les dix tests d’ingestion couvrent le catalogue des dimensions, les périodes, les doublons, le réimport, les cellules manquantes, la lecture des formules, les contrôles de marges, l’anomalie IPS, l’isolement des textes, le générateur et la conservation des effectifs. Les contrôles sur les totaux se limitent aux groupes dont les composantes sont disponibles.

## Données complémentaires proposées

Le fichier fourni `synthetic_demo.csv`, version `v1.0`, contient 650 valeurs de démonstration. Chacune des 130 combinaisons région–année comprend cinq valeurs.

| Grandeur | Lignes | Construction décrite ou contrôlée |
|---|---:|---|
| Inscriptions publiques par région | 390 | Garçons, filles et total. Allocation illustrative contrainte par les marges nationales publiques et les effectifs régionaux tous statuts par sexe |
| Salles primaires publiques | 130 | Ratio illustratif de 44 à 53 élèves par salle, conservé comme hypothèse |
| Enseignants du primaire public | 130 | Ratio illustratif de 40 à 53 élèves par personne, conservé comme hypothèse |

L’import a vérifié 30 marges nationales publiques, sexe par sexe et année par année. À titre d’exemple, en 2024/2025 la somme des régions donne 2 391 345 inscriptions publiques, correspondant à la marge observée `Feuil2!L5`. Les 49 736 salles et les 51 104 enseignants figurant dans **ce même scénario synthétique** sont des hypothèses de démonstration. L’utilisation opérationnelle demande des effectifs publics croisés, un inventaire des salles fonctionnelles et une disponibilité effective des enseignants documentés avec le même millésime.

### Variante reproductible et sensibilité

Le générateur alternatif `atlas-v2.0` produit un nouveau fichier portant sa propre version. Le fichier fourni reste disponible avec sa provenance. Exemple de création au chemin de son choix, en conservant le fichier de départ.

```sh
python -m ingestion generer "../DONNEES_STATISTQUES_ PRESCOLAIRE ET PRIMAIRE_2016_2025_DCB.xlsx" /tmp/burkina-education-variante-v2.csv --poids-ecoles 0.5 --graine ATLAS-DEMO-V2
```

Pour chaque année et chaque sexe, la valeur de base est l’effectif régional tous statuts. On le multiplie par `(1 − α) + α × écoles publiques / écoles totales`. La marge publique nationale du sexe est répartie avec ces poids, avec plafonnement par l’effectif régional du même sexe puis attribution des restes. En cas d’égalité, l’ordre des identifiants régionaux départage les régions. Le poids α est une hypothèse. La taille d’une école publique peut différer de celle d’une école privée. La graine détermine le ratio qui convertit l’effectif simulé en nombre entier de salles et de personnes pour chaque région et année.

Pour la région du Centre en 2024/2025, cette variante donne 439 244 inscriptions publiques pour α = 0, 326 820 pour α = 0,5 et 155 809 pour α = 1. Les trois répartitions totalisent exactement 2 391 345 inscriptions publiques au niveau national. La variation régionale mesure ici la sensibilité au poids retenu. Elle justifie la collecte d’effectifs régionaux publics réels avant de proposer des affectations.

## Données à rechercher pour les décisions

| Question de planification | Disponibilité et lecture | Complément déterminant |
|---|---|---|
| Demande à 2050 | Trajectoires d’inscriptions et variantes sous hypothèses | Populations par âge, scolarisation et parcours à millésime comparable |
| Accès et couverture | Taux bruts publiés et capacité exploratoire | Écoles géolocalisées, origine de la demande, réseau et conditions de déplacement |
| Disparités territoriales | 13 régions historiques, effectifs et taux publiés dans chaque périmètre | Correspondances territoriales pour les nouvelles sources |
| Équité | Sexe disponible dans les effectifs, milieu observé au national | Dénominateurs des taux et croisements locaux effectivement collectés |
| Infrastructures | Écoles primaires et salles préscolaires recensées | Salles utilisables, réhabilitations, ouvertures, fermetures, échéanciers |
| Enseignants | Personnes simulées pour le primaire public | Affectation, qualification et disponibilité effective en classe |
| Parcours | Admission, scolarisation, achèvement, réussite au CEP | Entrées, promotions, redoublements et sorties par cohorte |
| Résilience | Variations historiques descriptives | Indisponibilités et déplacements documentés pour étudier une perturbation |
| Financement | Volumes physiques exploratoires | Coûts unitaires, année de prix et enveloppes d’investissement/fonctionnement |
| Gouvernance | Traçabilité à la cellule et révisions versionnées | Contre-expertise, validation métier et autorisation de diffusion |
