from importlib.util import find_spec
from logging import getLogger
from os import makedirs
from pathlib import Path
import sys

if find_spec('src') is None:
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))

from src.refactoring.agents.refactoring_agent import refactoring_agent
from src.globals.types import UserPrompt
from src.utils import file_to_str_gen
from src.refactoring.handlers.vllm_handler import VLLMHandler

logger = getLogger(__name__)

CODE_DIR_TO_REFACTOR = Path('./datasets/OpenContext-engineblock/src')
OUTPUT_DIR = Path('./data/OpenContext-engineblock/file_based_refactoring')
LANGUAGE_EXTENSION = '.php'

MODELS = [
    'Qwen/Qwen2.5-Coder-1.5B',
    # 'Qwen/Qwen2.5-Coder-3B',
    # 'Skywork/Skywork-SWE-32B',
    # 'mistralai/Devstral-Small-2-24B-Instruct-2512'
]


def run_refactoring_agent():
    makedirs(OUTPUT_DIR, exist_ok=True)

    llm_handler = VLLMHandler(
        gpu_memory_utilization=0.8,
        max_model_len=32768,
        max_tokens=16384,
        system_prompt='You are a green software expert. You will receive PHP code snippets and you need to refactor the code snippet to be more efficient and green, with equivalent functionality. Return only the raw refactored PHP code in a markdown code block. Do not include explanations or any text other than the PHP code itself. If the input is not valid PHP, return the original code unchanged.',
    )

    user_prompts = [
        UserPrompt(php_file=str(path), prompt=content)
        for path, content in file_to_str_gen(
            CODE_DIR_TO_REFACTOR, LANGUAGE_EXTENSION
        )
    ]

    refactoring_agent(
        llm_handler=llm_handler,
        models=MODELS,
        user_prompts=user_prompts,
        output_path=OUTPUT_DIR / 'results_refactoring_agent.json',
    )


if __name__ == '__main__':
    run_refactoring_agent()
