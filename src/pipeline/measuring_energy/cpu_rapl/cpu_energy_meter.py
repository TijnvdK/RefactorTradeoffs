from logging import getLogger
from threading import Event, Thread
import numpy as np
from pyRAPL import Measurement, setup as rapl_setup

logger = getLogger(__name__)


class CPUEnergyMeter:
    def __init__(self, poll_interval: int = 30):
        """
        Create a CPUEnergyMeter instance.

        Raises:
            Exception: If there is an error initializing RAPL.
        """
        try:
            rapl_setup()
            self._meter = Measurement('cpu_energy')
        except Exception as _error:
            logger.exception(f'Error initializing RAPL: {_error}')
            raise

        self._accumulated_j = 0.0
        self._poll_interval = poll_interval
        self._running: bool = False
        self._stop_event = Event()
        self._thread = None

    def start(self) -> None:
        """
        Start measuring CPU energy consumption. Use stop() to end the
        measurement and get the energy consumed in joules.
        """

        self._accumulated_j = 0.0
        self._stop_event.clear()
        self._running = True
        self._meter.begin()
        self._thread = Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        while not self._stop_event.wait(self._poll_interval):
            self._meter.end()
            pkg = self._meter.result.pkg
            if pkg is not None:
                self._accumulated_j += np.sum(np.array(pkg) * 1e-6)
            self._meter.begin()

    def stop(self) -> float:
        """
        Stop measuring CPU energy consumption.

        Returns:
            float: The amount of Joules consumed by the CPU package since
                start() was called. If RAPL did not return a value, returns 0.0.
        """

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
        self._running = False

        self._meter.end()
        pkg = self._meter.result.pkg
        if pkg is not None:
            self._accumulated_j += np.sum(np.array(pkg) * 1e-6)
        return self._accumulated_j

    def is_running(self) -> bool:
        """
        Check if the energy meter is currently running.

        Returns:
            bool: True if the meter is running, False otherwise.
        """
        return self._running
