from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from config.settings import DEFAULT_SCENARIO
from core.graph_model import FlowParameters, GraphModel


@dataclass(frozen=True)
class Scenario:
    case_id: str
    title: str
    description: str
    graph: GraphModel
    parameters: FlowParameters


def load_scenario(path: str | Path = DEFAULT_SCENARIO) -> Scenario:
    scenario_path = Path(path)
    with scenario_path.open(encoding="utf-8") as scenario_file:
        data: Any = yaml.safe_load(scenario_file)
    if not isinstance(data, dict):
        raise ValueError(f"Format skenario tidak valid: {scenario_path}")
    graph = GraphModel.from_dict(data)
    parameters = FlowParameters.from_dict(data.get("parameters") or {})
    case_id = str(data.get("case_id", "")).strip()
    title = str(data.get("title", "")).strip()
    if not case_id or not title:
        raise ValueError("Skenario harus memiliki 'case_id' dan 'title'.")
    return Scenario(
        case_id=case_id,
        title=title,
        description=str(data.get("description", "")),
        graph=graph,
        parameters=parameters,
    )
