#!/usr/bin/env python

import boto3
import psutil
import subprocess as sp
import platform
import argparse
import piot

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


def cw_put_metric(metric, value, unit):
    cloudwatch.put_metric_data(
        MetricData=piot.cloudwatch_metric_data(args.hostname, metric, value, unit),
        Namespace=args.namespace
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--namespace", action="store", dest="namespace",
                        required=True, help="Namespace")
    parser.add_argument("--hostname", action="store", dest="hostname",
                        required=True, help="Hostname")
    args = parser.parse_args()

    # Memory
    mem = psutil.virtual_memory()
    cw_put_metric('MemoryFree', int(mem.available / (1024 * 1024)), 'Megabytes')

    # Disk Usage
    disk = psutil.disk_usage('/')
    cw_put_metric('DiskUsed', int(disk.used / (1024 * 1024)), 'Megabytes')

    # CPU Load
    cpu_load = psutil.cpu_percent(interval=3)
    cw_put_metric('CPUUtilization', cpu_load, 'Percent')

    # CPU Temp
    cpu_temp = None
    if platform.machine().startswith('arm') and platform.system() == 'Linux':  # raspberry pi
        cpu_temp = get_rpi_cpu_temperature()
    if cpu_temp:
        cw_put_metric('CPUTemp', cpu_temp, 'None')
