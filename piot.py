import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

TOPIC_STATUS_ON = ['1', 'on']
TOPIC_STATUS_OFF = ['0', 'off']
TOPIC_STATUS_TOGGLE = ['toggle']
TOPIC_STATUS_PULSE = ['blink', 'pulse']
LOG_FORMAT = '%(asctime)s %(filename)-15s %(funcName)-15s %(levelname)-8s %(message)s'
DATE_FORMAT = '%Y/%m/%d %-I:%M %p %Z'
FILE_DATE_FORMAT = '%Y-%m-%d-%H-%M-%S'


def iot_thing_topic(thing):
    return "$aws/things/{}/shadow/update".format(thing)


def iot_payload(target, doc):
    return json.dumps({'state': {target: doc}})


def topic_parser(prefix, message_topic):
    suffix = message_topic.replace('{}/'.format(prefix), '').split('/')
    arg = None
    arg2 = None
    cmd = suffix[0]
    if len(suffix) > 1:
        arg = suffix[1]
    if len(suffix) > 2:
        arg2 = suffix[2]
    return cmd, arg, arg2


def cloudwatch_metric_data(hostname, metric, value, unit, dimension='hostname'):
    return [
        {
            'MetricName': metric,
            'Dimensions': [
                {
                    'Name': dimension,
                    'Value': hostname
                },
            ],
            'Unit': unit,
            'Value': value
        },
    ]


def init_aws_iot_mqtt_client(args):
    # Init AWSIoTMQTTClient
    client = None
    port = args.port
    # Port defaults
    if args.useWebsocket and not args.port:  # When no port override for WebSocket, default to 443
        port = 443
    if not args.useWebsocket and not args.port:  # When no port override for non-WebSocket, default to 8883
        port = 8883
    #
    if args.useWebsocket:
        client = AWSIoTMQTTClient('', useWebsocket=True)
        client.configureEndpoint(args.host, port)
        client.configureCredentials(args.rootCAPath)
    else:
        client = AWSIoTMQTTClient('')
        client.configureEndpoint(args.host, port)
        client.configureCredentials(args.rootCAPath, args.privateKeyPath, args.certificatePath)
    # AWSIoTMQTTClient connection configuration
    client.configureAutoReconnectBackoffTime(1, 32, 20)
    client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    client.configureDrainingFrequency(2)  # Draining: 2 Hz
    client.configureConnectDisconnectTimeout(10)  # 10 sec
    client.configureMQTTOperationTimeout(5)  # 5 sec
    return client
