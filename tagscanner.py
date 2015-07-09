#!/usr/bin/env python
# coding=utf-8

from serial import Serial
import logging
import threading
import bglib
import re
import time

log = logging.getLogger(__name__)

class TagScanner:

	# variable to kill thread
	kill_check_activity = False

	# discovered tags
	tags = {}

	# function to call when a tag is read
	receive = None

	# dummy receive callback
	def dummy(self, data):
		pass

	# timeout handler
	def timeout(self, sender, args):
		log.info('BGLIB: Parser timed out')

	# scan response handler
	def scan_response(self, sender, args):
		# convert MAC to string
		sender = ''.join(chr(c) for c in args['sender'])

		# capture advertisement packets and look for tags
		if args['packet_type'] == 0:							# 0 - connectable advertisement packet
			ble_name = ''.join('%c' %c for c in args['data'])	# convert all data into a string to extract name (lazy)
			ble_name = re.sub(r'\W+', '', ble_name)				# remove everything but chars (lazier)
			if ble_name.find('TAG') == 0:						# if name begins with 'TAG'
				if not sender in self.tags:						# and if not yet discovered
					self.tags[sender] = {'count': 0}			# create entry for this tag
					log.info('TAG: Discovered %s', ble_name)

		# capture scan response packet and extract data
		# packet structure (30 bytes)
		# byte 0  	= packet length	(ignored)
		# byte 1  	= packet type 	(ignored)
		# byte 2-28	= data payload
		# byte 29	= packet count 	(used to identify retransmitted packets)
		# check activity thread
		rx = {}
		if args['packet_type'] == 4 and sender in self.tags and len(args['data']) == 30:
			# check if packet was already received
			if not args['data'][29] == self.tags[sender]['count']:
				rx['mac'] = sender					# MAC address
				rx['count'] = args['data'][29]		# packet count
				rx['rssi'] = args['rssi']			# RSSI
				rx['data'] = args['data'][2:29]		# data payload
				self.tags[sender] = rx				# append received packet
				self.receive(rx)					# call user

	def check_activity(self):
		while not self.kill_check_activity:
			self.ble.check_activity(self.serial)	# Check all incoming data
			time.sleep(0.01) 						# Sleep a bit

	# exit handler
	def exit(self):
		self.kill_check_activity = True
		self.serial.close()

	def __init__(self, port, receive = dummy):
		self.serial = Serial(port=port, baudrate=115200, timeout=1)
		self.serial.flushInput()
		self.serial.flushOutput()

		# set callback
		self.receive = receive

		# Initialize BGLib
		self.ble = bglib.BGLib()
		self.ble.packet_mode = False
		self.ble.on_timeout = self.timeout 							# Timeout handler
		self.ble.ble_evt_gap_scan_response += self.scan_response 	# Scan response handler
		# Disconnect BLE
		self.ble.send_command(self.serial, self.ble.ble_cmd_connection_disconnect(0)) 
		self.ble.check_activity(self.serial, 1)
		# Stop advertising
		self.ble.send_command(self.serial, self.ble.ble_cmd_gap_set_mode(0, 0))
		self.ble.check_activity(self.serial, 1)
		# Set scan parameter (interval, window, active)
		self.ble.send_command(self.serial, self.ble.ble_cmd_gap_set_scan_parameters(0xC8, 0xC8, 1))
		self.ble.check_activity(self.serial, 1)
		# Stop scanning
		self.ble.send_command(self.serial, self.ble.ble_cmd_gap_discover(1))
		self.ble.check_activity(self.serial, 1)

		# create thread for checking
		self.check_t = threading.Thread(target=self.check_activity)
		self.check_t.start()
