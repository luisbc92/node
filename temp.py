import meshnet
import sys
import logging as log

log.basicConfig(stream=sys.stderr, level=log.INFO)

rx = False

mesh = meshnet.MeshNet('com13')

def get(data):
	global rx
	if rx:
		src = mesh.status.source.encode('hex')
		print src + ' says ' + data

def on():
	global rx
	rx = True

def off():
	global rx
	rx = False

mesh.receive = get
mesh.net_master()

f = open('send.py', 'r')
send = f.read()


