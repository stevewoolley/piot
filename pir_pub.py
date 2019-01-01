#!/usr/bin/env python

import piot
import json
import logging
import platform
import watchtower
import argparse
from signal import pause
from gpiozero import MotionSensor


def pub(topic, value):
    logger.info("publish {} {} {} {}".format(topic, args.shadow_var, args.pin, value))
    myAWSIoTMQTTClient.publish(
        topic,
        json.dumps({args.shadow_var: value, 'message': "{} {}".format(args.shadow_var, value)}), 1)
    myAWSIoTMQTTClient.publish(
        piot.iot_thing_topic(args.thing),
        piot.iot_payload('reported', {args.shadow_var: value}), 1)


def motion():
    pub(args.topic, args.high_value)


def no_motion():
    if args.low_topic:
        pub(args.low_topic, args.low_value)
    else:
        pub(args.topic, args.low_value)


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
    parser.add_argument("-q", "--queue_len",
                        help="The length of the queue used to store values read from the sensor. (1 = disabled)",
                        type=int, default=1)
    parser.add_argument("-w", "--sample_rate",
                        help="The number of values to read from the device " +
                             "(and append to the internal queue) per second",
                        type=float, default=100)
    parser.add_argument("-x", "--threshold",
                        help="When the mean of all values in the internal queue rises above this value, " +
                             "the sensor will be considered active by the is_active property, " +
                             "and all appropriate events will be fired",
                        type=float, default=0.5)
    parser.add_argument("-s", "--shadow_var", help="Shadow variable", required=True)
    parser.add_argument("-y", "--high_value", help="high value", default=1)
    parser.add_argument("-z", "--low_value", help="low value", default=0)
    parser.add_argument("-o", "--low_topic", nargs='*', help="Low topic")
    args = parser.parse_args()

    if args.useWebsocket and args.certificatePath and args.privateKeyPath:
        parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('input_pub')
    logger.addHandler(watchtower.CloudWatchLogHandler(args.thing))

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = piot.init_aws_iot_mqtt_client(args)
    myAWSIoTMQTTClient.connect()

    pir = MotionSensor(args.pin, queue_len=args.queue_len, sample_rate=args.sample_rate, threshold=args.threshold)

    pir.when_motion = motion
    pir.when_no_motion = no_motion

    pause()
