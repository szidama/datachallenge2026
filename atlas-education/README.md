# Atlas Éducation · Burkina Faso 2050

Atlas Éducation est une plateforme locale de planification du primaire et du préscolaire publics. Elle met en relation les séries du classeur, des hypothèses de demande, les stocks de salles et d’enseignants et des options d’intervention. Le périmètre est celui des 13 régions historiques du classeur. L’historique se termine en 2024/2025 et la prospective produit un résultat pour chacune des 25 années scolaires suivantes.

## Ouvrir la plateforme sur ce Mac

Double-cliquez sur **Ouvrir Atlas Éducation.command**. Le lanceur démarre la démonstration sur ce poste ou retrouve le service à l’adresse **http://127.0.0.1:8050/**. Appuyez sur Entrée pour consulter le portail. Pour essayer le back-office, choisissez **1 · Analyste** ou **3 · Administrateur**. Le terminal ouvre la page de connexion et affiche l’identifiant et le mot de passe du profil choisi.

Sur l’écran de connexion de la démonstration, **Afficher les accès de l’administrateur** permet de sélectionner le fichier privé `.instance-locale/acces/administrateur.json`. Le navigateur affiche l’identifiant et le mot de passe sur ce poste. Cliquez sur **Se connecter** pour ouvrir la session.

Chaque titulaire peut ouvrir **Mon profil** dans le menu du back-office pour renseigner ou modifier son prénom, son nom de famille et son téléphone. La rubrique **Identifiant et mot de passe** demande le mot de passe actuel. Le changement de l’un de ces accès ferme les sessions du compte et invite le titulaire à se reconnecter. Le fichier de remise contient les accès initiaux. Le lanceur retrouve l’identifiant actuel et invite le titulaire à saisir le mot de passe qu’il a choisi.

Les profils de démonstration ont des fonctions distinctes. **Analyste** ouvre les tableaux, les projections et le comparateur. **Gestionnaire** prévisualise les sources, soumet des versions et prépare les corrections. **Administrateur** accède à tous les modules dans son périmètre, de l’import des données à la publication, ainsi qu’aux habilitations et au journal. Ce profil crée directement les comptes et modifie leur rôle, leurs permissions et leur territoire. Le journal enregistre chaque modification. Les contrôles indépendants de validation métier et de publication restent applicables. Les trois remises initiales sont privées au compte local du poste. Le mode démonstration réunit leurs moyens d’accès sur ce poste pour la prise en main. Pour un usage institutionnel, initialiser une instance distincte, remettre chaque accès à son titulaire et enrôler son application d’authentification.

L’instance livrée contient le classeur en brouillon, ses observations et le complément de démonstration. Les résultats calculés restent consultables dans **Programmation et rapports**. Le portail montre la carte et ses 13 fiches territoriales. Les séries apparaissent à l’issue du circuit de publication. Aucun dossier de travail de cette instance n’a reçu de validation institutionnelle.

## Trois parcours

1. **Revenir à une cellule.** Dans *Données et qualité*, choisissez la version du classeur. Ouvrez le détail d’une valeur ou l’anomalie de parité du Centre. Le dossier identifie le fichier, sa version, la feuille, la cellule et les transformations.
2. **Tester les besoins de 2050.** Dans *Comparer les interventions*, choisissez le primaire, le périmètre et un scénario de demande. Précisez la taille des groupes, les volumes annuels de salles et de postes et, si disponibles, les coûts. Le calcul conserve les paramètres, l’origine des stocks, les écarts de couverture, les besoins résiduels et la programmation quinquennale. Le préscolaire permet sa propre projection. Sa simulation de capacité exige une ventilation publique et des hypothèses de personnel adaptées.
3. **Diffuser une version.** Le gestionnaire soumet un jeu. Le validateur métier l’examine. L’analyste conserve un calcul et le fait valider. Le responsable de publication prépare un paquet, un validateur distinct le vérifie, le décideur en autorise la diffusion, puis le responsable le publie. Les décisions administratives motivées se consignent séparément. La recette de ce parcours utilise une instance de test temporaire.

## Données de démonstration proposées

Le jeu `../synthetic_demo.csv` est la proposition intégrée pour le **primaire public**. Il contient 650 lignes identifiées comme synthétiques. Chaque combinaison de région et d’année possède cinq valeurs, de 2016 à 2025.

