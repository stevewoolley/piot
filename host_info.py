#!/usr/bin/env python

import psutil
import platform
import argparse
import piot
import sys

if sys.platform == 'linux2':
    from gpiozero import *


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host",
                        help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
    parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
    parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
    parser.add_argument("--port", action="store", dest="port", type=int, help="Port number override")
    parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                        help="Use MQTT over WebSocket")
    parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
    parser.add_argument("--thing", help="thing name", default=platform.node().split('.')[0])
    args = parser.parse_args()

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = piot.init_aws_iot_mqtt_client(args)
    myAWSIoTMQTTClient.connect()

    # iterate through network interfaces of type == 2
    properties = {}
    for i in psutil.net_if_addrs():
        for k in psutil.net_if_addrs()[i]:
            family, address, netmask, broadcast, ptp = k
            if family == 2:
                properties[i] = address

    properties["hostname"] = platform.node()

    if sys.platform == 'darwin':
        # mac
        properties["release"] = platform.mac_ver()[0]
    elif sys.platform == 'darwin' and platform.machine().startswith('arm'):
        # raspberry pi
        properties["distribution"] = "{} {}".format(platform.linux_distribution()[0], platform.linux_distribution()[1])
        properties["hardware"] = "Pi Model {} V{}".format(pi_info().model, pi_info().pcb_revision)
    elif sys.platform == 'win32':
        # windows
        properties["distribution"] = "{} {}".format(platform.system(), platform.release())
        properties["hardware"] = platform.machine()

    myAWSIoTMQTTClient.publish(
        piot.iot_thing_topic(args.thing),
        piot.iot_payload('reported', properties), 1)
