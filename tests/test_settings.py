from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from yaml import dump

from src.settings import Settings, YamlSettingsSource


class TestYamlSettingsSource:
    """Tests for the YamlSettingsSource class."""

    @pytest.fixture
    def temp_config_dir(self):
        with TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def yaml_file_with_data(self, temp_config_dir):
        config_dir = temp_config_dir / 'config'
        config_dir.mkdir()

        yaml_file = config_dir / 'experiment.yaml'
        with open(yaml_file, 'w') as _file:
            dump(
                {
                    'VllmModel': 'meta-llama/Llama-2-7b',
                    'VllmApiUrl': 'http://localhost:8000',
                    'RunSize': 5,
                    'experiment_type': 'active',
                },
                _file,
            )

        return temp_config_dir

    @pytest.fixture
    def yaml_file_empty(self, temp_config_dir):
        config_dir = temp_config_dir / 'config'
        config_dir.mkdir()

        yaml_file = config_dir / 'experiment.yaml'
        yaml_file.touch()

        return temp_config_dir

    def test_call_normal(self, yaml_file_with_data, mocker):
        mocker.patch('src.settings.PARENT_DIR', yaml_file_with_data)
        parse_result = YamlSettingsSource(Settings)()

        assert isinstance(parse_result, dict)
        assert (
            'vllmmodel' in parse_result
            and parse_result['vllmmodel'] == 'meta-llama/Llama-2-7b'
        )
        assert (
            'vllmapiurl' in parse_result
            and parse_result['vllmapiurl'] == 'http://localhost:8000'
        )
        assert 'runsize' in parse_result and parse_result['runsize'] == 5
        assert (
            'experiment_type' in parse_result
            and parse_result['experiment_type'] == 'active'
        )

    def test_call_returns_empty_dict_when_file_missing(
        self, temp_config_dir, mocker
    ):
        mocker.patch('src.settings.PARENT_DIR', temp_config_dir)
        parse_result = YamlSettingsSource(Settings)()

        assert isinstance(parse_result, dict)
        assert len(parse_result) == 0

    def test_call_returns_empty_dict_when_file_empty(
        self, yaml_file_empty, mocker
    ):
        mocker.patch('src.settings.PARENT_DIR', yaml_file_empty)
        parse_result = YamlSettingsSource(Settings)()

        assert isinstance(parse_result, dict)
        assert len(parse_result) == 0

    def test_call_returns_empty_dict_when_yaml_file_has_no_content(
        self, yaml_file_empty, mocker
    ):
        mocker.patch('src.settings.PARENT_DIR', yaml_file_empty)
        parse_result = YamlSettingsSource(Settings)()

        assert isinstance(parse_result, dict)
        assert len(parse_result) == 0

    def test_get_field_value_normal(self, yaml_file_with_data, mocker):
        mocker.patch('src.settings.PARENT_DIR', yaml_file_with_data)
        source = YamlSettingsSource(Settings)
        value, field_name, is_env_var = source.get_field_value(
            field=mocker.Mock(), field_name='vllmmodel'
        )

        assert value == 'meta-llama/Llama-2-7b'
        assert field_name == 'vllmmodel'
        assert is_env_var is False

    def test_get_field_value_field_missing(self, yaml_file_with_data, mocker):
        mocker.patch('src.settings.PARENT_DIR', yaml_file_with_data)
        source = YamlSettingsSource(Settings)
        value, field_name, is_env_var = source.get_field_value(
            field=mocker.Mock(), field_name='nonexistent_field'
        )

        assert value is None
        assert field_name == 'nonexistent_field'
        assert is_env_var is False

    def test_get_field_value_file_missing(self, temp_config_dir, mocker):
        mocker.patch('src.settings.PARENT_DIR', temp_config_dir)
        source = YamlSettingsSource(Settings)
        value, field_name, is_env_var = source.get_field_value(
            field=mocker.Mock(), field_name='vllmmodel'
        )

        assert value is None
        assert field_name == 'vllmmodel'
        assert is_env_var is False
