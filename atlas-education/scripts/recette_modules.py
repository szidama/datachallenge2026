"""Recette ordonnée M00–M14. Arrêt dès le premier échec ; reprise possible par module."""
import argparse
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
CASES = {"I": "test_import.ImportTests", "P": "test_planning.Planning",
         "S": "test_server.ServiceTests", "D": "test_defi.DefiTests"}
MODULES = [
    ("Cadrage et audit", "D.mandat I.manifest"),
    ("Socle technique", "S.http_cookie_csrf_and_public_routes"),
    ("Comptes et habilitations", "S.authentication_and_revocation S.demo_locale_mot_de_passe_et_suspension S.grants_custom_not_self S.effective_role_changes_propagate_and_protect_admin S.administrateur_direct_permissions_individuelles_et_journal S.ancien_dossier_remplace_et_controles_reserves S.consultation_sans_modification_et_portee S.refus_annulation_et_prevention_delegation S.migration_role_administrateur S.profile_personal_details S.profile_credentials"),
    ("Référentiels", "D.jointure_provinciale I.dimensions_and_periods I.missing_and_indeterminate"),
    ("Import et qualité", "D.controle_annuaire_et_population I.idempotent_normalization I.source_ips_and_rates_unchanged I.integrity_detection I.foreign_text_isolated I.demo_margins_coverage_and_lineage I.generator_reproducibility_and_sensitivity I.duplicate_partial_margins_and_provenance_rejected"),
    ("Validation des données", "S.correction_source_retournee_et_remplacement_du_portail S.ajout_collecte_et_validation S.non_auto_validation_with_custom_role"),
    ("Analyses et tableaux de bord", "S.portee_et_exports S.chart_filters_and_synthetic_origin"),
    ("Prospective 2050", "D.projections_provinciales D.compatibilite_et_conflits P.trajectories_reconcile_and_holdouts_are_chronological P.learned_quantiles_minimize_loss_without_looking_ahead P.all_demand_scenarios_drive_resource_calculation P.scope_ignores_external_observations_and_demo S.prospective_brouillon_et_territoire"),
    ("Ressources et budgets", "D.stocks_annuaire_et_simulation P.missing_inputs_remain_missing P.actual_resources_take_precedence_and_rebasing P.partial_collection_respects_margins P.collected_prices_and_ringfenced_budgets"),
    ("Simulation et optimisation", "P.conservation_and_action_availability P.constrained_allocations_and_incremental_costs P.transfer_never_spends_staff_or_construction_quota P.parameters_rejected_without_computing"),
    ("Cartographie et accès", "D.carte_historique"),
    ("Validation des analyses et décisions", "S.administrateur_circuit_independant S.job_rights_changed"),
    ("Publication", "S.publication_droit_retrait_et_dependances S.correction_puis_diffusion_du_resultat_et_du_paquet"),
    ("Portail public", "S.http_cookie_csrf_and_public_routes S.correction_source_retournee_et_remplacement_du_portail"),
    ("Exploitation et restauration", "S.version_idempotente_et_restauration"),
]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--de", type=int, choices=range(15), default=0)
    cli.add_argument("--a", type=int, choices=range(15), default=14)
    cli.add_argument("--navigateur", action="store_true", help="Inclut les parcours complets à M14")
    args = cli.parse_args()
    if args.de > args.a:
        cli.error("Le premier module doit précéder le dernier.")
    for i in range(args.de, args.a + 1):
        title, tests = MODULES[i]
        suite = unittest.TestSuite()
        for test in tests.split():
            group, name = test.split(".")
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName(f"{CASES[group]}.test_{name}"))
        print(f"M{i:02}  {title}", flush=True)
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1, failfast=True).run(suite)
        if not result.wasSuccessful():
            return 1
        if i == 14 and args.navigateur:
            for extra in (["--demo-locale"], []):
                subprocess.run([sys.executable, "tests/verifier_interface.py", *extra], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
