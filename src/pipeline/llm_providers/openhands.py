from logging import getLogger
from openhands.sdk import LLM, Agent, AgentContext, Conversation, Event
from openhands.sdk.conversation.base import BaseConversation
from openhands.sdk.event.llm_convertible.action import ActionEvent
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.grep import GrepTool
from pydantic import SecretStr
from src.globals.custom_exceptions import LLMCallFailed
from src.pipeline.repository_registry.registry import get_repository_profile
from src.pipeline.llm_providers.tools.check_tools import (
    CorrectnessCheckTool,
    SyntaxCheckTool,
)
from src.pipeline.llm_providers.vllm_client import TokenUsage
from src.pipeline.worker_context import (
    set_worker_index,
    worker_index_from_repo,
)
from src.settings import settings

logger = getLogger(__name__)


def _build_system_prompt_suffix() -> str:
    """
    Build the agent system prompt suffix for the configured repository.
    """

    language_name = get_repository_profile().language_name
    return (
        f'You are refactoring {language_name} code. Use file_editor to read '
        'files, make the refactoring, then write the changes back. Call '
        f'{SyntaxCheckTool.name} to verify syntax, then '
        f'{CorrectnessCheckTool.name} to verify tests pass. '
        'Call finish when done. Do NOT output any explanations, '
        'summaries, or commentary; only make file edits and tool calls.'
    )


class OpenHandsSession:
    """
    A persistent OpenHands conversation session that supports multi-turn
    interaction. Create once per unit, then call `send(message)` for each
    turn (initial task + any retry feedback messages).
    """

    def __init__(self, working_dir: str) -> None:
        set_worker_index(worker_index_from_repo(working_dir))

        self._llm = LLM(
            model=f'openai/{settings.vllm_model}',
            api_key=SecretStr('EMPTY'),
            base_url=settings.vllm_api_url,
        )
        self._tool_call_count = 0

        agent = Agent(
            llm=self._llm,
            tools=[
                Tool(name=FileEditorTool.name),
                Tool(name=TaskTrackerTool.name),
                Tool(name=GrepTool.name),
                Tool(name=SyntaxCheckTool.name),
                Tool(name=CorrectnessCheckTool.name),
            ],
            agent_context=AgentContext(
                system_message_suffix=_build_system_prompt_suffix()
            ),
        )

        def _on_event(event: Event) -> None:
            if isinstance(event, ActionEvent):
                self._tool_call_count += 1

        self._conversation: BaseConversation = Conversation(
            agent=agent,
            workspace=working_dir,
            callbacks=[_on_event],
            max_iteration_per_run=50,
            visualizer=None,
        )

    def send(self, message: str) -> TokenUsage:
        """
        Send a message to the agent and run until it finishes.

        Returns the incremental token usage for this turn.
        """
        metrics_before = self._llm.metrics
        tokens_before_in = 0
        tokens_before_out = 0
        if metrics_before and metrics_before.accumulated_token_usage:
            tokens_before_in = (
                metrics_before.accumulated_token_usage.prompt_tokens
            )
            tokens_before_out = (
                metrics_before.accumulated_token_usage.completion_tokens
            )

        self._conversation.send_message(message)
        try:
            self._conversation.run()
        except Exception as _error:
            logger.error('OpenHands session failed: %s', _error)
            raise LLMCallFailed(_error)

        metrics_after = self._llm.metrics
        if metrics_after and metrics_after.accumulated_token_usage:
            usage = metrics_after.accumulated_token_usage
            return TokenUsage(
                prompt_tokens=usage.prompt_tokens - tokens_before_in,
                completion_tokens=usage.completion_tokens - tokens_before_out,
            )

        logger.warning(
            'OpenHands LLM metrics unavailable after run, returning zero token usage.'
        )
        return TokenUsage(prompt_tokens=0, completion_tokens=0)

    @property
    def tool_call_count(self) -> int:
        return self._tool_call_count
