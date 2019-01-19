#!/usr/bin/env python

import logging
import watchtower
import time
import platform
import argparse
import piot
from gpiozero import DigitalOutputDevice


def device(cmd):
    logger.debug("device {}".format(cmd))
    if args.pin is not None:
        if cmd < 0:
            output.on()
        elif cmd == 0:
            output.off()
        elif cmd > 0:
            output.blink(args.on_time, args.off_time, cmd)


def my_callback(client, user_data, message):
    logger.debug("callback message {} {}".format(message.topic, message.payload))
    cmd, arg, arg2 = piot.topic_parser(args.topic, message.topic)
    logger.info("callback {} {}".format(cmd, arg))
    if cmd in piot.TOPIC_STATUS_PULSE:
        device(int(arg))
    elif cmd in piot.TOPIC_STATUS_ON:
        device(-1)
    elif cmd in piot.TOPIC_STATUS_OFF:
        device(0)
    else:
        logger.warning('callback unrecognized command: {}'.format(cmd))


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
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int)
    parser.add_argument("-x", "--on_time", help="Number of seconds on", type=float, default=1)
    parser.add_argument("-y", "--off_time", help="Number of seconds off", type=float, default=1)
    parser.add_argument("-z", "--default", help="Pattern 0=off, -1=on, 1..n=number of blinks", type=int, default=1)
    args = parser.parse_args()

    if args.useWebsocket and args.certificatePath and args.privateKeyPath:
        parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format=piot.LOG_FORMAT)
    logger = logging.getLogger('output_sub')
    logger.addHandler(watchtower.CloudWatchLogHandler(args.thing))

    output = DigitalOutputDevice(args.pin)

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = piot.init_aws_iot_mqtt_client(args)
    myAWSIoTMQTTClient.connect()
    myAWSIoTMQTTClient.subscribe('{}/#'.format(args.topic), 1, my_callback)
    time.sleep(2)

    while True:
        time.sleep(1)
