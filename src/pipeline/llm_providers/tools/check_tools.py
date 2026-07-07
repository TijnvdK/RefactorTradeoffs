from typing import Sequence

from openhands.sdk import (
    Action,
    ImageContent,
    Observation,
    TextContent,
    ToolDefinition,
)
from openhands.sdk.tool import ToolExecutor, register_tool
from pydantic import Field

from src.pipeline.repository_registry.registry import get_repository_profile
from src.pipeline.worker_context import worker_index_from_repo


class SyntaxCheckAction(Action):
    code: str = Field(description='Source code to validate syntactically')


class SyntaxCheckObservation(Observation):
    passed: bool
    output: str

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        status = 'PASSED' if self.passed else 'FAILED'
        return [TextContent(text=f'Syntax check {status}.\n{self.output}')]


class SyntaxCheckExecutor(
    ToolExecutor[SyntaxCheckAction, SyntaxCheckObservation]
):
    def __call__(
        self, action: SyntaxCheckAction, conversation=None
    ) -> SyntaxCheckObservation:
        passed, output = get_repository_profile().syntax_check(action.code)
        return SyntaxCheckObservation(passed=passed, output=output)


class SyntaxCheckTool(
    ToolDefinition[SyntaxCheckAction, SyntaxCheckObservation]
):
    @classmethod
    def create(cls, conv_state) -> Sequence[ToolDefinition]:
        language_name = get_repository_profile().language_name
        return [
            cls(
                description=(
                    f'Checks whether a {language_name} snippet is '
                    'syntactically valid. Call this after editing code to '
                    'verify there are no syntax errors. Returns whether the '
                    'check passed and any error messages.'
                ),
                action_type=SyntaxCheckAction,
                observation_type=SyntaxCheckObservation,
                executor=SyntaxCheckExecutor(),
            )
        ]


class CorrectnessCheckAction(Action):
    pass


class CorrectnessCheckObservation(Observation):
    passed: bool
    output: str

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        status = 'PASSED' if self.passed else 'FAILED'
        return [TextContent(text=f'Test suite {status}.\n{self.output}')]


class CorrectnessCheckExecutor(
    ToolExecutor[CorrectnessCheckAction, CorrectnessCheckObservation]
):
    def __call__(
        self, action: CorrectnessCheckAction, conversation=None
    ) -> CorrectnessCheckObservation:
        # The executor may run on a different thread than the pipeline worker
        # that claimed the isolated environment, so the thread-local worker
        # index is unreliable here. Resolve it from the conversation workspace
        # (the worker's working copy, named worker_{k}) instead.
        worker_index = None
        if conversation is not None:
            worker_index = worker_index_from_repo(
                conversation.workspace.working_dir
            )
        passed, output = get_repository_profile().correctness_check(
            worker_index
        )
        return CorrectnessCheckObservation(passed=passed, output=output)


class CorrectnessCheckTool(
    ToolDefinition[CorrectnessCheckAction, CorrectnessCheckObservation]
):
    @classmethod
    def create(cls, conv_state) -> Sequence[ToolDefinition]:
        return [
            cls(
                description=(
                    'Runs the test suite over the entire code repository. '
                    'Call this after completing a refactor to verify no '
                    'existing behaviour was broken. Returns whether all tests '
                    'passed and details of any failures.'
                ),
                action_type=CorrectnessCheckAction,
                observation_type=CorrectnessCheckObservation,
                executor=CorrectnessCheckExecutor(),
            )
        ]


register_tool(SyntaxCheckTool.name, SyntaxCheckTool)
register_tool(CorrectnessCheckTool.name, CorrectnessCheckTool)
