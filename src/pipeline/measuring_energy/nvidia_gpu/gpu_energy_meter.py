from logging import getLogger
from typing import List
from pynvml import (
    nvmlDeviceGetCount,
    nvmlDeviceGetHandleByIndex,
    NVMLError,
    nvmlDeviceGetTotalEnergyConsumption,
    nvmlInit,
)

logger = getLogger(__name__)


class GPUEnergyMeter:
    def __init__(self):
        """
        Create a GPUEnergyMeter instance.

        Raises:
            NVMLError: If there is an error initializing NVML.
        """
        try:
            nvmlInit()
            self._gpu_handles = [
                nvmlDeviceGetHandleByIndex(i)
                for i in range(nvmlDeviceGetCount())
            ]
        except NVMLError as error:
            logger.exception(f'Error initializing NVML: {error}')
            raise

        self._before: List[float] = []
        self._running: bool = False

    def start(self) -> None:
        """
        Start measuring GPU energy consumption. Use stop() to end the
        measurement and get the energy consumed in joules.
        """
        self._before = [
            nvmlDeviceGetTotalEnergyConsumption(handle)
            for handle in self._gpu_handles
        ]
        self._running = True

    def stop(self) -> float:
        """
        Stop measuring GPU energy consumption.

        Returns:
            float: The amount of joules consumed by the GPU since start() was
                called.
        """
        after = [
            nvmlDeviceGetTotalEnergyConsumption(handle)
            for handle in self._gpu_handles
        ]
        self._running = False

        total_energy_j = (
            sum(
                after_i - before_i
                for after_i, before_i in zip(after, self._before)
            )
            / 1e3
        )
        return total_energy_j

    def is_running(self) -> bool:
        """
        Check if the energy meter is currently running.

        Returns:
            bool: True if the meter is running, False otherwise.
        """
        return self._running
