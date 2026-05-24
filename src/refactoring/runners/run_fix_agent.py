from importlib.util import find_spec
from logging import getLogger
from os import makedirs
from pathlib import Path
import sys

from src.refactoring.agents.fix_agent import fix_agent

if find_spec('src') is None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

from src.refactoring.handlers.vllm_handler import VLLMHandler

logger = getLogger(__name__)

CODE_DIR_TO_REFACTOR = Path('./datasets/OpenConext-engineblock/src')
OUTPUT_DIR = Path('./datasets/OpenConext-engineblock-refactored')
LANGUAGE_EXTENSION = '.php'

MODEL = 'Qwen/Qwen2.5-Coder-1.5B'

ITERATION = 0


def run_fix_agent():
    makedirs(OUTPUT_DIR, exist_ok=True)

    llm_handler = VLLMHandler(
        gpu_memory_utilization=0.8,
        max_model_len=32768,
        max_tokens=16384,
        system_prompt='You are a expert software developer. You should only return the refactored code, without any explanations or comments.',
    )

    llm_handler.change_model(MODEL)

    if ITERATION == 0:
        input_path = OUTPUT_DIR / 'results_refactoring_agent.json'
    else:
        input_path = (
            OUTPUT_DIR / f'results_fix_agent_iteration_{ITERATION - 1}.json'
        )

    fix_agent(
        llm_handler=llm_handler,
        input_path=input_path,
        output_path=OUTPUT_DIR
        / f'results_fix_agent_iteration_{ITERATION}.json',
    )


if __name__ == '__main__':
    run_fix_agent()
