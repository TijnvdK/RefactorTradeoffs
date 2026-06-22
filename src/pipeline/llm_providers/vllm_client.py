from logging import getLogger
from typing import List, Tuple, TypedDict
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from src.globals.custom_exceptions import LLMCallFailed
from src.settings import settings
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

from src.pipeline.utils import parse_refactored_code

logger = getLogger(__name__)

## Types ##
History = List[ChatCompletionMessageParam]


class TokenUsage(TypedDict):
    prompt_tokens: int
    completion_tokens: int


##

_client = OpenAI(api_key='EMPTY', base_url=settings.vllm_api_url)


def _send_message_to_llm(messages: History) -> ChatCompletion:
    """
    Send a message to the LLM.

    Args:
        messages (History): The chat history with a new user message.

    Returns:
        ChatCompletion: The chat completion response from the LLM.
    """
    return _client.chat.completions.create(
        model=settings.vllm_model,
        messages=messages,
        timeout=settings.vllm_server_timeout,
    )


def chat(
    history: History, user_message: str
) -> Tuple[History, str, TokenUsage]:
    """
    Send a message to the LLM via vLLM.

    Args:
        history (History): The chat history.
        user_message (str): The message to send to the LLM.

    Raises:
        LLMCallFailed: If the LLM API call fails.
        LLMCallFailed: If there is an API connection error.
        LLMCallFailed: If the LLM API returns a status error.
        LLMCallFailed: If an unexpected error occurs.

    Returns:
        Tuple[History, str, TokenUsage]: The updated chat history, the LLM's
            reply, and the token usage. The LLM's reply is parsed to extract
            the refactored code snippet.
    """

    new_history: History = history + [
        ChatCompletionUserMessageParam(role='user', content=user_message)
    ]

    try:
        response = _send_message_to_llm(new_history)
    except APITimeoutError as _error:
        logger.error(
            'LLM API call timed out after %d seconds.',
            settings.vllm_server_timeout,
        )
        raise LLMCallFailed(_error)
    except APIConnectionError as _error:
        logger.error(
            'Failed to connect to LLM API at %s.', settings.vllm_api_url
        )
        raise LLMCallFailed(_error)
    except APIStatusError as _error:
        logger.error('LLM API returned an error: %s', _error)
        raise LLMCallFailed(_error)
    except Exception as _error:
        logger.error(
            'An unexpected error occurred during LLM API call: %s', _error
        )
        raise LLMCallFailed(_error)

    reply = response.choices[0].message.content
    if reply is None:
        logger.warning('LLM response content is None, returning empty string.')
        reply = ''
    result_code = parse_refactored_code(reply)

    new_history += [
        ChatCompletionAssistantMessageParam(role='assistant', content=reply)
    ]

    usage = response.usage
    if usage:
        token_usage = TokenUsage(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )
    else:
        logger.warning(
            'LLM response usage is None, returning zero token usage.'
        )
        token_usage = TokenUsage(prompt_tokens=0, completion_tokens=0)

    return (new_history, result_code, token_usage)
