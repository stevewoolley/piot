#!/usr/bin/env python

import time
import argparse
import piot


def callback(client, userdata, message):
    print("sub {} {}".format(message.topic, message.payload))
    if message.topic == args.topic:
        # base topic
        print("base topic {}".format(message.topic))
    else:
        # sub topic
        cmd, arg = piot.topic_parser(args.topic, message.topic)
        print("sub topic {} {}".format(cmd, arg))


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
    args = parser.parse_args()

    if args.useWebsocket and args.certificatePath and args.privateKeyPath:
        parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
        exit(2)

    if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
        parser.error("Missing credentials for authentication.")
        exit(2)

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = piot.init_aws_iot_mqtt_client(args)
    myAWSIoTMQTTClient.connect()

    # subscribe to topic
    result = myAWSIoTMQTTClient.subscribe('{}'.format(args.topic), 0, callback)
    time.sleep(2)
    print('Subscribe to {} = {}'.format(args.topic, result))

    # subscribe to subtopics
    result = myAWSIoTMQTTClient.subscribe('{}/#'.format(args.topic), 0, callback)
    time.sleep(2)
    print('Subscribe to {} = {}'.format('{}/#'.format(args.topic), result))

    while True:
        time.sleep(1)
