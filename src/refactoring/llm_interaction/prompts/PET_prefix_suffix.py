from typing import Callable, Optional

from src.refactoring.llm_interaction.prompts.PET import PET


class PET_PrefixSuffix(PET):
    """
    Prefix/Suffix prompting involves placing specific phrases or instructions
    before (prefix) or after (suffix) the input instructions.
    """

    def __init__(
        self, prefix: Optional[str] = None, suffix: Optional[str] = None
    ):
        """
        Create an instance of the PET_PrefixSuffix class.

        Args:
            prefix (Optional[str], optional): The prefix to add to the user
                prompt. Defaults to None.
            suffix (Optional[str], optional): The suffix to add to the user
                prompt. Defaults to None.
        """
        self.prefix = prefix
        self.suffix = suffix

    def apply(self, user_prompt: str) -> str:
        if self.prefix is not None:
            self.prefix = (
                f'{self.prefix}{"" if self.prefix.endswith("\n") else " "}'
            )
        if self.suffix is not None:
            self.suffix = (
                f'{"" if self.suffix.startswith("\n") else " "}{self.suffix}'
            )

        return f'{self.prefix or ""}{user_prompt}{self.suffix or ""}'

    def apply_and_call(
        self, language_model_caller: Callable[[str], str], user_prompt: str
    ) -> str:
        prompt = self.apply(user_prompt)
        return language_model_caller(prompt)
