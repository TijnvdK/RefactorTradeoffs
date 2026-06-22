from logging import getLogger
import numpy as np
from pyRAPL import Measurement, setup as rapl_setup

logger = getLogger(__name__)


class CPUEnergyMeter:
    def __init__(self):
        """
        Create a CPUEnergyMeter instance.

        Raises:
            Exception: If there is an error initializing RAPL.
        """
        try:
            rapl_setup()
            self._meter = Measurement('cpu_energy')
        except Exception as _error:
            logger.error(f'Error initializing RAPL: {_error}')
            raise

        self._running: bool = False

    def start(self) -> None:
        """
        Start measuring CPU energy consumption. Use stop() to end the
        measurement and get the energy consumed in joules.
        """
        self._meter.begin()
        self._running = True

    def stop(self) -> float:
        """
        Stop measuring CPU energy consumption.

        Returns:
            float: The amount of Joules consumed by the CPU package since
                start() was called. If RAPL did not return a value, returns 0.0.
        """

        self._meter.end()
        self._running = False

        energy_J = self._meter.result.pkg
        if energy_J is None:
            logger.warning(
                'RAPL did not return a value for CPU energy consumption.'
            )
            return 0.0

        return np.sum(np.array(energy_J) * 1e-6)

    def is_running(self) -> bool:
        """
        Check if the energy meter is currently running.

        Returns:
            bool: True if the meter is running, False otherwise.
        """
        return self._running
