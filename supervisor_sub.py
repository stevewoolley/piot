#!/usr/bin/env python

import argparse
import logging
import watchtower
import piot
import time
from datetime import datetime, timedelta
import xmlrpclib
import supervisor.xmlrpc
import platform
import AWSIoTPythonSDK.exception.AWSIoTExceptions

SHADOW_VAR = 'supervised'

pulses = {}


def status():
    processes = proxy.supervisor.getAllProcessInfo()
    procs = {}
    for s in processes:
        procs[s['name']] = s['statename']
    logger.info("supervised: {}".format(processes))
    try:
        myAWSIoTMQTTClient.publish(
            piot.iot_thing_topic(args.thing),
            piot.iot_payload('reported', procs), 0)
    except (AWSIoTPythonSDK.exception.AWSIoTExceptions.publishTimeoutException,
            AWSIoTPythonSDK.exception.AWSIoTExceptions.subscribeTimeoutException):
        logger.warn("callback publish timeout")


def start(process):
    try:
        proxy.supervisor.startProcess(process)
    except Exception as err:
        logging.error("{} {} failed {}".format('start', process, err))
    status()


def stop(process):
    try:
        proxy.supervisor.stopProcess(process)
    except Exception as err:
        logging.error("{} {} failed {}".format('stop', process, err))
    status()


def restart():
    try:
        proxy.supervisor.restart()
    except Exception as err:
        logging.error("{} failed {}".format('restart', err))
    status()


def pulse(process, seconds=10):
    try:
        proc = proxy.supervisor.getProcessInfo(process)
        if proc['state'] == 0:
            start(process)
        pulses[process] = datetime.now() + timedelta(seconds=int(seconds))
    except Exception as err:
        logging.error("{} {} failed {}".format('pulse', process, err))


def callback(client, userdata, message):
    logger.debug("message topic {} payload {}".format(message.topic, message.payload))
    cmd, arg, arg2 = piot.topic_parser(args.topic, message.topic)
    logger.info("{} {}".format(cmd, arg))
    if cmd == 'status' and arg is None:
        status()
    elif cmd == 'restart' and arg is None and arg2 is None:
        restart()
    elif cmd == 'start' and arg is not None:
        start(arg)
    elif cmd == 'stop' and arg is not None:
        stop(arg)
    elif cmd == 'pulse' and arg is not None and arg2 is not None:
        pulse(arg, arg2)
    else:
        logging.error('invalid command {} {}'.format(cmd, arg))


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
        for key, value in pulses.iteritems():
            if datetime.now() > value:
                stop(key)
                del pulses[key]
        time.sleep(1)
