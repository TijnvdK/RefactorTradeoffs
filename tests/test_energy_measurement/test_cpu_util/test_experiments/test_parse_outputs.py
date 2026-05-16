import pytest
import polars as pl
from pathlib import Path
from energy_measurement.cpu_util.experiments.parse_outputs import load_files

EXPECTED_SCHEMA = {
    'sample': pl.Int64,
    'work_ns': pl.Int64,
    'cpu_utilization': pl.Float64,
    'hz': pl.Int32,
    'cpu_load': pl.Int32,
    'period_ns': pl.Int64,
    'expected_measurements': pl.Int32,
}


def create_test_csv(
    directory: Path, hz: int, cpu_load: int, duration: int
) -> None:
    path = directory / f'cpu_util_hz{hz}_load{cpu_load}_duration{duration}.csv'
    path.write_text('sample,work_ns,cpu_utilization\n1,500,0.45\n2,600,0.50\n')


class TestParseOutputs:
    def test_schema(self, tmp_path: Path):
        create_test_csv(tmp_path, hz=1000, cpu_load=50, duration=10)
        df = load_files(tmp_path)
        assert df.schema == EXPECTED_SCHEMA

    def test_columns(self, tmp_path: Path):
        create_test_csv(tmp_path, hz=100, cpu_load=50, duration=10)
        df = load_files(tmp_path)

        assert df['hz'].first() == 100
        assert df['cpu_load'].first() == 50
        assert df['period_ns'].first() == 10_000_000
        assert df['expected_measurements'].first() == 1000

        assert df['sample'].to_list() == [1, 2]
        assert df['work_ns'].to_list() == [500, 600]
        assert df['cpu_utilization'].to_list() == pytest.approx([0.45, 0.50])
