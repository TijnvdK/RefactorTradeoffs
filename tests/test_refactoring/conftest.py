import pytest

from src.refactoring.handlers.interface.backend_handler import BackendHandler


@pytest.fixture
def backend_handler():
    class HandlerTester(BackendHandler):
        def send_message(self, user_prompt: str) -> str:
            return f'This is mocked response to: {user_prompt}'

    return HandlerTester(
        system_prompt='system', model='model', temperature=0.5, timeout=30
    )
