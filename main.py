from flask import Flask, Response
import co2meter
import sys

app = Flask(__name__)
mon = co2meter.CO2monitor(bypass_decrypt=True)

@app.route('/telemetry')
def metrics():
    _, co2, temperature = mon.read_data()
    response_text = f"""#TYPE co2meter_temperature_current gauge
co2meter_temperature_current {temperature}
#TYPE co2meter_co2_current gauge
co2meter_temperature_current {co2}
    """
    return Response(response_text, mimetype='text/plain')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python script.py <host> <port>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])

    app.run(host=host, port=port)

