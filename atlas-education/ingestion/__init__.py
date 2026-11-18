"""API d'ingestion. Aucun import ne rend son contenu public."""
from .demo import import_demo, import_synthetic
from .lecture import import_workbook
from .referentiel import CATALOGUE, REGIONS

__all__ = ["import_workbook","import_demo","import_synthetic","REGIONS","CATALOGUE"]
