#!/usr/bin/env python
# coding=utf-8

import tagscanner
import logging
import time

log = logging.getLogger(__name__)

mesh = None

def tag_read(tag):
	print 'TAG: ' + tag['mac'] + ' ' + str(tag['rssi'])

# entry point of the program
# should be pashed an instance to the mesh network
def main(_mesh):
	global mesh

	# initiate tag scanner
	#ts = tagscanner.TagScanner('ttyACM0', tag_read)

	mesh = _mesh

	while True:
		time.sleep(1)
		mesh.net_tx(mesh.attr.master, 'alive')

# exit signal
def exit():
	ts.exit()	# exit tag scanner
