from pathlib import Path
from typing import Any, Dict, Literal, Tuple

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from yaml import safe_load

PARENT_DIR = Path(__file__).parent


class YamlSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field, field_name) -> Tuple[Any, str, bool]:
        yaml_file = PARENT_DIR / 'config' / 'experiment.yaml'
        if not yaml_file.exists():
            return None, field_name, False
        with open(yaml_file) as f:
            data = safe_load(f) or {}
        data = {k.lower(): v for k, v in data.items()}
        return data.get(field_name), field_name, False

    def __call__(self) -> Dict[str, Any]:
        yaml_file = PARENT_DIR / 'config' / 'experiment.yaml'
        if not yaml_file.exists():
            return {}
        with open(yaml_file) as f:
            data = safe_load(f) or {}
        return {k.lower(): v for k, v in data.items()}


class Settings(BaseSettings):
    ## LLM settings ##
    vllm_model: str
    vllm_server_model_name: str
    vllm_embedding_model: str
    vllm_embedding_server_model_name: str
    vllm_api_url: str
    vllm_gpu_memory_utilization: float
    vllm_max_model_len: int
    vllm_max_tokens: int
    vllm_tensor_parallel_size: int

    ## Timeouts ##
    vllm_server_timeout: int
    semantic_check_timeout: int
    correctness_check_timeout: int

    ## Agent settings ##
    agent_type: Literal['rag', 'openhands']
    language: Literal['php']

    ## Experiment configuration ##
    run_size: int
    max_semantic_retries: int
    max_correctness_retries: int

    ## Paths ##
    job_dir: str
    path_to_repository: str
    path_to_php_cli_sif: str
    path_to_openhands_sif: str
    path_to_mariadb_sif: str
    path_to_phpunit_sif: str
    path_to_rag_vector_store: str

    ## SonarQube settings ##
    sq_url: str
    sq_token: str
    sq_project_key: str

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls),
        )


settings = Settings()  # type: ignore[call-arg]
