#!/usr/bin/env python
# coding=utf-8

import meshnet
import time
import sys
import os
import logging as log

log.basicConfig(stream=sys.stderr, level=log.DEBUG)

try:
	import app
except ImportError:
	log.error('APP: Application is invalid')

# initiate mesh network
mesh = meshnet.MeshNet('/dev/ttyUSB0')

def pipe_update(data):
	# check if the received file is correct
	try:
		compile(data, '<string>', 'exec')
	except:
		log.warning('UPDATE: Invalid app')
		return

	# stop mesh and app
	try:
		app.exit()
		mesh.exit()
	except:
		log.warning('MAIN: Error exiting')

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
		pass
	except:
		log.warning('APP: Unexpected error')
		while True:
			# keep running to get updates
			pass


	# stop mesh and app
	try:
		app.exit()
		mesh.exit()
	except:
		log.warning('MAIN: Error exiting')

if __name__ == '__main__':
	main()
