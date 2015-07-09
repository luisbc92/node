#!/usr/bin/env python
# coding=utf-8

import meshnet
import time
import sys
import os
import app
import logging as log

log.basicConfig(stream=sys.stderr, level=log.INFO)

# initiate mesh network
mesh = meshnet.MeshNet('ttyUSB0')

def pipe_update(data):
	# check if the received file is correct
	try:
		compile(data, '<string>', 'exec')
	except:
		log.warning('UPDATE: Invalid app')
		return

	# stop mesh and app
	mesh.exit()
	app.exit()

	# update app
	f = open('./app.py', 'w')
	f.write(data)
	f.close()

	# restart main module
	python = sys.executable
	os.execl(python, python, * sys.argv)

def main():
	# update pipe
	mesh.net_add_pipe('update', pipe_update)

	try:
		# execute app
		app.main(mesh)
	except KeyboardInterrupt:
		app.exit()
		mesh.exit()

if __name__ == '__main__':
	main()