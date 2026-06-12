from typing import List, Literal, Optional, TypedDict


class UnitResultSchema(TypedDict):
    name: str
    file: str
    accepted: bool
    semantic_retries: int
    correctness_retries: int
    llm_calls: int
    tokens_in: int
    tokens_out: int
    tool_calls: Optional[int]


class ResultSchema(TypedDict):
    run_index: int
    experiment_type: Literal['passive', 'active']
    agent_type: Literal['agent', 'agentic']
    model: str
    language: Literal['php']
    wall_time_seconds: float
    cpu_energy_joules: float
    gpu_energy_joules: float
    total_energy_joules: float
    total_llm_calls: int
    total_tokens_in: int
    total_tokens_out: int
    total_processed_units: int
    total_accepted_units: int
    total_rejected_units: int
    acceptance_rate: float
    per_unit_results: List[UnitResultSchema]
