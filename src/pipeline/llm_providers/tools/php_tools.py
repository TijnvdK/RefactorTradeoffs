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

from src.pipeline.code_checks.correctness_checks import correctness_check_eb
from src.pipeline.code_checks.semantic_checks import semantic_check_php
from src.pipeline.worker_context import worker_index_from_repo


class SemanticCheckPhpAction(Action):
    code: str = Field(description='PHP code to validate syntactically')


class SemanticCheckPhpObservation(Observation):
    passed: bool
    output: str

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        status = 'PASSED' if self.passed else 'FAILED'
        return [TextContent(text=f'Syntax check {status}.\n{self.output}')]


class SemanticCheckPhpExecutor(
    ToolExecutor[SemanticCheckPhpAction, SemanticCheckPhpObservation]
):
    def __call__(
        self, action: SemanticCheckPhpAction, conversation=None
    ) -> SemanticCheckPhpObservation:
        passed, output = semantic_check_php(action.code)
        return SemanticCheckPhpObservation(passed=passed, output=output)


class SemanticCheckPhpTool(
    ToolDefinition[SemanticCheckPhpAction, SemanticCheckPhpObservation]
):
    @classmethod
    def create(cls, conv_state) -> Sequence[ToolDefinition]:
        return [
            cls(
                description=(
                    'Checks whether a PHP snippet is syntactically valid. '
                    'Call this after editing PHP code to verify there are no syntax errors. '
                    'Returns whether the check passed and any error messages.'
                ),
                action_type=SemanticCheckPhpAction,
                observation_type=SemanticCheckPhpObservation,
                executor=SemanticCheckPhpExecutor(),
            )
        ]


class CorrectnessCheckEbAction(Action):
    pass


class CorrectnessCheckEbObservation(Observation):
    passed: bool
    output: str

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        status = 'PASSED' if self.passed else 'FAILED'
        return [TextContent(text=f'EB test suite {status}.\n{self.output}')]


class CorrectnessCheckEbExecutor(
    ToolExecutor[CorrectnessCheckEbAction, CorrectnessCheckEbObservation]
):
    def __call__(
        self, action: CorrectnessCheckEbAction, conversation=None
    ) -> CorrectnessCheckEbObservation:
        # The executor may run on a different thread than the pipeline worker
        # that claimed the isolated environment, so the thread-local worker
        # index is unreliable here. Resolve it from the conversation workspace
        # (the worker's working copy, named worker_{k}) instead.
        worker_index = None
        if conversation is not None:
            worker_index = worker_index_from_repo(
                conversation.workspace.working_dir
            )
        passed, output = correctness_check_eb(worker_index)
        return CorrectnessCheckEbObservation(passed=passed, output=output)


class CorrectnessCheckEbTool(
    ToolDefinition[CorrectnessCheckEbAction, CorrectnessCheckEbObservation]
):
    @classmethod
    def create(cls, conv_state) -> Sequence[ToolDefinition]:
        return [
            cls(
                description=(
                    'Runs the EB test suite over the entire code repository. '
                    'Call this after completing a refactor to verify no existing behaviour was broken. '
                    'Returns whether all tests passed and details of any failures.'
                ),
                action_type=CorrectnessCheckEbAction,
                observation_type=CorrectnessCheckEbObservation,
                executor=CorrectnessCheckEbExecutor(),
            )
        ]


register_tool(SemanticCheckPhpTool.name, SemanticCheckPhpTool)
register_tool(CorrectnessCheckEbTool.name, CorrectnessCheckEbTool)
