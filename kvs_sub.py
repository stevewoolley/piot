from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import docker


def my_callback(client, userdata, message):
    docker_client = docker.from_env()
    logger.debug("message topic:{} payload:{}".format(message.topic, message.payload))
    cmd = message.topic.replace('{}/'.format(args.topic), '')
    logger.debug("message cmd:{}".format(cmd))

    if cmd == 'status':
        try:
            print('status:{}'.format(docker_client.containers.get(args.docker_container_name).status))
        except:
            print('status:stopped')
    elif cmd == 'start':
        print('start')
    elif cmd == 'stop':
        client.containers.get(args.docker_container_name).stop()
    else:
        logger.info("invalid cmd:{}".format(cmd))


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
    parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="basicPubSub",
                        help="Targeted client id")
    parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
    parser.add_argument("-n", "--docker_container_name", action="store", dest="docker_container_name",
                        default="kvs-streamer", help="Name of docker container")
    parser.add_argument("-s", "--stream", action="store", dest="stream", required=True,
                        help="Name kinesis video stream")
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
    logger = logging.getLogger("AWSIoTPythonSDK.core")
    logger.setLevel(logging.INFO)
    streamHandler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)

    # Init AWSIoTMQTTClient
    myAWSIoTMQTTClient = None
    if args.useWebsocket:
        myAWSIoTMQTTClient = AWSIoTMQTTClient(args.clientId, useWebsocket=True)
        myAWSIoTMQTTClient.configureEndpoint(args.host, port)
        myAWSIoTMQTTClient.configureCredentials(args.rootCAPath)
    else:
        myAWSIoTMQTTClient = AWSIoTMQTTClient(args.clientId)
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
