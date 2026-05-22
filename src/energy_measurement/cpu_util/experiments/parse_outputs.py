from logging import getLogger
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import polars as pl
from re import compile as re_compile, IGNORECASE

logger = getLogger(__name__)

FILENAME_RE = re_compile(
    r'cpu_util_hz(\d+)_load(\d+)_duration(\d+)\.csv$', IGNORECASE
)


def load_files(directory: Path) -> pl.DataFrame:
    """
    load_files loads all CSV files in the given directory that match the
    expected filename format:
    `cpu_util_hz{hz}_load{cpu_load}_duration{duration}.csv`,
    where `{hz}` is the frequency in Hz, `{cpu_load}` is the expected CPU
    load in %, and `{duration}` is the measurement duration.

    Args:
        directory (Path): The directory to load CSV files from.

    Raises:
        ValueError: If no valid CSV files are found in the directory.

    Returns:
        pl.DataFrame: sample (i64) | work_ns (i64) | cpu_utilization (f64) |
                      hz (i32) | cpu_load (i32) | period_ns (i64) |
                      expected_measurements (i32)
    """
    frames = []
    for path in sorted(directory.glob('cpu_util_hz*.csv')):
        match = FILENAME_RE.match(path.name)
        if not match:
            logger.warning(
                f'Skipping (unrecognized filename format): {path.name}'
            )
            continue

        hz, cpu_load, duration = (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )

        df = pl.read_csv(path)
        df = df.with_columns(
            hz=pl.lit(hz, dtype=pl.Int32),
            cpu_load=pl.lit(cpu_load, dtype=pl.Int32),
            period_ns=pl.lit(int(1e9 / hz), dtype=pl.Int64),
            expected_measurements=pl.lit(hz * duration, dtype=pl.Int32),
        )
        frames.append(df)

    if not frames:
        raise ValueError(f'No valid CSV files found in directory: {directory}')

    logger.info(f'Loaded {len(frames)} files from {directory}')
    return pl.concat(frames)


def _ns_to_ms(x: pl.Series) -> pl.Series:
    """Convert nanoseconds to milliseconds."""
    return x / 1e6


def plot_iteration_duration(df: pl.DataFrame, output_path: Path) -> None:
    """
    plot_iteration_duration creates a boxplot of iteration durations (work_ns)
    for each CPU load level.

    Args:
        df (pl.DataFrame): DataFrame containing the measurement data, expected
            to have columns:
            - cpu_load (int): The CPU load level.
            - work_ns (int): The duration of the work phase in nanoseconds for
              each iteration.
        output_path (Path): The path where the plot will be saved.
    """

    cpu_loads = sorted(df['cpu_load'].unique())
    data = [
        _ns_to_ms(df.filter(pl.col('cpu_load') == cpu_load)['work_ns'])
        for cpu_load in cpu_loads
    ]

    fig, axis = plt.subplots()
    bp = axis.boxplot(data, patch_artist=True, notch=False, showfliers=False)

    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(cpu_loads)))  # type: ignore
    for path, color in zip(bp['boxes'], colors):
        path.set_facecolor(color)

    axis.set_xticks(range(1, len(cpu_loads) + 1))
    axis.set_xticklabels(
        [f'{cpu_load}%' for cpu_load in cpu_loads], rotation=45
    )
    axis.set_xlabel('CPU load')
    axis.set_ylabel('Iteration duration (ms)')
    axis.yaxis.set_minor_locator(mticker.AutoMinorLocator())
    axis.grid(axis='y', linestyle='--', alpha=0.5)
    fig.tight_layout()

    fig.savefig(output_path / '1_iteration_duration.png', dpi=300)
    plt.close(fig)


