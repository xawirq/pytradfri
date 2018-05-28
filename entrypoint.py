#!/usr/bin/env python3
"""
This is an example of how the pytradfri-library can be used.
To run the script, do the following:
$ pip3 install pytradfri
$ Download this file (example_sync.py)
$ python3 example_sync.py <IP>
Where <IP> is the address to your IKEA gateway. The first time
running you will be asked to input the 'Security Code' found on
the back of your IKEA gateway.
"""

# Hack to allow relative import above top level package
import sys
import os
folder = os.path.dirname(os.path.abspath(__file__))  # noqa
sys.path.insert(0, os.path.normpath("%s/.." % folder))  # noqa
import json

from pytradfri import Gateway
from pytradfri.api.libcoap_api import APIFactory
from pytradfri.error import PytradfriError
from pytradfri.util import load_json, save_json

import uuid
import argparse
import threading
import time

import paho.mqtt.client as mqtt

# The callback for when the client receives a CONNACK response from the server.


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(userdata['topic'])


def on_message(client, userdata, msg):
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    devices_command = userdata['gateway'].get_devices()
    devices_commands = userdata['api'](devices_command)
    devices = {dev.name: dev
               for dev
               in userdata['api'](devices_commands)
               if dev.has_light_control}
    cmd = json.loads(msg.payload.decode('utf-8'))
    if cmd['light'] in devices:
        userdata['api'](devices[cmd['light']]
                        .light_control.set_dimmer(cmd['level']))


CONFIG_FILE = 'tradfri_standalone_psk.conf'


parser = argparse.ArgumentParser()
parser.add_argument('host', metavar='IP', type=str,
                    help='IP Address of your Tradfri gateway')
parser.add_argument('-K', '--key', dest='key', required=False,
                    help='Security code found on your Tradfri gateway')

parser.add_argument('-m', '--mqtt-host', required=True)
parser.add_argument('-u', '--user', required=True)
parser.add_argument('-p', '--password', required=True)
parser.add_argument('-t', '--topic', required=True)

args = parser.parse_args()


if args.host not in load_json(CONFIG_FILE) and args.key is None:
    print("Please provide the 'Security Code' on the back of your "
          "Tradfri gateway:", end=" ")
    key = input().strip()
    if len(key) != 16:
        raise PytradfriError("Invalid 'Security Code' provided.")
    else:
        args.key = key


def observe(api, device):
    def callback(updated_device):
        light = updated_device.light_control.lights[0]
        print("Received message for: %s" % light)

    def err_callback(err):
        print(err)

    def worker():
        api(device.observe(callback, err_callback, duration=120))

    threading.Thread(target=worker, daemon=True).start()
    print('Sleeping to start observation task')
    time.sleep(1)


def main():
    # Assign configuration variables.
    # The configuration check takes care they are present.
    conf = load_json(CONFIG_FILE)

    try:
        identity = conf[args.host].get('identity')
        psk = conf[args.host].get('key')
        api_factory = APIFactory(host=args.host, psk_id=identity, psk=psk)
    except KeyError:
        identity = uuid.uuid4().hex
        api_factory = APIFactory(host=args.host, psk_id=identity)

        try:
            psk = api_factory.generate_psk(args.key)
            print('Generated PSK: ', psk)

            conf[args.host] = {'identity': identity,
                               'key': psk}
            save_json(CONFIG_FILE, conf)
        except AttributeError:
            raise PytradfriError("Please provide the 'Security Code' on the "
                                 "back of your Tradfri gateway using the "
                                 "-K flag.")

    api = api_factory.request

    gateway = Gateway()

    client = mqtt.Client(
        userdata={"api": api, "gateway": gateway, 'topic': args.topic})
    client.username_pw_set(args.user, args.password)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(args.mqtt_host, 1883, 60)

    client.loop_forever()


main()
