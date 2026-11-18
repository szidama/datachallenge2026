# Atlas Éducation Burkina Faso 2050

Atlas aide à planifier les salles de classe et les affectations d’enseignants dans les 13 régions historiques du Burkina Faso. L’étude du primaire public utilise l’annuaire scolaire 2024–2025 et présente trois scénarios de demande jusqu’à l’année scolaire 2049/2050.

## Ouvrir Atlas depuis GitHub

[Ouvrir mon instance dans GitHub Codespaces](https://codespaces.new/szidama/datachallenge2026?quickstart=1)

1. Connectez-vous à GitHub, puis créez ou reprenez votre Codespace. Atlas démarre automatiquement.
2. Dans le terminal du Codespace, tapez `python3 demarrer.py acces`. La commande affiche le lien **Espace de travail**, votre identifiant administrateur, votre mot de passe et votre code temporaire. Relancez-la pour obtenir un nouveau code à son renouvellement.
3. Suivez le lien et cliquez sur **Se connecter**. Le portail public est aussi accessible depuis l’onglet **Ports**, ligne **8051 · Atlas Éducation**, avec **Ouvrir dans le navigateur**.

Chaque Codespace possède ses propres comptes, données, travaux et journal. Rouvrez le même Codespace pour les retrouver. Le port est privé par défaut. [Fonctionnement des ports GitHub Codespaces](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace)

## Ouvrir Atlas sur son ordinateur

Téléchargez et décompressez le dépôt ou clonez-le. Avec Python 3.10 ou plus récent, ouvrez un terminal dans le dossier contenant `demarrer.py` et lancez la commande de votre système. [Télécharger le dépôt en ZIP](https://github.com/szidama/datachallenge2026/archive/refs/heads/main.zip)

| Système | Démarrer | Revoir les accès administrateur dans un second terminal |
|---|---|---|
| Windows | `py -3 demarrer.py` | `py -3 demarrer.py acces` |
| macOS ou Linux | `python3 demarrer.py` | `python3 demarrer.py acces` |

Le terminal affiche les accès et ouvre le back-office. Le premier lancement installe les bibliothèques Excel incluses dans le dépôt et calcule les exemples. Avec Python et son module `venv` installés, Atlas fonctionne hors ligne dès le premier démarrage. Gardez le terminal ouvert pendant votre visite. **Ctrl+C** arrête le serveur. Relancez la même commande pour reprendre votre travail.

[Ouvrir le back-office local](http://127.0.0.1:8051/admin) · [Ouvrir le portail local](http://127.0.0.1:8051/)

## Essayer les fonctionnalités

Le compte **administrateur** dispose de tous les modules, de toutes les permissions et du périmètre national. Dans **Comparer les interventions**, modifiez une hypothèse et relancez le calcul. Dans **Habilitations et audit**, créez des comptes ou modifiez leurs droits. Sur le portail, ouvrez **Publications**, sélectionnez deux scénarios et cliquez sur **Comparer les trajectoires publiées**. Les trois éditions d’exercice du primaire public reprennent l’annuaire 2024–2025 et présentent la référence et l’intervention combinée en 2050.

Pour réaliser vous-même le circuit complet, déconnectez le compte courant et affichez les accès du profil suivant. Par exemple, `python3 demarrer.py acces atlas.validation` affiche les accès du validateur de **votre** instance. Sous Windows, utilisez `py -3` à la place de `python3`.

| Identifiant initial | Opérations à essayer |
|---|---|
| `administrateur` | Ouvrir tous les modules, gérer les comptes, les rôles et l’audit |
| `gestionnaire` | Importer le classeur, corriger et soumettre une source |
| `analyste` | Calculer les projections, comparer les interventions et exporter un dossier |
| `atlas.validation` | Valider la source, examiner les résultats et vérifier le dossier de diffusion |
| `atlas.autorisation` | Consigner la décision et autoriser la diffusion |
| `atlas.diffusion` | Préparer le dossier, publier l’édition autorisée et gérer son retrait |

Les mots de passe sont générés à la création de chaque instance. La base et les remises d’accès résident dans `.instance-atlas/`, exclu de Git. **Mon profil** permet de changer l’identifiant et le mot de passe.

## Données et documentation

- [Guide des modules et installation institutionnelle](atlas-education/README.md)
- [Lire le rapport scientifique illustré en PDF](outputs/Rapport-scientifique-Atlas-2050.pdf) ou [ouvrir sa version Word](outputs/Rapport-scientifique-Atlas-2050.docx). Ses 15 pages suivent les sept parties du défi, avec sept captures d’Atlas et un graphique des projections.
- [Consulter les résultats des trois scénarios dans Excel](outputs/Defi-2050/Atlas-primaire-public-2050.xlsx)
- [Télécharger les résultats nationaux, régionaux et provinciaux et les hypothèses](outputs/Defi-2050/)
- [Reproduire les calculs et la vérification des modules](atlas-education/README.md#défi-de-planification-à-lhorizon-2050)

Le calcul régional fait évoluer les stocks de salles et d’enseignants. Le diagnostic des 45 provinces compare la demande projetée à l’inventaire de 2025. Les projections démographiques des 6–11 ans s’arrêtent en 2035. Atlas maintient ensuite les parts territoriales de 2035.

Les [deux classeurs de démonstration](outputs/Simulations-demonstration/) utilisent des données régionales générées. Le classeur de l’étude et le rapport utilisent les stocks recensés dans l’annuaire.
