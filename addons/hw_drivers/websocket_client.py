import json
import logging
import pprint
import requests
import time
import urllib.parse
import websocket

from threading import Thread

from odoo.addons.hw_drivers import main
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.server_logger import close_server_log_sender_handler

_logger = logging.getLogger(__name__)
websocket.enableTrace(True, level=logging.getLevelName(_logger.getEffectiveLevel()))


@helpers.require_db
def send_to_controller(params, server_url=None):
    """Confirm the operation's completion by sending a response back to the Odoo server

    :param params: the parameters to send back to the server
    :param server_url: URL of the Odoo server (provided by decorator).
    """
    try:
        response = requests.post(server_url + "/iot/box/send_websocket", json={'params': params}, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        _logger.exception('Could not reach confirmation status URL: %s', server_url)


def on_error(ws, error):
    _logger.error("websocket received an error: %s", error)


@helpers.require_db
class WebsocketClient(Thread):
    channel = ""

    def on_open(self, ws):
        """
            When the client is setup, this function send a message to subscribe to the iot websocket channel
        """
        ws.send(json.dumps({
            'event_name': 'subscribe',
            'data': {
                'channels': [self.channel],
                'last': self.last_message_id,
                'identifier': helpers.get_identifier(),
            }
        }))

    def on_message(self, ws, messages):
        """Synchronously handle messages received by the websocket."""
        for message in json.loads(messages):
            _logger.debug("websocket received a message: %s", pprint.pformat(message))
            self.last_message_id = message['id']
            payload = message['message']['payload']
            if not helpers.get_identifier() in payload.get('iot_identifiers', []):
                continue

            match message['message']['type']:
                case 'iot_action':
                    for device_identifier in payload['device_identifiers']:
                        if device_identifier in main.iot_devices:
                            _logger.debug("device '%s' action started with: %s", device_identifier, pprint.pformat(payload))
                            main.iot_devices[device_identifier].action(payload)
                case 'server_clear':
                    helpers.disconnect_from_server()
                    close_server_log_sender_handler()
                case 'restart_odoo':
                    ws.close()
                    helpers.odoo_restart()
                case _:
                    continue

    def on_close(self, ws, close_status_code, close_msg):
        _logger.debug("websocket closed with status: %s", close_status_code)
        helpers.update_conf({'last_websocket_message_id': self.last_message_id})

    def __init__(self, channel, server_url=None):
        """This class will not be instantiated if no db is connected.

        :param str channel: the channel to subscribe to
        :param str server_url: URL of the Odoo server (provided by decorator).
        """
        self.channel = channel
        self.last_message_id = int(helpers.get_conf('last_websocket_message_id') or 0)
        url_parsed = urllib.parse.urlsplit(server_url)
        scheme = url_parsed.scheme.replace("http", "ws", 1)
        self.url = urllib.parse.urlunsplit((scheme, url_parsed.netloc, 'websocket', '', ''))
        super().__init__()

    def run(self):
        self.ws = websocket.WebSocketApp(self.url,
            header={"User-Agent": "OdooIoTBox/1.0"},
            on_open=self.on_open, on_message=self.on_message,
            on_error=on_error, on_close=self.on_close)

        # The IoT synchronised servers can stop in 2 ways that we need to handle:
        #  A. Gracefully:
        #   In this case a disconnection signal is sent to the IoT-box
        #   The websocket is properly closed, but it needs to be established a new connection when
        #   the server will be back.
        #
        # B. Forced/killed:
        #   In this case there is no disconnection signal received
        #
        #   This will also happen with the graceful quit as `reconnect` will trigger if the server
        #   is offline while attempting the new connection
        while True:
            try:
                run_res = self.ws.run_forever(reconnect=10)
                _logger.debug("websocket run_forever return with %s", run_res)
            except Exception:
                _logger.exception("An unexpected exception happened when running the websocket")
            _logger.debug('websocket will try to restart in 10 seconds')
            time.sleep(10)
