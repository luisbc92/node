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

	# check gap scan response packets
	def gap_scan_response(self, sender, args):
		# convert MAC to string
		sender = sender.encode('hex')

		# capture advertisement packets and look for tags
		if args['packet_type'] == 0:
				ble_name = ''.join('%c' %c for c in args['data'])	# convert all data into a string to extract name (lazy)
				ble_name = re.sub(r'\W+', '', ble_name)				# remove everything but chars (lazier)
				if ble_name.find('TAG') == 0:						# if name begins with 'TAG'
					tag = {'mac': send, 'rssi': args['rssi'], 'count': 0}	# pack data
					mesh.net_tx(mesh.attr.master, tag)						# send to master

	# ble check activity thread
	def check_activity(self):
		while running:
			self.ble.check_activity(self.serial)
			time.sleep(0.1)

	# start application
	def start(self):
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

		# setup thread for checking ble activity
		self.running = True
		self.thread = threading.Thread(target=self.check_activity)
		self.thread.start()

	# stop application
	def stop(self):
		self.running = False
		self.thread.join(1)
		self.serial.close()

	# initialize application
	def __init__(self, _mesh):
		# get instance of the mesh network
		mesh = _mesh

		# open serial port
		self.serial = Serial(port='/dev/ttyACM0', baudrate=115200, timeout=1)
		self.serial.flushInput()
		self.serial.flushOutput()