def plot_deadline_miss_rate(df: pl.DataFrame, output_path: Path) -> None:
    """
    plot_deadline_miss_rate creates a table showing the deadline miss rate for
    each combination of CPU load and frequency. The miss rate is calculated as
    the percentage of iterations that is missing from the expected
    measurement amount.

    Args:
        df (pl.DataFrame): DataFrame containing the measurement data,
            expected to have columns:
            - cpu_load (int): The CPU load level.
            - hz (int): The frequency in Hz at which the measurements were
                taken.
            - expected_measurements (int): The expected number of measurements
                based on the duration and frequency.
        output_path (Path): The path where the table will be saved.
    """

    stats = (
        df.group_by(['cpu_load', 'hz'])
        .agg(
            [
                pl.col('expected_measurements').first(),
                pl.len().alias('actual_measurements'),
            ]
        )
        .with_columns(
            miss_rate=(
                (
                    1
                    - pl.col('actual_measurements')
                    / pl.col('expected_measurements')
                )
                * 100
            ).clip(lower_bound=0)
        )
        .sort(['cpu_load', 'hz'])
    )

    cpu_loads = sorted(stats['cpu_load'].unique().to_list())
    hz_values = sorted(stats['hz'].unique().to_list())

    table_data = []
    for load in cpu_loads:
        row = []
        for hz in hz_values:
            val = stats.filter(
                (pl.col('cpu_load') == load) & (pl.col('hz') == hz)
            )['miss_rate']
            row.append(f'{val[0]:.2f}%' if len(val) > 0 else 'N/A')
        table_data.append(row)

    fig, axis = plt.subplots()
    axis.axis('off')

    col_labels = [f'{hz} Hz' for hz in hz_values]
    row_labels = [f'{load}%' for load in cpu_loads]

    table = axis.table(
        cellText=table_data,
        rowLabels=row_labels,
        colLabels=col_labels,
        loc='center',
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(list(range(len(hz_values))))

    for (row, col), cell in table.get_celld().items():
        if row == 0 and col >= 0:
            cell.set_text_props(weight='bold')
        elif col == -1 and row > 0:
            cell.set_text_props(weight='bold')
        elif row > 0 and col >= 0:
            val_text = table_data[row - 1][col]
            if val_text != 'N/A':
                val_float = float(val_text.rstrip('%'))
                if val_float > 0:
                    cell.set_text_props(weight='bold', color='red')

    axis.set_title(
        'Deadline miss rate (% of expected measurements missing)', pad=12
    )
    fig.tight_layout()

    fig.savefig(output_path / '2_deadline_miss_rate.png', dpi=300)
    plt.close(fig)


def plot_utilization_accuracy(df: pl.DataFrame, output_path: Path) -> None:
    """
    plot_utilization_accuracy creates a line plot showing the measured CPU
    utilization against the expected CPU load for each frequency.

    Args:
        df (pl.DataFrame): DataFrame containing the measurement data,
            expected to have columns:
            - cpu_load (int): The expected CPU load level.
            - hz (int): The frequency in Hz at which the measurements were
                taken.
            - cpu_utilization (float): The measured CPU utilization for each
                iteration.
        output_path (Path): The path where the plot will be saved.
    """

    hz_values = sorted(df['hz'].unique())
    cpu_loads = sorted(df['cpu_load'].unique())

    fig, axis = plt.subplots()
    axis.plot(
        cpu_loads,
        cpu_loads,
        color='black',
        linestyle='--',
        linewidth=1,
        label='Ideal (measured = expected)',
        zorder=1,
    )

    colors = plt.cm.tab10(np.linspace(0, 1, len(hz_values)))  # type: ignore
    for hz, color in zip(hz_values, colors):
        sub = df.filter(pl.col('hz') == hz)
        stats = (
            sub.group_by('cpu_load')
            .agg(
                [
                    pl.col('cpu_utilization').mean().alias('mean'),
                    pl.col('cpu_utilization').std().alias('std'),
                    pl.col('cpu_utilization').count().alias('count'),
                ]
            )
            .sort('cpu_load')
        )
        stats = stats.with_columns(
            se=(pl.col('std') / (pl.col('count') ** 0.5))
        )

        axis.errorbar(
            stats['cpu_load'].to_numpy(),
            stats['mean'].to_numpy(),
            yerr=stats['se'].to_numpy(),
            fmt='o-',
            color=color,
            capsize=4,
            label=f'{hz} Hz',
            zorder=2,
        )

    axis.set_xlabel('Expected CPU load (%)')
    axis.set_ylabel('Measured CPU utilization (%)')
    axis.legend()
    axis.grid(linestyle='--', alpha=0.5)
    fig.tight_layout()

    fig.savefig(output_path / '3_utilization_accuracy.png', dpi=300)
    plt.close(fig)


def main() -> None:
    _cwd = Path.cwd()

    ## Expected location for measurement results ##
    data_dir = _cwd / 'outputs' / 'measurement_results'
    measurements = load_files(data_dir)

    ## Expected output location ##
    output_dir = _cwd / 'outputs' / 'parsed_results'
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_iteration_duration(measurements, output_dir)
    plot_deadline_miss_rate(measurements, output_dir)
    plot_utilization_accuracy(measurements, output_dir)


if __name__ == '__main__':
    main()
