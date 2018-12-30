#!/usr/bin/env python

import boto3
import psutil
import subprocess as sp
import platform
import argparse

cloudwatch = boto3.client('cloudwatch')

def os_execute(s):
    """Returns string result of os call"""
    try:
        return sp.check_output(s.split()).rstrip('\n')
    except Exception as ex:
        return None


def get_rpi_cpu_temperature():
    """Returns raspberry pi cpu temperature in Centigrade"""
    temp = os_execute('/opt/vc/bin/vcgencmd measure_temp')
    return float(temp.split('=')[1].strip('\'C'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--namespace", action="store", dest="namespace",
                        required=True, help="Namespace")
    parser.add_argument("--hostname", action="store", dest="hostname",
                        required=True, help="Hostname")
    args = parser.parse_args()

    # Memory
    mem = psutil.virtual_memory()
    cloudwatch.put_metric_data(
        MetricData=[
            {
                'MetricName': 'MemoryFree',
                'Dimensions': [
                    {
                        'Name': 'hostname',
                        'Value': args.hostname
                    },
                ],
                'Unit': 'Megabytes',
                'Value': int(mem.available / (1024 * 1024))
            },
        ],
        Namespace=args.namespace
    )

    # Disk Usage
    disk = psutil.disk_usage('/')
    cloudwatch.put_metric_data(
        MetricData=[
            {
                'MetricName': 'DiskUsed',
                'Dimensions': [
                    {
                        'Name': 'hostname',
                        'Value': args.hostname
                    },
                ],
                'Unit': 'Megabytes',
                'Value': int(disk.used / (1024 * 1024))
            },
        ],
        Namespace=args.namespace
    )

    # CPU Load
    cpu_load = psutil.cpu_percent(interval=3)
    cloudwatch.put_metric_data(
        MetricData=[
            {
                'MetricName': 'CPUUtilization',
                'Dimensions': [
                    {
                        'Name': 'hostname',
                        'Value': args.hostname
                    },
                ],
                'Unit': 'Percent',
                'Value': cpu_load
            },
        ],
        Namespace=args.namespace
    )

    # CPU Temp
    cpu_temp = None
    if platform.machine().startswith('arm') and platform.system() == 'Linux':  # raspberry pi
        cpu_temp = get_rpi_cpu_temperature()
    if cpu_temp:
        cloudwatch.put_metric_data(
            MetricData=[
                {
                    'MetricName': 'CPUTemp',
                    'Dimensions': [
                        {
                            'Name': 'hostname',
                            'Value': args.hostname
                        },
                    ],
                    'Unit': 'None',
                    'Value': cpu_temp
                },
            ],
            Namespace=args.namespace
        )
