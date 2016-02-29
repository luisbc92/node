import meshnet
import sys
import time
import logging as log

log.basicConfig(stream=sys.stderr, level=log.INFO)

print 'Initializing mesh network..'
mesh = meshnet.MeshNet('com4')
mesh.start()
mesh.net_master()

print 'Stopping application...'
mesh.net_tx(mesh.attr.broadcast, ' ', 'stopapp')
time.sleep(1)

print 'Sending update...'
f = open('app.py', 'r')
update = f.read()
mesh.net_tx(mesh.attr.broadcast, update, 'update')

print 'Waiting...'
time.sleep(5)

mesh.stop()