| Donnée simulée | Volume | Contrôle ou hypothèse |
|---|---:|---|
| Inscriptions publiques régionales, garçons et filles | 260 | Valeurs entières, bornées par les inscriptions régionales tous statuts. Chaque répartition retrouve les effectifs publics nationaux du sexe considéré. |
| Inscriptions publiques régionales, total | 130 | Somme des deux sexes. |
| Salles du primaire | 130 | Stock illustratif issu des effectifs simulés et d’une hypothèse de charge. La simulation applique séparément la disponibilité. |
| Enseignants du primaire | 130 | Stock illustratif de personnes. Les hypothèses de présence et de service déterminent l’encadrement disponible. |

Chaque ligne porte sa méthode, son unité, son origine, sa version et sa graine. La version fournie est conservée. Un générateur alternatif permet de tester d’autres ventilations avec une graine et un poids réglables. Un CSV de terrain peut ensuite apporter des effectifs régionaux, des stocks réellement utilisables, des coûts et des budgets. Son intégration produit une nouvelle version à faire valider. [Dictionnaire, méthodes, exemples chiffrés et commandes de génération](ingestion/README.md)

## Démarrer sur un autre poste

Placer le classeur et le CSV à côté du dossier `atlas-education`. Depuis ce dossier, avec Python 3.12 et un environnement virtuel activé, exécuter les commandes suivantes. Sans terminal interactif, le lanceur initialise puis démarre le service et affiche ses adresses. Sur un autre système, employer le lanceur Python directement.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/demonstration.py
```

La base et les remises du mode démonstration résident dans `../.instance-locale/`, hors du répertoire web. Le service reste local après la fermeture du terminal de remise. Le démarrage d’une instance avec des titulaires distincts, les variables d’environnement, la journalisation, les sauvegardes et la restauration sont décrits dans le [guide d’exploitation](server/EXPLOITATION.md).

## Architecture et références de maintenance

La version vérifiée utilise Python 3.12.14, SQLite 3.53.1, openpyxl 3.1.5 et des modules JavaScript natifs. Le navigateur charge les styles, la carte et l’image depuis le service local. Une base transactionnelle conserve les versions, les sources, les exécutions, les habilitations et les paquets publiés. Ce monolithe évite d’imposer un serveur SIG ou une file de messages séparée pour cette volumétrie. [Cycle de maintenance Python](https://devguide.python.org/versions/) · [Module SQLite](https://docs.python.org/3/library/sqlite3.html) · [Version d’openpyxl](https://pypi.org/project/openpyxl/3.1.5/)

| Dossier | Responsabilité |
|---|---|
| `ingestion/` | Lecture des 21 tableaux, sources et dimensions normalisées, anomalies, compléments et générateur. |
| `planning/` | Modèles de demande, validations chronologiques, ressources, budgets et interventions. |
| `server/` | Authentification, accès territoriaux, versions, tâches, gouvernance, audit et deux API distinctes. |
| `web/` | Portail de consultation et espace privé. Seuls les écrans et les ressources visuelles sont servis comme fichiers statiques. |
| `tests/` | Recettes reproductibles sur le classeur, les scénarios, les droits et la publication. |
| `docs/` | Matrice de couverture, hypothèses de périmètre, critères de recette et limites. |

La carte reprend les géométries ADM1 de 2017 de la Banque mondiale diffusées par geoBoundaries, identifiant BFA-ADM1-92566538. Les contours ont été simplifiés et projetés pour l’affichage. [Source géographique](https://www.geoboundaries.org/api/current/gbOpen/BFA/ADM1/) · [Licence CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

Le diaporama présente trois photographies documentaires, redimensionnées et converties en WebP. Le cadrage varie selon l’écran. Les crédits figurent sous chaque vue et sur la page Méthodologie. [Classe de Dourtenga, KKB, 2008](https://commons.wikimedia.org/wiki/File:Dourtenga_school.JPG) · [École primaire de Gando, Helge Fahrnberger, 2005](https://commons.wikimedia.org/wiki/File:Gando-School-Burkina-Faso.JPG) · [Logements des enseignants à Gando, GandoIT, 2009](https://commons.wikimedia.org/wiki/File:Kere_teachers_accommodation.jpg) · [Licence CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)

## Défi de planification à l’horizon 2050

Dans **Comparateur d’interventions**, choisir le primaire public et la source **Annuaire du primaire 2024–2025 et démographie provinciale**. Le tableau provincial permet de classer les salles, les enseignants ou les équipements des 45 provinces historiques et d’exporter la sélection. Le comparateur régional simule la référence et les interventions sur les stocks évolutifs. Le dossier et son export conservent les sources et leurs empreintes. Le portail présente le diagnostic après publication d’une édition qui l’intègre.

Le jalon principal est 2050. La série des 6–11 ans de l’INSD s’arrête en 2035. Au-delà, la répartition utilise les derniers poids démographiques disponibles. Le diagnostic territorial à inventaire constant et le calendrier de simulation régionale ont des interprétations distinctes.

Depuis ce dossier, les commandes suivantes reproduisent les cinq jalons et la recette ordonnée. Le dernier argument du calcul désigne le dossier de sortie.

```sh
python3 scripts/reproduire_defi.py ../DONNEES*.xlsx ../outputs/Defi-2050
python3 scripts/recette_modules.py --navigateur
```

La vérification en navigateur utilise Node.js et Playwright avec Chromium. Pour une installation séparée, définir `ATLAS_PLAYWRIGHT` vers le module Playwright et, si nécessaire, `ATLAS_CHROME` vers l’exécutable Chrome. Les deux modes d’authentification sont exercés sur des bases temporaires.

Le rapport scientifique reprend les sept parties du défi en 14 pages. Depuis ce dossier, générer la version PDF avec `python3 docs/rapport-2050/rapport.py ../outputs/Defi-2050/resultats.json ../outputs/Rapport-scientifique-Atlas-2050.pdf` (ReportLab). La même commande avec une destination `.docx` produit la version Word éditable et utilise également python-docx, Pillow et pypdfium2. Les deux versions partagent les chiffres, le texte, les figures et les sources.

Les captures de référence sont incluses dans `docs/rapport-2050/figures`. Les captures de test se reproduisent avec `python3 tests/verifier_interface.py --demo-locale --captures docs/rapport-2050/figures`. La capture du circuit de diffusion est un constat daté du portail de travail. Le classeur Excel s’exporte avec `node docs/rapport-2050/classeur.mjs ../outputs/Defi-2050/resultats.json ../outputs/Defi-2050/Atlas-primaire-public-2050.xlsx` et le module `@oai/artifact-tool`.

Pour reconstruire le référentiel depuis les rapports officiels avec Poppler, utiliser `python3 scripts/importer_provinces.py primaire.pdf projections-insd.pdf localites-insd.pdf`. Les trois liens et les empreintes SHA-256 figurent dans `planning/data/provinces_2025.json`. La documentation scientifique et les résultats de la recette sont livrés dans le dossier `outputs` du projet.

## Recette et domaine d’utilisation

```sh
python -m unittest discover -s tests -v
```

Les tests couvrent le réimport, les valeurs manquantes, l’anomalie IPS, les marges nationales de la démonstration, les horizons de projection, les contraintes physiques et budgétaires, l’isolement des régions et des rôles, les changements d’habilitation, les circuits de diffusion et la restauration. La recette complémentaire en navigateur vérifie les deux espaces sur une instance jetable, dont la comparaison de deux publications et l’affichage mobile. Pour la rejouer avec Node, Playwright et Chromium installés, exécutez `python tests/verifier_interface.py`. Les variables facultatives `ATLAS_PLAYWRIGHT` et `ATLAS_CHROME` indiquent un module Playwright et un exécutable Chrome déjà installés.

Les besoins projetés portent sur les inscriptions sous hypothèses. Les effectifs publics régionaux simulés demandent une confirmation par collecte. Une implantation précise, des temps de déplacement ou une estimation démographique par cohorte exigent des données supplémentaires. La comparaison fournit des allocations entières faisables par heuristique. Une ouverture institutionnelle demande la qualification de l’hébergement et des habilitations ainsi que la validation des sources et hypothèses.

[Couverture des objectifs et des modules](docs/Cadrage-et-recette.md) · [Méthode de prospective et d’allocation](planning/README.md) · [Contrats de l’API et exploitation](server/EXPLOITATION.md)
