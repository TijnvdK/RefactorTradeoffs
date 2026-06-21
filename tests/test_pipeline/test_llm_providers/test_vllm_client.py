from openai import APIConnectionError, APIStatusError, APITimeoutError
from unittest.mock import Mock
import pytest

from src.globals.custom_exceptions import LLMCallFailed
from src.pipeline.llm_providers.vllm_client import History, chat


PATCH_TARGET = (
    'src.pipeline.llm_providers.vllm_client._client.chat.completions.create'
)


def make_mock_response(
    mocker,
    content: str | None,
    prompt_tokens=10,
    completion_tokens=5,
    include_usage=True,
):
    """Helper to build a mock ChatCompletion response."""
    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = content

    if include_usage:
        mock_response.usage = mocker.Mock(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    else:
        mock_response.usage = None

    return mock_response


class TestVLLMClient:
    def test_chat_correct(self, mocker):
        mock_response = make_mock_response(
            mocker, content='```python\nreturn 42\n```'
        )
        mocker.patch(PATCH_TARGET, return_value=mock_response)

        initial_history: History = [
            {'role': 'user', 'content': 'prior message'}
        ]
        history, code, usage = chat(initial_history, 'refactor this')

        assert code == 'return 42'
        assert usage == {'prompt_tokens': 10, 'completion_tokens': 5}

        assert history[0] == {'role': 'user', 'content': 'prior message'}
        assert history[1]['role'] == 'user'
        assert history[1]['content'] == 'refactor this'
        assert history[2]['role'] == 'assistant'
        assert history[2].get('content') == '```python\nreturn 42\n```'

    def test_chat_no_reply_causes_empty_string(self, mocker):
        mock_response = make_mock_response(mocker, content=None)
        mocker.patch(PATCH_TARGET, return_value=mock_response)

        _, code, _ = chat([], 'anything')
        assert code == ''

    def test_chat_no_usage_causes_zero_tokens(self, mocker):
        mock_response = make_mock_response(
            mocker, content='some code', include_usage=False
        )
        mocker.patch(PATCH_TARGET, return_value=mock_response)

        _, _, usage = chat([], 'anything')
        assert usage == {'prompt_tokens': 0, 'completion_tokens': 0}

    def test_api_timeout_raises_llm_call_failed(self, mocker):
        mock_request = Mock()
        mocker.patch(
            PATCH_TARGET, side_effect=APITimeoutError(request=mock_request)
        )

        with pytest.raises(LLMCallFailed):
            chat([], 'anything')

    def test_api_connection_error_raises_llm_call_failed(self, mocker):
        mock_request = Mock()
        mocker.patch(
            PATCH_TARGET, side_effect=APIConnectionError(request=mock_request)
        )

        with pytest.raises(LLMCallFailed):
            chat([], 'anything')

    def test_api_status_error_raises_llm_call_failed(self, mocker):
        mock_response = Mock()
        mocker.patch(
            PATCH_TARGET,
            side_effect=APIStatusError(
                message='API error', response=mock_response, body=None
            ),
        )

        with pytest.raises(LLMCallFailed):
            chat([], 'anything')

    def test_unexpected_exception_raises_llm_call_failed(self, mocker):
        mocker.patch(PATCH_TARGET, side_effect=RuntimeError('boom'))

        with pytest.raises(LLMCallFailed):
            chat([], 'anything')
