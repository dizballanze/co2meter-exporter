import threading
import logging
from typing import Tuple
import time

import co2meter


logger = logging.getLogger(__name__)


class MonitoringThread(threading.Thread):
    def __init__(self, monitor: co2meter.CO2monitor, interval_seconds: int = 10):
        self._monitor = monitor
        self._interval_seconds = interval_seconds
        self.latest_data: Tuple[float | None, float | None, float | None] = (
            None,
            None,
            None,
        )
        super().__init__()

    def run(self) -> None:
        while True:
            try:
                self._read_data()
            except BaseException as err:
                logger.exception("CO2 read data exception %s", (err,))
            finally:
                time.sleep(self._interval_seconds)

    def _read_data(self):
        data = self._monitor.read_data()
        if data:
            self.latest_data = data
