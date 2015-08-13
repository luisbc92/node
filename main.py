#!/usr/bin/env python
# coding=utf-8

import meshnet
import time
import sys
import os
import logging as log

log.basicConfig(stream = sys.stderr, level = log.INFO)

# import application
try:
	import app
except ImportError:
	log.error('APP: Application is invalid')

# instatiate mesh network
mesh = meshnet.MeshNet('/dev/ttyUSB0')

# instatiate application
try:
	app = app.App(mesh)
except:
	log.error('APP: Error instatiating application')

# update pipe
def pipe_update(data):
	log.info('MAIN: Update requested')
	# check if the received file is valid
	try:
		compile(data, '<string>', 'exec')
	except:
		log.error('UPDATE: Application is invalid')
		return

	# stop mesh network and application
	try:
		app.stop()
		mesh.stop()
	except:
		log.warning('MAIN: Error stopping application and mesh')

	# update application
	f = open('/home/pi/node/app.py', 'w')
	f.write(data)
	f.close()

	# restart main module
	python = sys.executable
	os.execl(python, python, * sys.argv)

# stop application pipe
def pipe_stopapp(data):
	log.info('MAIN: Application stop requested')
	try:
		app.stop()
	except:
		log.warning('APP: Error stopping application')

# start application pipe
def pipe_startapp(data):
	log.info('MAIN: Application start requested')
	app.start()

# reset pipe
def pipe_reset(data):
	log.info('MAIN: Reset requested')
	# stop mesh network and application
	try:
		app.stop()
		mesh.stop()
	except:
		log.warning('MAIN: Error stopping application and mesh')

	# restart main module
	python = sys.executable
	os.execl(python, python, * sys.argv)

# main module
def main():
	# start mesh network
	mesh.start()

	# register pipes
	mesh.net_add_pipe('update', pipe_update)
	mesh.net_add_pipe('startapp', pipe_startapp)
	mesh.net_add_pipe('stopapp', pipe_stopapp)
	mesh.net_add_pipe('reset', pipe_reset)

	# execute application
	try:
		app.start()
	except:
		log.error('APP: Error starting application')

	# infinite loop
	try:
		while True:
			pass
	except KeyboardInterrupt:
		pass

	# stop everything
	try:
		app.stop()
		mesh.stop()
	except:
		log.error('MAIN: Error stopping application and mesh')

if __name__ == '__main__':
	main()