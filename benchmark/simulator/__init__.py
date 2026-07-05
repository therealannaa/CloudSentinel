"""Attack simulator — generates telemetry + ground-truth manifests for every
scenario in the frozen taxonomy (docs/week1/02_scenario_taxonomy.md)."""
from .specs import SCENARIO_SPECS, dev_ids, heldout_ids, all_ids  # noqa: F401
from .builder import build_scenario  # noqa: F401
