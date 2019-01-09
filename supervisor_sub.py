#!/usr/bin/env python

import argparse
import logging
import watchtower
import piot
import time
import xmlrpclib
import supervisor.xmlrpc
import platform
import AWSIoTPythonSDK.exception.AWSIoTExceptions

SHADOW_VAR = 'supervised'


def publish_status(delay=2):
    time.sleep(delay)
    results = proxy.supervisor.getAllProcessInfo()
    supervised = []
    for s in results:
        supervised.append('{} ({})'.format(s['name'], s['statename']))
    logger.info("supervised: {}".format(', '.join(supervised)))
    try:
        myAWSIoTMQTTClient.publish(
            piot.iot_thing_topic(args.thing),
            piot.iot_payload('reported', {SHADOW_VAR: ', '.join(supervised)}), 0)
    except (AWSIoTPythonSDK.exception.AWSIoTExceptions.publishTimeoutException,
            AWSIoTPythonSDK.exception.AWSIoTExceptions.subscribeTimeoutException):
        logger.warn("callback publish timeout")


def callback(client, userdata, message):
    logger.debug("message topic {} payload {}".format(message.topic, message.payload))
    cmd, arg = piot.topic_parser(args.topic, message.topic)
    logger.info("callback {}".format(cmd))
    if cmd == 'status':
        publish_status(0)
    elif cmd == 'start':
        logger.info('{} {}'.format(cmd, arg))
        try:
            proxy.supervisor.startProcess(arg)
        except Exception as err:
            logging.error("{} {} failed {}".format(cmd, arg, err))
        publish_status()
    elif cmd == 'stop':
        logger.info('{} {}'.format(cmd, arg))
        try:
            proxy.supervisor.stopProcess(arg)
        except Exception as err:
            logging.error("{} {} failed {}".format(cmd, arg, err))
        publish_status()


if __name__ == "__main__":
    # Read in command-line parameters
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host",
                        help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
    parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
    parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
    parser.add_argument("-p", "--port", action="store", dest="port", type=int, help="Port number override")
    parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                        help="Use MQTT over WebSocket")
    parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
    parser.add_argument("--thing", help="thing name", default=platform.node().split('.')[0])
    parser.add_argument("--socket_path", help="socket path", default='/var/run/supervisor.sock')
    parser.add_argument("--uri", help="Uniform Resource Indicator", default='http://127.0.0.1')

    args = parser.parse_args()

    if args.useWebsocket and args.certificatePath and args.privateKeyPath:
        parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format=piot.LOG_FORMAT)
    logger = logging.getLogger('supervisor_sub')
    logger.addHandler(watchtower.CloudWatchLogHandler(args.thing))

    proxy = xmlrpclib.ServerProxy(
        args.uri, transport=supervisor.xmlrpc.SupervisorTransport(
            None, None, serverurl='unix://{}'.format(args.socket_path)))

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = piot.init_aws_iot_mqtt_client(args)
    myAWSIoTMQTTClient.connect()
    myAWSIoTMQTTClient.subscribe('{}/#'.format(args.topic), 1, callback)
    time.sleep(2)

    while True:
        time.sleep(1)
