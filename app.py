#!/usr/bin/env python
# coding=utf-8

import tagscanner
import logging
import time

log = logging.getLogger(__name__)

def tag_read(tag):
	# send to master
	mesh.net_tx(mesh.attr.master, tag)

def mesh_receive(data):
	pass

# entry point of the program
# should be pashed an instance to the mesh network
def main(_mesh):
	global ts
	global mesh

	mesh = _mesh

	# register receive callback
	mesh.receive = mesh_receive

	# initiate tag scanner
	ts = tagscanner.TagScanner('/dev/ttyAMA0', tag_read)

	while True:
		time.sleep(1)

# exit signal
def exit():
	ts.exit()	# exit tag scanner
