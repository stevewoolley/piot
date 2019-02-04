#!/usr/bin/env python

from time import sleep
import datetime
from picamera import PiCamera
import argparse
import platform

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--format", action="store", default='jpeg', dest="format", help="Output format")
    parser.add_argument("-p", "--prefix", action="store", default='snapshot', dest="prefix", help="Output prefix")
    parser.add_argument("--width", action="store", default=3280, type=int, dest="width", help="Resolution width")
    parser.add_argument("--height", action="store", default=2464, type=int, dest="height", help="Resolution height")
    parser.add_argument("--thing", help="thing name", default=platform.node().split('.')[0])
    args = parser.parse_args()

    camera = PiCamera()
    camera.resolution = (args.width, args.height)
    sleep(2)  # Camera warm-up time
    output = "{}-{}-{}.{}".format(args.prefix, args.thing, datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                                  args.format)
    camera.capture(args.output, format=args.format)
    camera.close()
