#!/usr/bin/env python

import json
import logging
from signal import pause
from gpiozero import Button
import argparse
import watchtower
import platform
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient


def iot_thing_topic(thing):
    return "$aws/things/{}/shadow/update".format(thing)


def iot_payload(target, doc):
    return json.dumps({'state': {target: doc}})


def high():
    logger.info("publish high {} {} {} {}".format(args.topic, args.shadow_var, args.pin, args.high_value))
    myAWSIoTMQTTClient.publish(
        args.topic,
        json.dumps(
            {
                args.shadow_var: args.high_value,
                'message': "{} {}".format(args.shadow_var, args.high_value)
            }
        ),
        1
    )
    myAWSIoTMQTTClient.publish(
        iot_thing_topic(args.thing),
        iot_payload(
            'reported',
            {args.shadow_var: args.high_value}
        ),
        1
    )


def low():
    logger.info("publish low {} {} {} {}".format(args.low_topic, args.shadow_var, args.pin, args.low_value))
    myAWSIoTMQTTClient.publish(
        args.low_topic,
        json.dumps(
            {
                args.shadow_var: args.low_value,
                'message': "{} {}".format(args.shadow_var, args.low_value)
            }
        ),
        1
    )
    myAWSIoTMQTTClient.publish(
        iot_thing_topic(args.thing),
        iot_payload(
            'reported',
            {args.shadow_var: args.low_value}
        ),
        1
    )


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
                        type=bool, default=True)
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

    port = args.port

    if args.useWebsocket and args.certificatePath and args.privateKeyPath:
        parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    # Port defaults
    if args.useWebsocket and not args.port:  # When no port override for WebSocket, default to 443
        port = 443
    if not args.useWebsocket and not args.port:  # When no port override for non-WebSocket, default to 8883
        port = 8883

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('input_pub')
    logger.addHandler(watchtower.CloudWatchLogHandler(args.thing))

    # default low_topic to topic if not defined
    if args.low_topic is None or len(args.low_topic) == 0:
        args.low_topic = args.topic

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = None
    if args.useWebsocket:
        myAWSIoTMQTTClient = AWSIoTMQTTClient('', useWebsocket=True)
        myAWSIoTMQTTClient.configureEndpoint(args.host, port)
        myAWSIoTMQTTClient.configureCredentials(args.rootCAPath)
    else:
        myAWSIoTMQTTClient = AWSIoTMQTTClient('')
        myAWSIoTMQTTClient.configureEndpoint(args.host, port)
        myAWSIoTMQTTClient.configureCredentials(args.rootCAPath, args.privateKeyPath, args.certificatePath)

    # AWSIoTMQTTClient connection configuration
    myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

    myAWSIoTMQTTClient.connect()

    inp = Button(args.pin, pull_up=args.pull_up, bounce_time=args.bounce_time)

    inp.when_pressed = high
    inp.when_released = low

    pause()
