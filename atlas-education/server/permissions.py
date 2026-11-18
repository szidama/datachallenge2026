"""Catalogue commun aux contrôles du service, aux menus et à l’éditeur de rôles."""

GROUPS = {
    "Données et qualité": {"data.read":"Consulter les données", "data.import":"Importer un classeur", "data.edit":"Corriger et soumettre les données",
                          "data.validate":"Valider les sources"},
    "Analyses et planification": {"analysis.read":"Consulter les analyses enregistrées", "analysis.run":"Enregistrer une exploration", "projection.run":"Calculer les projections",
                                  "optimization.run":"Simuler les interventions", "analysis.validate":"Examiner et valider les résultats"},
    "Décisions et diffusion": {"report.export":"Exporter les ressources accessibles", "decision.record":"Enregistrer une décision",
                               "publication.approve":"Autoriser la diffusion", "publication.publish":"Préparer et publier",
                               "publication.withdraw":"Retirer une publication"},
    "Administration": {"users.manage":"Administrer les comptes", "roles.manage":"Gérer les rôles et habilitations",
                       "audit.read":"Consulter le journal d’audit"},
}
PERMISSIONS = {key for group in GROUPS.values() for key in group}
READ = {
    "datasets": {"data.read","data.import","data.edit","data.validate","analysis.run","analysis.validate","projection.run",
                 "optimization.run","publication.publish","publication.approve","decision.record"},
    "analyses": {"analysis.read","analysis.run","analysis.validate","projection.run","optimization.run","decision.record","publication.publish","publication.approve"},
    "decisions": {"decision.record","publication.approve","publication.publish","analysis.validate"},
    "publications": {"publication.publish","publication.approve","publication.withdraw","analysis.validate","data.validate","decision.record"},
}
MODULES = {
    "pilotage":set(), "donnees":READ["datasets"], "exploration":READ["datasets"], "prospective":{"projection.run"},
    "ressources":{"optimization.run"}, "interventions":{"optimization.run"}, "programmation":READ["analyses"],
    "validation":READ["analyses"] | READ["publications"] | {"data.edit"},
    "comptes":{"users.manage","roles.manage","audit.read"}, "profil":set(),
}

def modules_for(permissions):
    return [name for name,allowed in MODULES.items() if not allowed or allowed.intersection(permissions)]
