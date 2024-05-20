from dataclasses import dataclass
import argparse
import logging

from aiohttp import web
from aiomisc.service.aiohttp import AIOHTTPService
from aiomisc.service.base import Service
from atc_mi_interface import general_format, atc_mi_advertising_format
from bleak import BleakScanner
import aiomisc
import co2meter


logger = logging.getLogger(__name__)


@dataclass
class Metric:
    name: str
    type: str
    value: float


class BleakTempReaderService(Service):
    __required__ = ("metrics",)

    async def callback(self, device, advertisement_data):
        format_label, adv_data = atc_mi_advertising_format(advertisement_data)
        if not adv_data:
            return
        atc_mi_data = general_format.parse(adv_data)
        if atc_mi_data.atc1441_format:
            data = atc_mi_data.atc1441_format[0]
            logger.info("%s: temp=%d humidity=%d", data.MAC, data.temperature, data.humidity)
            if data.MAC not in self._registry:
                self._registry[data.MAC] = {
                    "temperature": Metric(name='ble_temperature{deviceID="' + data.MAC + '"}', type="gauge", value=data.temperature),
                    "humidity": Metric(name='ble_humidity{deviceID="' + data.MAC + '"}', type="gauge", value=data.humidity),
                }
                self.metrics.extend([self._registry[data.MAC]["temperature"], self._registry[data.MAC]["humidity"]])

            self._registry[data.MAC]["temperature"].value = data.temperature
            self._registry[data.MAC]["humidity"].value = data.humidity

    async def start(self):
        self._registry = {}
        self.scanner = BleakScanner(detection_callback=self.callback)
        await self.scanner.start()

    async def stop(self):
        await self.scanner.stop()


class TelemetryService(AIOHTTPService):

    __required__ = ("co2monitor",)

    async def telemetry_handler(self, request):
        _, co2, temperature = self.co2monitor.read_data()
        self._temperature_metric.value = temperature
        self._co2_metric.value = co2

        response_lines = []
        for metric in self.metrics:
            response_lines.append(f"#TYPE {metric.name} {metric.type}")
            response_lines.append(f"{metric.name} {metric.value}")
        return web.Response(text="\n".join(response_lines))

    async def create_application(self):
        self._temperature_metric = Metric(
            name="co2meter_temperature_current",
            type="gauge",
            value=None,
        )
        self._co2_metric = Metric(
            name="co2meter_co2_current",
            type="gauge",
            value=None,
        )
        self.metrics.extend([self._temperature_metric, self._co2_metric])

        app = web.Application()
        app.router.add_get('/telemetry', self.telemetry_handler)
        return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an aiohttp service.")
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the HTTP server on.')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the HTTP server on.')
    args = parser.parse_args()

    mon = co2meter.CO2monitor(bypass_decrypt=True)
    mon.start_monitoring(interval=1)

    metrics = []
    with aiomisc.entrypoint(
        TelemetryService(address=args.host, port=args.port, co2monitor=mon, metrics=metrics),
        BleakTempReaderService(metrics=metrics),
    ) as loop:
        loop.run_forever()
