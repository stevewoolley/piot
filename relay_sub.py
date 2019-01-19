#!/usr/bin/env python

import logging
import time
import argparse
import watchtower
import platform
import piot
from gpiozero import OutputDevice


def device(cmd):
    logger.debug("device {}".format(cmd))
    if args.pin is not None:
        if cmd < 0:
            output.on()
        elif cmd == 0:
            output.off()
        elif cmd > 0:
            output.on()
            time.sleep(args.pulse_delay)
            output.off()


def callback(client, user_data, message):
    logger.debug("callback message {} {}".format(message.topic, message.payload))
    cmd, arg, arg2 = piot.topic_parser(args.topic, message.topic)
    logger.info("callback {} {}".format(cmd, arg))
    if cmd in piot.TOPIC_STATUS_PULSE:
        device(1)
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
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-d", "--pulse_delay", help="length of pulse in seconds", type=float, default=0.5)
    parser.add_argument("-a", "--active_high",
                        help="If True, the on() method will set the GPIO to HIGH. " +
                             "If False(the default), the on() method will set the GPIO to LOW " +
                             "(the off() method always does the opposite).",
                        type=bool, default=False)
    parser.add_argument("-i", "--initial_value",
                        help="If False (the default), the device will be off initially. " +
                             "If None, the device will be left in whatever state the pin is found " +
                             "in when configured for output (warning: this can be on). " +
                             "If True, the device will be switched on initially.",
                        type=bool, default=False)
    args = parser.parse_args()

    if args.useWebsocket and args.certificatePath and args.privateKeyPath:
        parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format=piot.LOG_FORMAT)
    logger = logging.getLogger('relay_sub')
    logger.addHandler(watchtower.CloudWatchLogHandler(args.thing))

    output = OutputDevice(args.pin, args.active_high, args.initial_value)

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = piot.init_aws_iot_mqtt_client(args)
    myAWSIoTMQTTClient.connect()
    myAWSIoTMQTTClient.subscribe('{}/#'.format(args.topic), 1, callback)
    time.sleep(2)

    while True:
        time.sleep(1)
