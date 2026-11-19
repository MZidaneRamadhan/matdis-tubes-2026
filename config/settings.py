from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = PROJECT_ROOT / "cases" / "scenarios"
DEFAULT_SCENARIO = SCENARIO_DIR / "asia_afrika.yaml"
