from tests.random_generate_functions import generate_random_string


class TestPET_ZeroShotCoT:
    def test_pet_zero_shot_cot(self):
        from llm_interaction.prompts.PET_zero_shot_CoT import PET_ZeroShotCoT

        user_prompt = generate_random_string(20)

        pet_prompt = PET_ZeroShotCoT()
        applied = pet_prompt.apply(user_prompt)
        assert applied == f"Q: {user_prompt}\n\nA: Let's think step by step."
