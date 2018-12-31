#!/usr/bin/env python

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import docker
import watchtower

DEVICES = ["/dev/video0", "/dev/vchiq"]
VOLUMES = {'/opt/vc/': {'bind': '/opt/vc', 'mode': 'rw'}}


def my_callback(client, userdata, message):
    docker_client = docker.from_env()
    logger.debug("message topic {} payload {}".format(message.topic, message.payload))
    cmd = message.topic.replace('{}/'.format(args.topic), '')
    logger.debug("message command {}".format(cmd))

    if cmd == 'status':
        try:
            logger.info('status {} {} {}'.format(
                args.image,
                args.docker_container_name,
                docker_client.containers.get(args.docker_container_name).status)
            )
        except:
            logger.info('status {} {} unknown'.format(
                args.image,
                args.docker_container_name
            ))
    elif cmd == 'start':
        result = docker_client.containers.run(
            args.image,
            detach=True,
            name=args.docker_container_name,
            remove=True,
            devices=DEVICES,
            environment=[
                "stream={}".format(args.stream),
                "aws_access_key={}".format(args.aws_access_key),
                "aws_secret_key={}".format(args.aws_secret_key),
                "aws_region={}".format(args.aws_region)
            ],
            volumes=VOLUMES
        )
        logger.info('start {} {} {}'.format(
            args.image,
            args.docker_container_name,
            result.status
        ))
    elif cmd == 'stop':
        docker_client.containers.get(args.docker_container_name).stop()
        logger.info('stop {} {}'.format(
            args.image,
            args.docker_container_name
        ))
    else:
        logger.warn("invalid command {}".format(cmd))


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
    parser.add_argument("-n", "--docker_container_name", action="store", dest="docker_container_name",
                        default="kvs-streamer", help="Container name")
    parser.add_argument("-s", "--stream", action="store", dest="stream", required=True,
                        help="Kinesis video stream")
    parser.add_argument("-i", "--image", action="store", dest="image", default='rpi-gst',
                        help="Docker image")
    parser.add_argument("--aws_access_key", action="store", dest="aws_access_key", required=True,
                        help="AWS Access Key")
    parser.add_argument("--aws_secret_key", action="store", dest="aws_secret_key", required=True,
                        help="AWS Secret Key")
    parser.add_argument("--aws_region", action="store", dest="aws_region", required=True,
                        help="AWS Region")
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
    logger = logging.getLogger('kvs_sub')
    logger.addHandler(watchtower.CloudWatchLogHandler(args.stream))

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
    myAWSIoTMQTTClient.subscribe('{}/#'.format(args.topic), 1, my_callback)
    time.sleep(2)

    while True:
        time.sleep(1)
