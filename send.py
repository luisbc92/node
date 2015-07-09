#!/usr/bin/env python
# coding=utf-8

import tagscanner
import logging
import time

log = logging.getLogger(__name__)

def tag_read(tag):
	print 'TAG: ' + tag['mac'] + ' ' + str(tag['rssi'])

# entry point of the program
# should be pashed an instance to the mesh network
def main(mesh):
	global ts

	# initiate tag scanner
	ts = tagscanner.TagScanner('ttyAMA0', tag_read)

	while True:
		time.sleep(1)

# exit signal
def exit():
	ts.exit()	# exit tag scanner
