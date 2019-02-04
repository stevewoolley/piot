#!/usr/bin/env python

from time import sleep
from picamera import PiCamera
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", action="store", required=True, dest="output", help="Output filename")
    parser.add_argument("-f", "--format", action="store", default='jpeg', dest="format", help="Output format")
    parser.add_argument("--width", action="store", default=3280, dest="width", help="Resolution width")
    parser.add_argument("--height", action="store", default=2464, dest="height", help="Resultion height")
    args = parser.parse_args()

    camera = PiCamera()
    camera.resolution = (args.width, args.height)
    # Camera warm-up time
    sleep(2)
    camera.capture(args.output, format=args.format)
    camera.close()