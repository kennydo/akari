import configparser
import datetime
import json
import logging
import re
from typing import Any, Dict, List, NamedTuple

import click
import influxdb
import requests

host = '192.168.1.1'
username = 'admin'
password = 'close2u'
http_id = 'TIDab64fd713c1d8016'


log = logging.getLogger(__name__)

WIFI_DEVICE_MEASUREMENT_NAME = 'wifi_device'

WifiDeviceSnapshot = NamedTuple('WifiDeviceSnapshot', [
    ('interface', str),
    ('hostname', str),
    ('mac_address', str),
    # RSSI is in in dBm, from 0 to -120
    ('rssi', int),
    ('tx_rate', int),
    ('rx_rate', int),
])


class TomatoRouter:
    def __init__(self, host: str, username: str, password: str, http_id: str):
        self.host = host
        self.username = username
        self.password = password
        self.http_id = http_id

        self._session = requests.Session()
        self._session.auth = (self.username, self.password)

    def _get_device_list_info(self) -> Dict[str, Any]:
        response = self._session.post(
            'http://{host}/update.cgi'.format(host=host),
            data={
                '_http_id':http_id,
                'exec':'devlist',
            })

        return {
            param: json.loads(value.replace("\'",'\"'))
            for param, value in re.findall(r"(?P<param>\w*) = (?P<value>.*);", response.text)
            if param != "dhcpd_static"
        }

    def get_wireless_devices(self) -> List[WifiDeviceSnapshot]:
        device_list_info = self._get_device_list_info()

        mac_addr_to_hostname = {
            lease[2]: lease[0]
            for lease in device_list_info['dhcpd_lease']
        }

        snapshots = []
        for wireless_device in device_list_info['wldev']:
            interface, mac_address, rssi, tx_rate, rx_rate, _, _ = wireless_device
            hostname = mac_addr_to_hostname.get(mac_address, '')

            snapshots.append(WifiDeviceSnapshot(
                interface=interface,
                hostname=hostname,
                mac_address=mac_address,
                rssi=rssi,
                tx_rate=tx_rate,
                rx_rate=rx_rate,
            ))

        return snapshots


def connect_to_influxdb(influxdb_config: configparser.SectionProxy) -> influxdb.InfluxDBClient:
    return influxdb.InfluxDBClient(
        host=influxdb_config['host'],
        port=int(influxdb_config['port']),
        database=influxdb_config['database'],
        username=influxdb_config['username'],
        password=influxdb_config['password'],
        ssl=influxdb_config.getboolean('use_ssl'),
    )


def connect_to_router(router_config: configparser.SectionProxy) -> TomatoRouter:
    return TomatoRouter(
        host=router_config['host'],
        username=router_config['username'],
        password=router_config['password'],
        http_id=router_config['http_id'],
    )


@click.command()
@click.option('--config', 'config_path',
              type=click.Path(exists=True, readable=True, resolve_path=True))
def emit_wifi_device_data(config_path):
    if not config_path:
        raise click.BadParameter("Config path must be supplied")

    log.info('Reading config from %s', config_path)
    config = configparser.ConfigParser()
    with open(config_path) as config_file:
        config.read_file(config_file)

    influxdb_client = connect_to_influxdb(config['influxdb'])
    router = connect_to_router(config['tomato_router'])

    formatted_utc_timestamp = '{0}Z'.format(datetime.datetime.utcnow().isoformat())

    influxdb_points = []
    for device in router.get_wireless_devices():
        data_point = {
            'timestamp': formatted_utc_timestamp,
            'measurement': WIFI_DEVICE_MEASUREMENT_NAME,
            'tags': {
                'interface': device.interface,
                'hostname': device.hostname,
                'mac_address': device.mac_address,
            },
            'fields': {
                'rssi': device.rssi,
                'tx_rate': device.tx_rate,
                'rx_rate': device.rx_rate,
            },
        }
        influxdb_points.append(data_point)

    log.info('Sending %s data points to influxdb', len(influxdb_points))
    log.debug('Logging points to influxdb: %s', influxdb_points)
    influxdb_client.write_points(influxdb_points)
