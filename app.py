from serial import Serial
import threading
import logging
import time
import bglib
import re
import time

log = logging.getLogger(__name__)

class App:
	# mesh net
	mesh = None

	# run status
	running = False

	# tag list
	tags = []

	# rssi average for each tag
	rssi_avg = {}

	# average parameters
	RSSIw = 0.1

	# distance parameters
	A = 1.0
	n = 1.0
	Ptx = 4.0

	# check gap scan response packets
	def gap_scan_response(self, sender, args):
		# convert MAC to string
		sender = ''.join(chr(c) for c in args['sender'])

		# capture advertisement packets and look for tags
		if args['packet_type'] == 0:
			ble_name = ''.join('%c' %c for c in args['data'])	# convert all data into a string to extract name (lazy)
			ble_name = re.sub(r'\W+', '', ble_name)				# remove everything but chars (lazier)
			if ble_name.find('TAG') == 0:						# if name begins with 'TAG'
				if not sender in self.tags:						# if tag is not in list
					self.tags.append(sender)					# add it
					self.rssi_avg[sender] = 0					# init average
				self.rssi_avg[sender] = (1.0 - self.RSSIw) * self.rssi_avg[sender] + self.RSSIw * float(args['rssi'])
				distance = self.A * pow(abs(self.Ptx / self.rssi_avg[sender]), self.n) 
				#distance = pow((self.Ptx - self.rssi_avg[sender]) / (10 * self.n), 10)
				tag = {'mac': sender, 'rssi': self.rssi_avg[sender], 'd': distance}	# pack data 
				print 'Sent packet: ' + str(tag)
				self.mesh.net_tx(self.mesh.attr.master, tag)		# send to master

		# get payload
		if args['packet_type'] == 4 and sender in self.tags:
			self.rssi_avg[sender] = 0.9 * self.rssi_avg[sender] + 0.1 * float(args['rssi'])
			distance = self.A * pow((self.Ptx / self.rssi_avg[sender]), self.n) 
			tag = {'mac': sender, 'rssi': self.rssi_avg[sender], 'd': distance, 'data': args['data']}	# pack data
			print 'Sent packet: ' + str(tag)
			self.mesh.net_tx(self.mesh.attr.master, tag)		# send to master

	# ble check activity thread
	def check_activity(self):
		while self.running:
			self.ble.check_activity(self.serial)
			time.sleep(0.01)

	# start application
	def start(self):
		# Initialize BGLib
		self.ble = bglib.BGLib()
		self.ble.packet_mode = False
		self.ble.ble_evt_gap_scan_response += self.gap_scan_response 	# Scan response handler
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

		# register pipes
		self.mesh.net_add_pipe('seta', self.pipe_seta)
		self.mesh.net_add_pipe('setn', self.pipe_setn)
		self.mesh.net_add_pipe('setrssiw', self.pipe_setrrsiw)

		# setup thread for checking ble activity
		self.running = True
		self.check_thread.start()

	# stop application
	def stop(self):
		self.running = False
		time.sleep(0.5)
		self.serial.close()

	# A parameter pipe
	def pipe_seta(self, data):
		self.A = float(data)


	# n parameter pipe
	def pipe_setn(self, data):
		self.n = float(data)

	# RSSI weight pipe
	def pipe_setrrsiw(self, data):
		self.RSSIw = float(data)

	# initialize application
	def __init__(self, mesh):
		# get instance of the mesh network
		self.mesh = mesh

		# open serial port
		self.serial = Serial(port='/dev/ttyACM0', baudrate=115200, timeout=1)
		self.serial.flushInput()
		self.serial.flushOutput()

		# create thread
		self.check_thread = threading.Thread(target=self.check_activity)
