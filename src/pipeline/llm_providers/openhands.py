from logging import getLogger
from pathlib import Path
from typing import Tuple
from openhands.sdk import LLM, Agent, Conversation, Event
from openhands.sdk.event.llm_convertible.action import ActionEvent
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.grep import GrepTool
from pydantic import SecretStr
from src.globals.custom_exceptions import LLMCallFailed
from src.pipeline.llm_providers.vllm_client import TokenUsage
from src.settings import settings

logger = getLogger(__name__)


def run_openhands_task(task: str, working_dir: Path) -> Tuple[int, TokenUsage]:
    llm = LLM(
        model=f'openai/{settings.vllm_model}',
        api_key=SecretStr('EMPTY'),
        base_url=settings.vllm_api_url,
    )

    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
            Tool(name=GrepTool.name),
        ],
    )

    tool_call_count = 0

    def _on_event(event: Event) -> None:
        nonlocal tool_call_count
        if isinstance(event, ActionEvent):
            tool_call_count += 1

    conversation = Conversation(
        agent=agent,
        workspace=working_dir,
        callbacks=[_on_event],
    )
    conversation.send_message(task)

    try:
        conversation.run()
    except Exception as _error:
        logger.error('OpenHands session failed: %s', _error)
        raise LLMCallFailed(_error)

    metrics = llm.metrics
    if metrics:
        usage = metrics.accumulated_token_usage
        if usage:
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        else:
            logger.warning(
                'OpenHands LLM accumulated_token_usage is None, returning zero token usage.'
            )
            token_usage = TokenUsage(prompt_tokens=0, completion_tokens=0)
    else:
        logger.warning(
            'OpenHands LLM metrics are None, returning zero token usage.'
        )
        token_usage = TokenUsage(prompt_tokens=0, completion_tokens=0)

    return (tool_call_count, token_usage)
