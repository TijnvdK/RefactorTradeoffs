from os import makedirs
from pathlib import Path
from logging import (
    basicConfig as logging_basicConfig,
    INFO as logging_INFO,
    getLogger,
)
from typing import List
from src.globals.types import UserPrompt
from src.refactoring.agents.fix_agent import fix_agent
from src.refactoring.agents.refactoring_agent import refactoring_agent
from src.refactoring.agents.verification_agent import verification_agent
from src.refactoring.handlers.vllm_handler import VLLMHandler
from src.utils import file_to_str_gen
from src.refactoring.verifiers.engineblock_verifier import (
    engineblock_verifier,
)

logger = getLogger(__name__)

###
# Experiment Configurations

##
CWD = Path.cwd()

# TARGET_REPOSITORY is the root of the repository that needs to be refactored.
TARGET_REPOSITORY = CWD / 'datasets/OpenContext-engineblock'
# FOLDER_TO_REFACTOR is the folder in the repository that is to be refactored.
# This can be the same as `TARGET_REPOSITORY` if the entire repository is to
# be refactored.
FOLDER_TO_REFACTOR = TARGET_REPOSITORY / 'src'
# PROGRAMMING_LANGUAGE is the programming language of the code snippets that
# are being refactored.
PROGRAMMING_LANGUAGE = 'PHP'
# OUTPUT_DIR is the directory where the results of all agents will be stored.
OUTPUT_DIR = CWD / 'data/OpenContext-engineblock/file_based_refactoring'

###

###
# Runners


def run_refactoring_agent(models: List[str]) -> None:
    system_prompt = """
You are a green software expert. You will receive PHP code snippets and you
need to refactor the code snippet to be more efficient and green, with
equivalent functionality. Return only the raw refactored PHP code in a markdown
code block. Do not include explanations or any text other than the PHP code
itself. If the input is not valid PHP, return the original code unchanged.
""".strip()

    llm_handler = VLLMHandler(
        gpu_memory_utilization=0.8,
        max_model_len=32768,
        max_tokens=16384,
        timeout=300,
        system_prompt=system_prompt,
    )

    user_prompts = [
        UserPrompt(php_file=str(path), prompt=content)
        for path, content in file_to_str_gen(
            FOLDER_TO_REFACTOR, PROGRAMMING_LANGUAGE
        )
    ]

    refactoring_agent(
        llm_handler=llm_handler,
        models=models,
        user_prompts=user_prompts,
        output_path=OUTPUT_DIR / 'results_refactoring_agent.json',
    )


def run_verification_agent(input_file: Path, iteration: int) -> bool:
    return verification_agent(
        input_file,
        OUTPUT_DIR / f'results_verification_agent_iteration_{iteration}.json',
        TARGET_REPOSITORY,
        engineblock_verifier,
    )


def run_fix_agent(model: str, iteration: int) -> None:
    system_prompt = """
You are a expert software developer. You should only return the refactored
code, without any explanations or comments.
""".strip()

    llm_handler = VLLMHandler(
        gpu_memory_utilization=0.8,
        max_model_len=32768,
        max_tokens=16384,
        system_prompt=system_prompt,
    )

    llm_handler.change_model(model)

    input_path = OUTPUT_DIR / f'results_fix_agent_iteration_{iteration}.json'

    fix_agent(
        llm_handler=llm_handler,
        input_path=input_path,
        output_path=OUTPUT_DIR
        / f'results_fix_agent_iteration_{iteration}.json',
    )


###


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description='Run specific agents')

    parser.add_argument(
        '--agent',
        type=str,
        choices=['refactoring', 'verification', 'fix'],
        required=True,
        help='The agent to run',
    )

    parser.add_argument(
        '--model',
        type=str,
        required=True,
        help='The model to use for the refactoring and fix agents',
    )

    iteration_help = """
The iteration number for verification and fix agents. The zero value is only
applicable for the verification agent, and it indicates that the input file
is the output of the refactoring agent.
""".strip()
    parser.add_argument(
        '--iteration',
        type=int,
        default=0,
        help=iteration_help,
    )

    args = parser.parse_args()

    logging_basicConfig(
        level=logging_INFO, format='%(asctime)s - %(levelname)s - %(message)s'
    )

    makedirs(OUTPUT_DIR, exist_ok=True)

    if args.agent == 'refactoring':
        run_refactoring_agent([args.model])
    elif args.agent == 'verification':
        if args.iteration == 0:
            input_file = OUTPUT_DIR / 'results_refactoring_agent.json'
        else:
            input_file = (
                OUTPUT_DIR
                / f'results_fix_agent_iteration_{args.iteration}.json'
            )
        all_passed = run_verification_agent(input_file, args.iteration)
        if all_passed:
            logger.info(
                'All code snippets passed verification in iteration '
                f'{args.iteration}.'
            )
        else:
            logger.info(
                'Some code snippets failed verification in iteration '
                f'{args.iteration}. Check the output file for details.'
            )
    elif args.agent == 'fix':
        run_fix_agent(args.model, args.iteration)
