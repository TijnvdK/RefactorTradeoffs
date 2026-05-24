from typing import Optional, TypedDict


class CodeRecord(TypedDict):
    model: str
    php_file: str  # Absolute path
    code: str
    energy_consumed_refactor: float
    energy_consumed_fix: Optional[float]
    amount_of_refactoring_retries: Optional[int]
    amount_of_fix_retries: Optional[int]
    error_output: Optional[str]


class UserPrompt(TypedDict):
    prompt: str
    php_file: str  # Absolute path
