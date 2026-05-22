from typing import List, TypedDict
from logging import getLogger
from src.energy_measurement.nvidia_gpu.nvidia_smi_wrapper import GPUEnergyMeter
from src.globals.custom_exceptions import LMCallFailed
from src.refactoring.llm_interaction.handlers.interface.backend_handler import (
    BackendHandler,
)
from re import compile as re_compile, DOTALL as re_DOTALL

logger = getLogger(__name__)


class RefactoringAgentOutput(TypedDict):
    id: str
    model: str
    energy_consumed: float
    refactored_code: str


class UserPrompt(TypedDict):
    id: str
    prompt: str


_CODE_FENCED = re_compile(
    r'(`{3,})(?:[^\n`]+\n(?!\1)|\n?)(.*?)(?:\n?\1|$)', re_DOTALL
)
_CODE_TRAILING_FENCH = re_compile(r'^(.*?)\n?```', re_DOTALL)


def parse_refactored_code(raw_output: str) -> str:
    r"""
    Parses the raw output from the LLM to extract the refactored code snippet.
    The function considers the following cases (the function extracts {code}):
    1. \`\`\`{code}\`\`\` w and w/o {language} tag
    2. \`\`\`\\n{code}\\n\`\`\` w and w/o {language} tag
    3. \`\`\`\\n{code}\`\`\` w and w/o {language} tag
    4. \`\`\`{code}\\n\`\`\` w and w/o {language} tag
    5. \`\`\`\\n{code} w and w/o {language} tag and newline
    6. {code}\\n\`\`\` w and w/o newline
    The function tries to parse on order of priority. Where case 1 has the
    highest priority and case 6 the lowest.

    Limitations:
    - The function always retrieves the first code snippet if multiple code
        snippets are present in the raw output.
    - In case 5, it will retrieve everything after the opening code fence.
    - The correctness of the function is not guaranteed with nested code fences.
    - The function returns the code exactly as is, without any additional
        formatting or cleanup.

    Args:
        raw_output (str): String with a supposed code snippet,
            possibly with code fences.

    Returns:
        str: The extracted code snippet without code fences, or the original
            string if no code fences are found.
    """

    match = _CODE_FENCED.search(raw_output)
    if match and not (
        match.group(2) == ''
        and match.start() > 0
        and match.end() == len(raw_output)
    ):
        return match.group(2)

    match = _CODE_TRAILING_FENCH.search(raw_output)
    if match:
        return match.group(1)

    return raw_output


def agent(
    llm_handler: BackendHandler,
    models: List[str],
    user_prompts: List[UserPrompt],
) -> List[RefactoringAgentOutput]:
    """
    This agent interacts with the LLM via the provided backend handler to
    refactor code snippets based on the provided inputs.

    Args:
        llm_handler (BackendHandler): The backend handler to use for
        interacting with the LLM.
        models (List[str]): The list of models to use.
        user_prompts (List[UserPrompt]): The list of user prompts to use.

    Returns:
        List[RefactoringAgentOutput]: The list of refactored code outputs.
    """

    gpu_energy_meter = GPUEnergyMeter()

    result: List[RefactoringAgentOutput] = []
    for model in models:
        llm_handler.change_model(model)
        for index, user_prompt in enumerate(user_prompts):
            logger.info(
                f'Trying to refactor prompt {index}/{len(user_prompts) - 1} with model {model}...'
            )

            id, prompt = user_prompt['id'], user_prompt['prompt']

            gpu_energy_meter.start()

            refactored_code_unparsed = ''
            try:
                refactored_code_unparsed = llm_handler.send_message(
                    f'```{prompt}```'
                )
            except LMCallFailed as e:
                logger.error(
                    'Error occurred while sending message for model '
                    f'{model}: {e}'
                )

            energy_consumed = gpu_energy_meter.stop()

            if len(refactored_code_unparsed) == 0:
                logger.warning(
                    f'No refactored code received for model {model} with '
                    f'prompt "{id}". Skipping.'
                )
                continue

            parsed_refactored_code = parse_refactored_code(
                refactored_code_unparsed
            )

            logger.info(
                f'Model {model} refactored code for prompt "{id}" '
                f'with energy consumption {energy_consumed:.4f} J.'
            )

            result.append(
                RefactoringAgentOutput(
                    id=id,
                    model=model,
                    energy_consumed=energy_consumed,
                    refactored_code=parsed_refactored_code,
                )
            )

    return result
