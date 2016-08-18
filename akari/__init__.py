import configparser
import datetime
import logging

import click
import influxdb
import phue

import akari.log_config  # noqa: F401


log = logging.getLogger(__name__)

#: The influxdb measurement names
LIGHT_MEASUREMENT_NAME = 'light'
ROOM_MEASUREMENT_NAME = 'room'


def connect_to_hue_bridge(hue_config: configparser.SectionProxy) -> phue.Bridge:
    return phue.Bridge(
        ip=hue_config['ip_address'],
        username=hue_config['username'],
    )


def connect_to_influxdb(influxdb_config: configparser.SectionProxy) -> influxdb.InfluxDBClient:
    return influxdb.InfluxDBClient(
        host=influxdb_config['host'],
        port=int(influxdb_config['port']),
        database=influxdb_config['database'],
        username=influxdb_config['username'],
        password=influxdb_config['password'],
        ssl=influxdb_config.getboolean('use_ssl'),
    )


class InfluxdbPointBuilder:
    def __init__(self, measurement: str, utc_timestamp: datetime.datetime):
        self.measurement = measurement
        self.formatted_utc_timestamp = '{0}Z'.format(utc_timestamp.isoformat())

        # `InfluxDBClient.write_points`-friendly stored data
        self.points = []

    def add_light_point(
            self,
            *,
            light_name: str,
            light_unique_id: str,
            room_name: str,
            room_class: str,
            configured_brightness: int,
            effective_brightness: int,
            is_on: bool,
            is_reachable: bool) -> None:
        """
        Note that the brightness of a bulb is in the range [1, 254].
        However, if the bulb is off, then the effective brightness is 0.

        :param light_name: the human-provided name for this bulb
        :param light_unique_id: a long string like '00:17:88:01:10:5c:8a:5d-0b'
        :param room_name: if in a room, the human-provided name of the room
        :param room_class: if in a room, the human-specified class of the room
        :param configured_brightness: how bright the bulb is set to be, if on
        :param effective_brightness: how bright the bulb actually is
        :param is_on: whether the bulb is on
        :param is_reachable: whether the bulb is connected to the bridge
        """
        self.points.append({
            'timestamp': self.formatted_utc_timestamp,
            'measurement': LIGHT_MEASUREMENT_NAME,
            'tags': {
                'light_name': light_name,
                'light_unique_id': light_unique_id,
                'room_name': room_name,
                'room_class': room_class,
            },
            'fields': {
                'configured_brightness': configured_brightness,
                'effective_brightness': effective_brightness,
                'is_on': is_on,
                'is_reachable': is_reachable,
            }
        })

    def add_room_point(
            self,
            *,
            room_name: str,
            room_class: str,
            num_lights_on: int,
            num_lights_off: int,
            num_lights_reachable: int,
            num_lights_unreachable: int) -> None:
        """
        :param room_name: the human-provided name of the room
        :param room_class: the Hue-provided room classification
        :param num_lights_on: how many lights in the room are on
        :param num_lights_off: how many lights in the room are off
        :param num_lights_reachable: how many lights in the room are reachable
        :param num_lights_unreachable: how many lights in the room are unreachable
        """
        self.points.append({
            'timestamp': self.formatted_utc_timestamp,
            'measurement': ROOM_MEASUREMENT_NAME,
            'tags': {
                'room_name': room_name,
                'room_class': room_class,
            },
            'fields': {
                'num_lights_on': num_lights_on,
                'num_lights_off': num_lights_off,
                'num_lights_reachable': num_lights_reachable,
                'num_lights_unreachable': num_lights_unreachable,
            }
        })


@click.command()
@click.option('--config', 'config_path',
              type=click.Path(exists=True, readable=True, resolve_path=True))
def main(config_path):
    if not config_path:
        raise click.BadParameter("Config path must be supplied")

    log.info('Reading config from %s', config_path)
    config = configparser.ConfigParser()
    with open(config_path) as config_file:
        config.read_file(config_file)

    hue_bridge = connect_to_hue_bridge(config['hue_bridge'])
    influxdb_client = connect_to_influxdb(config['influxdb'])

    rooms = hue_bridge.get_group()
    light_id_to_room_id = {}
    for room_id in rooms:
        for light_id in rooms[room_id]['lights']:
            light_id_to_room_id[light_id] = room_id

    lights = hue_bridge.get_light()

    point_builder = InfluxdbPointBuilder(
        'hue_light', datetime.datetime.utcnow())

    # Start building up the list of metrics
    for light_id, light in lights.items():
        if light_id in light_id_to_room_id:
            room = rooms[light_id_to_room_id[light_id]]
            room_name = room['name']
            room_class = room['class']
        else:
            room_name = None
            room_class = None

        configured_brightness = light['state']['bri']
        is_on = light['state']['on']
        is_reachable = light['state']['reachable']

        if is_on:
            effective_brightness = configured_brightness
        else:
            effective_brightness = 0

        point_builder.add_light_point(
            light_name=light['name'],
            light_unique_id=light['uniqueid'],
            room_name=room_name,
            room_class=room_class,
            configured_brightness=configured_brightness,
            effective_brightness=effective_brightness,
            is_on=is_on,
            is_reachable=is_reachable,
        )

    for room_id, room in rooms.items():
        num_lights_on = 0
        num_lights_off = 0
        num_lights_reachable = 0
        num_lights_unreachable = 0

        for light_id in room['lights']:
            light = lights[light_id]

            if light['state']['on']:
                num_lights_on += 1
            else:
                num_lights_off += 1

            if light['state']['reachable']:
                num_lights_reachable += 1
            else:
                num_lights_unreachable += 1

        point_builder.add_room_point(
            room_name=room['name'],
            room_class=room['class'],
            num_lights_on=num_lights_on,
            num_lights_off=num_lights_off,
            num_lights_reachable=num_lights_reachable,
            num_lights_unreachable=num_lights_unreachable,
        )

    log.info('Sending %s data points to influxdb', len(point_builder.points))
    log.debug('Logging points to influxdb: %s', point_builder.points)
    influxdb_client.write_points(point_builder.points)
