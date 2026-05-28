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
        try:
            nvmlInit()
            self._gpu_handles = [
                nvmlDeviceGetHandleByIndex(i)
                for i in range(nvmlDeviceGetCount())
            ]
        except NVMLError as error:
            logger.error(f'Error initializing NVML: {error}')
            raise

        self._before: List[float] = []

    def start(self) -> None:
        self._before = [
            nvmlDeviceGetTotalEnergyConsumption(handle)
            for handle in self._gpu_handles
        ]

    def stop(self) -> float:
        after = [
            nvmlDeviceGetTotalEnergyConsumption(handle)
            for handle in self._gpu_handles
        ]
        total_energy_J = (
            sum(
                after_i - before_i
                for after_i, before_i in zip(after, self._before)
            )
            / 1e3
        )
        return total_energy_J
