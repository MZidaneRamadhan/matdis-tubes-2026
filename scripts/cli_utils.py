from pathlib import Path

from config.settings import DEFAULT_SCENARIO


def resolve_scenario_path(path: str | Path | None = None) -> Path:
    scenario_path = Path(path) if path is not None else DEFAULT_SCENARIO
    if not scenario_path.is_file():
        raise FileNotFoundError(f"File skenario tidak ditemukan: {scenario_path}")
    return scenario_path
