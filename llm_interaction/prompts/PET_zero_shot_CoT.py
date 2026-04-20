from typing import Callable

from llm_interaction.prompts.PET import PET


class PET_ZeroShotCoT(PET):
    """
    Zero-Shot Chain-of-Thought (CoT) is a variant of Chain-of-Thought (CoT) [1]
    where zero examples are given. CoT involves decomposing a problem into
    intermediate steps and solving each intermediate step before giving the
    final answer. The PET uses the phrase "Let's think step by step."
    to encourage detailed reasoning before giving a final answer [2].

    [1]: Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Brian Ichter,
    Fei Xia, Ed H. Chi, Quoc V. Le, and Denny Zhou. 2022. Chain-of-thought
    prompting elicits reasoning in large language models. In Proceedings of
    the 36th International Conference on Neural Information Processing Systems
    (NIPS '22). Curran Associates Inc., Red Hook, NY, USA, Article 1800,
    24824-24837.
    [2]: Takeshi Kojima, Shixiang Shane Gu, Machel Reid, Yutaka Matsuo, and
    Yusuke Iwasawa. 2022. Large language models are zero-shot reasoners. In
    Proceedings of the 36th International Conference on Neural Information
    Processing Systems (NIPS '22). Curran Associates Inc., Red Hook, NY, USA,
    Article 1613, 22199-22213.
    """

    def apply(self, user_prompt: str) -> str:
        return f"Q: {user_prompt}\n\nA: Let's think step by step."

    def apply_and_call(
        self, language_model_caller: Callable[[str], str], user_prompt: str
    ) -> str:
        prompt = self.apply(user_prompt)
        return language_model_caller(prompt)
