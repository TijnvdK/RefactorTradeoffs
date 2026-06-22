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
        passed, output = correctness_check_eb()
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
