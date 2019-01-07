#!/usr/bin/env python

import piot
import json
import logging
from signal import pause
from gpiozero import Button
import argparse
import watchtower
import platform


def pub(topic, value):
    logger.info("publish {} {} {} {}".format(topic, args.shadow_var, args.pin, value))
    myAWSIoTMQTTClient.publish(
        topic,
        json.dumps({args.shadow_var: value, 'message': "{} {}".format(args.shadow_var, value)}), 1)
    myAWSIoTMQTTClient.publish(
        piot.iot_thing_topic(args.thing),
        piot.iot_payload('reported', {args.shadow_var: value}), 1)


def high():
    pub(args.topic, args.high_value)


def low():
    pub(args.low_topic, args.low_value)


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
    parser.add_argument("-u", "--pull_up",
                        help="If True (the default), the GPIO pin will be pulled high by default. " +
                             "In this case, connect the other side of the button to ground. " +
                             "If False, the GPIO pin will be pulled low by default. " +
                             "In this case, connect the other side of the button to 3V3",
                        default=True)
    parser.add_argument("-b", "--bounce_time",
                        help="If None (the default), no software bounce compensation will be performed. " +
                             "Otherwise, this is the length of time (in seconds) " +
                             "that the component will ignore changes in state after an initial change.",
                        type=float, default=None)
    parser.add_argument("-s", "--shadow_var", help="Shadow variable", required=True)
    parser.add_argument("-y", "--high_value", help="high value", default=1)
    parser.add_argument("-z", "--low_value", help="low value", default=0)
    parser.add_argument("-o", "--low_topic", action="store", dest="low_topic",
                        help="Low topic (defaults to topic if not assigned")
    args = parser.parse_args()

    if args.useWebsocket and args.certificatePath and args.privateKeyPath:
        parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format=piot.LOG_FORMAT)
    logger = logging.getLogger('input_pub')
    logger.addHandler(watchtower.CloudWatchLogHandler(args.thing))

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = piot.init_aws_iot_mqtt_client(args)
    myAWSIoTMQTTClient.connect()

    inp = Button(args.pin, pull_up=args.pull_up, bounce_time=args.bounce_time)

    # default low_topic to topic if not defined
    if args.low_topic is None or len(args.low_topic) == 0:
        args.low_topic = args.topic

    inp.when_pressed = high
    inp.when_released = low

    pause()
