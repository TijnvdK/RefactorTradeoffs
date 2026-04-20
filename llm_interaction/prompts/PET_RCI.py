from typing import Callable

from globals.custom_exceptions import UnsupportedOperationError
from llm_interaction.prompts.PET import PET


class PET_RCI(PET):
    """
    Recursive Criticism and Improvement (RCI) [1] details a multi-step process.
    First, the LLM generates a response for the input instructions, and then
    the LLM is prompted again to critique this answer. Hereafter, the LLM is
    to create an improved response for the initial input instructions, based
    on the generated answer and the critique. RCI can run in multiple
    iterations, repeating the process above multiple times.

    [1]: Geunwoo Kim, Pierre Baldi, and Stephen McAleer. 2023. Language models
    can solve computer tasks. In Proceedings of the 37th International
    Conference on Neural Information Processing Systems (NIPS '23). Curran
    Associates Inc., Red Hook, NY, USA, Article 1723, 39648-39677.
    """

    def __init__(
        self,
        amount_of_rci_iterations: int,
        critique_target: str,
        rci_follow_up_system_prompt: str,
        set_system_prompt: Callable[[str], None],
    ):
        """
        Create an instance of the PET_RCI class.

        Args:
            amount_of_rci_iterations (int): The amount of iterations.
            critique_target (str): The target for the critique.
            rci_follow_up_system_prompt (str): The system prompt for the RCI follow-up.
            set_system_prompt (Callable[[str], None]): The method to set the
                system prompt of the backend handler. The RCI PET requires
                different system prompts for the different steps in the
                RCI process.
        """
        self.amount_of_rci_iterations = amount_of_rci_iterations
        self.critique_target = critique_target
        self.rci_follow_up_system_prompt = rci_follow_up_system_prompt
        self.set_system_prompt = set_system_prompt

    def apply(self, user_prompt: str) -> str:
        raise UnsupportedOperationError(
            'This PET only supports the `apply_and_call` method.'
        )

    def apply_and_call(
        self, language_model_caller: Callable[[str], str], user_prompt: str
    ) -> str:
        code = language_model_caller(user_prompt)
        for _ in range(self.amount_of_rci_iterations):
            self.set_system_prompt('')
            critique = language_model_caller(
                f'Review the following answer and find {self.critique_target} '
                f'problems with it: \n```\n{code}\n```'
            )

            self.set_system_prompt(self.rci_follow_up_system_prompt)
            modified_user_prompt = (
                f'Based on the critique:\n{critique}\n'
                f'improve the following answer:\n```\n{code}\n```'
            )

            code = language_model_caller(modified_user_prompt)
        return code
