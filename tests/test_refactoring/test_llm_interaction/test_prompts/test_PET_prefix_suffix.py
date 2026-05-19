from tests.random_generate_functions import generate_random_string


class TestPET_PrefixSuffix:
    def test_pet_prefix_suffix_closed(self):
        from refactoring.llm_interaction.prompts.PET_prefix_suffix import (
            PET_PrefixSuffix,
        )

        prefix = generate_random_string(20)
        suffix = generate_random_string(20)
        user_prompt = generate_random_string(20)

        pet_prompt = PET_PrefixSuffix(prefix=prefix, suffix=suffix)
        applied = pet_prompt.apply(user_prompt)
        assert applied == f'{prefix} {user_prompt} {suffix}'

    def test_pet_prefix_suffix_newline(self):
        from refactoring.llm_interaction.prompts.PET_prefix_suffix import (
            PET_PrefixSuffix,
        )

        prefix = generate_random_string(20) + '\n'
        suffix = '\n' + generate_random_string(20)
        user_prompt = generate_random_string(20)

        pet_prompt = PET_PrefixSuffix(prefix=prefix, suffix=suffix)
        applied = pet_prompt.apply(user_prompt)
        assert applied == f'{prefix}{user_prompt}{suffix}'
