#!/usr/bin/env python
# coding=utf-8

"""
meshnet.py

By Luis Bañuelos, 2015
luiscarlos.banuelos@gmail.com

This module creates a simple network using Xbee DigiMesh modules.
Packets sent on the network are encoded using MessagePack.

Uses Paul Malmsten Xbee API library.
"""
import logging
import time
from xbee import DigiMesh
from serial import Serial
from umsgpack import packb as pack
from umsgpack import unpackb as unpack

log = logging.getLogger(__name__)

class NoResponseException(Exception):
	pass

class TxFailureException(Exception):
	pass

class InvalidFrameTypeException(Exception):
	pass

class MeshNet:

	# struct of network attributes
	class attr:
		broadcast = '\x00\x00\x00\x00\x00\x00\xFF\xFF'
		master = '\x00\x00\x00\x00\x00\x00\xFF\xFE'	# Address of the master node (bcast default)
		id = ''				# Mesh Network ID
		ch = ''				# Mesh Network Channel
		retries = 3			# Number of attempts to send a packer
		mtu = 60			# Maximum Transmission Unit

	# struct of status information
	class status:
		tx = None 			# Transmit status information
		master = False		# True if currently the master node
		source = '\x00\x00\x00\x00\x00\x00\xFF\xFF'	# source address of last received packet

	# nodes currently sending chunks
	chunks = {}

	# user defined transfer pipes
	# key is pipe name
	# value is callback
	pipes = {}

	# function to call when receiving data
	receive = None

	# dummy receive callback
	def dummy(self, data):
		pass

	# enters command mode and returns True if succesful
	def xbee_at_begin(self):
		time.sleep(1)
		self.serial.write('+++')
		time.sleep(1)
		if self.serial.read(3) == 'OK\r':
			self.serial.flushOutput()
			self.serial.flushInput()
			return True
		else:
			return False

	# sends AT command and reads reply (crappily)
	def xbee_at(self, cmd):
		self.serial.write('AT' + cmd + '\r')
		return self.serial.read(3)

	def net_add_pipe(self, name, callback):
		self.pipes[name] = callback

	# transmit packet to the network (blocks until ack)
	def net_tx(self, dest, data, pipe='data'):
		# pack only the data to test its length
		p_data = pack(data)					# pack the data
		mtu = self.attr.mtu					# get mtu

		size = (len(p_data) / mtu) + (len(p_data) % mtu > 0)		# number of packets
		packet = {'t': pipe, 'size': size}						# create header
		self.xbee_tx(dest=dest, data=pack(packet), ack=True)		# send header
		for chunk in [p_data[x:x+mtu] for x in range(0, len(p_data), mtu)]:	# partition in chunks
			packet = {'t': 'c', 'c': chunk}							# type c for chunk (reduce overhead)	
			self.xbee_tx(dest=dest, data=pack(packet), ack=True)	# transmit chunk
		log.debug('NET: Sent packet')

	# advertises self as the master node in the network
	# will update each nodes master address and build route
	def net_master(self):
		packet = {'t': 'set-master'}		# create packet
		tx = pack(packet)					# pack the packet

		# broadcast packet to all nodes (no need to ack)
		self.xbee.send('tx', dest_addr='\x00\x00\x00\x00\x00\x00\xFF\xFF', data=tx)

		# ask all nodes to build route to master
		self.xbee.at(command='AG', parameter='\xFF\xFF')

		# log
		if (self.status.master == False):
			log.info('NET: Becoming master node')	# Just became master
			self.status.master = True
		# readvertising otherwise

	# join the network, causing master to indentify itself
	def net_join(self):
		packet = {'t': 'join'}		# create packet
		tx = pack(packet)				# pack the packet

		# broadcast packet to all nodes (no need to ack)
		self.xbee_tx(dest='\x00\x00\x00\x00\x00\x00\xFF\xFF', data=tx)
		log.info('NET: Joined network')

	# handles frames received from the network
	def net_rx(self, frame):
		address = frame['source_addr']
		self.status.source = address
		rx = unpack(frame['data'])

		# receive a chunk (should be first)
		if address in self.chunks:
			if rx['t'] == 'c':
				self.chunks[address]['data'] += rx['c']		# append chunk
				self.chunks[address]['size'] -= 1			# decrement size left
				if self.chunks[address]['size'] == 0:		# if we have all chunks
					data = unpack(self.chunks[address]['data'])	# unpack
					callback = self.chunks[address]['callback']	# get function to call
					del self.chunks[address]				# remove node from list
					log.debug('NET: Received packet')
					callback(data)
			else:	# we were expecting chunks but got something different
				del self.chunks[address]	# transmission got corrupted, take of out list
				log.warning('NET: Lost packet')

		# get new master address and update dh/dl (not really needed)
		if rx['t'] == 'set-master':
			log.info('NET: New master node')
			self.xbee.at(command='DH', parameter='\x00\x00')
			self.xbee.at(command='DL', parameter='\xFF\xFF')
			self.attr.master = '\x00' + frame['source_addr']
			self.status.master = False

		# node joined the network, if master, readvertise
		if rx['t'] == 'join' and self.status.master == True:
			log.info('NET: New node joined the network')
			self.net_master()

		# receive data (data pipe)
		if rx['t'] == 'data':
			# insert new entry into chunks pending dictionary with the
			# source address as a key, this is used to catch the remaining
			# packets and insert data directly. size is decremented when
			# more packets are received until it hits 0 and the packet is complete.
			# callback contains the function to call when the entire packet is received.
			self.chunks[address] = {'callback': self.receive, 'size': rx['size'], 'data': ''}

		# user defined pipes
		if rx['t'] in self.pipes:
			callback = self.pipes[rx['t']]
			self.chunks[address] = {'callback': callback, 'size': rx['size'], 'data': ''}

	# transmit data from Xbee
	def xbee_tx(self, dest, data, ack=False):
		# if ack is needed set frame_id = 1
		if (ack):
			frame_id='\x01'
		else:
			frame_id='\x00'

		# send packet
		self.xbee.send('tx', frame_id=frame_id , dest_addr=dest, data=data)

		# if ack is needed, wait for it
		if ack:
			# wait until packet is acknowledged
			while (self.status.tx == None):
				time.sleep(0.01)
			# check response
			if not (self.status.tx == '\x00'):
				self.status.tx = None
				log.warning('XBEE: TX Failed')
				#raise TxFailureException
			else:
				self.status.tx = None

	# handles API frames from Xbee
	def xbee_rx(self, frame):
		# aggregate addressing update
		if (frame['id'] == 'ag_update'):
			log.info('XBEE: Route to master updated')
			pass

		# forward frame to network
		if (frame['id'] == 'rx'):
			log.debug('XBEE: Received data frame')
			self.net_rx(frame)

		# transmission status
		if (frame['id'] == 'tx_status'):
			log.debug('XBEE: Transmission status report')
			self.status.tx = frame['deliver_status']

	def exit(self):
		self.xbee.halt()
		self.serial.close()

	# initializes mesh network
	# port = xbee serial port
	# mesh_id = mesh network id (0x0000 - 0xFFFF)
	# mesh_ch = mesh network ch (0x0C - 0x17)
	# receive = handler for incoming data
	def __init__(self, port=None, mesh_id='\x55\x55', mesh_ch='\x0C', receive=dummy):
		# Serial port
		self.serial = Serial(port, timeout=0.5)

		# Mesh Network ID
		self.attr.id = mesh_id
		# Mesh Network Channel
		self.attr.ch = mesh_ch

		# capture receive callback
		self.receive = receive

		# find and configure xbee for communication at 57,600bps and API mode
		self.serial.baudrate = 57600
		self.serial.flushOutput()
		self.serial.flushInput()
		if not (self.xbee_at_begin() and self.xbee_at('AP') == '1\r'):
			log.info('XBEE: Not configured')
			for baud in [9600, 57600, 115200, 1200, 2400, 4800, 38400]:	# loop through baud rates
				log.info('XBEE: Trying at %dbps', baud)
				self.serial.baudrate = baud
				self.serial.flushInput()
				self.serial.flushOutput()
				if (self.xbee_at_begin()):
					self.xbee_at('RE')		# restore factory settings
					self.xbee_at('BD6')		# baud rate 57,600 bps
					self.xbee_at('AP1')		# api mode
					self.xbee_at('WR')		# write settings
					self.xbee_at('CN')		# exit command mode
					log.info('XBEE: Ready')
					break
			else:
				log.error('XBEE: No Response from Xbee')
				raise NoResponseException
		else:
			self.xbee_at('CN')
			log.info('XBEE: Ready')

		# set mesh network id and channel and set default dh/dl
		self.serial.baudrate = 57600
		self.xbee = DigiMesh(self.serial, callback=self.xbee_rx)
		self.xbee.at(command='ID', parameter=self.attr.id)
		self.xbee.at(command='CH', parameter=self.attr.ch)
		self.xbee.at(command='DH', parameter='\x00\x00')
		self.xbee.at(command='DL', parameter='\xFF\xFF')

		# join the network
		self.net_join()






