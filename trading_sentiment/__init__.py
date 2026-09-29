"""Pure, unit-tested logic behind the Databricks notebooks (no Spark or Databricks imports at module level)."""

CATALOG = "workspace"
SCHEMA = "sec_filings"


def table(name: str, catalog: str = CATALOG, schema: str = SCHEMA) -> str:
    """Fully qualified Unity Catalog table name, e.g. ``workspace.sec_filings.fact_risk``."""
    return f"{catalog}.{schema}.{name}"
