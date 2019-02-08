#!/usr/bin/env python

from time import sleep
import datetime
from picamera import PiCamera
import argparse
import platform
import logging
import piot
import watchtower

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--format", action="store", default='jpeg', dest="format", help="Output format")
    parser.add_argument("-p", "--prefix", action="store", default='snapshot', dest="prefix", help="Output prefix")
    parser.add_argument("-d", "--directory", action="store", default='/tmp', dest="directory", help="Output directory")
    parser.add_argument("--width", action="store", default=3280, type=int, dest="width", help="Resolution width")
    parser.add_argument("--height", action="store", default=2464, type=int, dest="height", help="Resolution height")
    parser.add_argument("--thing", help="thing name", default=platform.node().split('.')[0])
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format=piot.LOG_FORMAT)
    logger = logging.getLogger('snapshot')
    logger.addHandler(watchtower.CloudWatchLogHandler(args.thing))

    camera = PiCamera()
    camera.resolution = (args.width, args.height)
    sleep(2)  # Camera warm-up time
    output = "{}/{}-{}-{}.{}".format(args.directory, args.prefix, args.thing,
                                     datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                                     args.format)
    logger.info("snapshot {}".format(output))
    camera.capture(output, format=args.format)
    camera.close()
