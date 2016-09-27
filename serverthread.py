import sys, os

from PyQt4.QtGui import QApplication
# from PyQt4.QtCore import QUrl, QTimer, QObject, pyqtSignal
from PyQt4.QtCore import *
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtGui import QCheckBox, QDialog, QComboBox, QFrame, QSizePolicy, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QWidget, QHeaderView, QPushButton, QTextEdit, QLabel
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest

import select
import socket
from threading import Thread
from time import ctime
import sys

''' Global variables -------------------------------------------------------'''

HOST    = '127.0.0.1'
PORT    = 56789
ADDR    = (HOST, PORT)
BUFSIZE = 1024
PERIOD  = 1000  # msec - send status report request to every drone periodically
drone_list = [] # list of the connected drones
MAC_list = [] # list of the MAC address of all drone clients
selected_drone = []
STATUS_OUTPUT = 'select a drone\n'
droneSize = 30

def LOG(logger, msg):
	print str(ctime()) + ' [' + logger + '] ' + msg

def drone_by_mac(mac):
	for drone in drone_list:
		if drone.getMAC() == mac:
			return drone

	return None

def drone_by_id(id_):
	for drone in drone_list:
		if drone.getId() == id_:
			return drone

	return None

''' Server thread class ----------------------------------------------------'''

class ServerThread(Thread):
	def __init__(self, signal):
		Thread.__init__(self)
		try:
			LOG('Server', 'create socket')
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			LOG('Server', 'bind address to the socket')
			self.socket.bind(ADDR)
			LOG('Server', 'start listening')
			self.socket.listen(10)
			self.setDaemon(True)
		except Exception, e:
			LOG('Server', repr(e))
			raise ValueError(repr(e))

		self.signal = signal

	def run(self):
		connection_list = [self.socket]
		self.drone_idx = 1

		try:
			while True:
				read_socket, write_socket, error_socket = select.select(connection_list, [], [], 10)

				for sock in read_socket:
					# a new client
					if sock == self.socket:
						client, addr = self.socket.accept()
						connection_list.append(client)
						idx = connection_list.index(client) - 1
						LOG('Server', 'a new client ' + str(idx) + ' is connected')
						
					# existing client
					else:
						data = sock.recv(BUFSIZE)
						idx = connection_list.index(sock) - 1

						if data:
							LOG('Server', 'received message from client ' + str(idx) + ': ' + data)

							msgList = data.split('\t')
							msgList.pop()
							for curMsg in msgList:
								msg = curMsg.split(' ')
								if msg[0] == 'gui':
									if msg[1] == 'timer':
										self.guiTimerHandler()
									elif msg[1] == 'launch':
										self.guiLaunchHandler(msg)
									elif msg[1] == 'landing':
										self.guiLandingHandler(msg)
									elif msg[1] == 'relocation':
										self.guiRelocationHandler(msg)
									elif msg[1] == 'videoShare':
										self.guiVideoShareHandler(msg)
									elif msg[1] == 'frame':
										self.guiFrameHandler()
									elif msg[1] == 'gohome':
										self.guiGoHomeHandler(msg)
									else:
										LOG('Server', 'error - undefined message: ' + data)

								elif msg[0] == 'drone':
									if msg[1] == 'new':
										self.droneNewHandler(sock, msg)
										self.guiTimerHandler()
									elif msg[1] == 'status':
										self.droneStatusHandler(sock, msg)
									else:
										LOG('Server', 'error - undefined message: ' + data)

								else:
									LOG('Server', 'error - undefined message: ' + data)
						else:
							LOG('Server', 'client ' + str(idx) + ': the end of the connection')
							if idx >= 1:
								for drone_in_list in drone_list:
									if drone_in_list.getSocket() == sock:
										break
								else:
									continue
								droneID = drone_in_list.getId()
								drone_list.remove(drone_in_list)
								if drone_in_list in selected_drone:
									selected_drone.remove(drone_in_list)

								drone_in_list.__del__()

								output = ('Drone %d: connection closed' % droneID)
								LOG('Server', output)
								self.signal.emit(output)

								output2 = ("closed %d" % droneID)
								self.signal.emit(output2)

							else:
								output = ('GUI-server connection closed')
								LOG('Server', output)
								self.signal.emit(output)

							connection_list.remove(sock)
							sock.close()

		except Exception, e:
			LOG('Server', repr(e))
			self.socket.shutdown(socket.SHUT_RDWR)

		LOG('Server', 'socket shutdown')
		try:
			self.socket.shutdown(socket.SHUT_RDWR)
		except Exception, e:
			LOG('Server', repr(e))
			
		LOG('Server', 'the end of the socket server thread')
		self.socket.close()

	def guiTimerHandler(self):
		LOG('Server', 'timer message - update drone status')

		if drone_list:
			for drone_in_list in drone_list[:]:
				droneSocket = drone_in_list.getSocket()
				try:
					droneSocket.send('status\t')
				except Exception, e:
					LOG('Server', repr(e))
					droneSocket.shutdown(socket.SHUT_RDWR)
					connection_list.remove(droneSocket)
					drone_list.remove(drone_in_list)
					drone_in_list.__del__()
			output = 'broadcast status report request to every drone'
			LOG('Server', output)
			self.signal.emit(output)

	def guiLaunchHandler(self, msg):
		LOG('Server', 'Launch message')
		droneID = int(msg[2])

		for drone_in_list in drone_list:
			if drone_in_list.getId() == droneID:
				break
		else:
			LOG('Server', 'cannot find drone ' + str(droneID))
			return

		droneSocket = drone_in_list.getSocket()
		message = 'launch'
		LOG('Server', 'send a message to drone ' + str(droneID) + ': ' + message)
		try:
			droneSocket.send(message + '\t')
		except Exception, e:
			LOG('Server', repr(e))
			droneSocket.shutdown(socket.SHUT_RDWR)
			connection_list.remove(droneSocket)
			drone_list.remove(drone_in_list)
			drone_in_list.__del__()
			return

		output = ('Drone %d launch' % droneID)
		LOG('Server', output)
		self.signal.emit(output)

	def guiLandingHandler(self, msg):
		LOG('Server', 'Landing message')

		droneID = int(msg[2])

		for drone_in_list in drone_list:
			if drone_in_list.getId() == droneID:
				break
		else:
			LOG('Server', 'cannot find drone ' + str(droneID))
			return

		droneSocket = drone_in_list.getSocket()
		message = 'landing'
		LOG('Server', 'send a message to drone ' + str(droneID) + ': ' + message)
		try:
			droneSocket.send(message + '\t')
		except Exception, e:
			LOG('Server', repr(e))
			droneSocket.shutdown(socket.SHUT_RDWR)
			connection_list.remove(droneSocket)
			drone_list.remove(drone_in_list)
			drone_in_list.__del__()
			return

		output = ('Drone %d landing' % droneID)
		LOG('Server', output)
		self.signal.emit(output)

	def guiGoHomeHandler(self, msg):
		LOG('Server', 'GoHome message')

		droneID = int(msg[2])

		for drone_in_list in drone_list:
			if drone_in_list.getId() == droneID:
				break
		else:
			LOG('Server', 'cannot find drone ' + str(droneID))
			return

		droneSocket = drone_in_list.getSocket()
		message = 'gohome'
		LOG('Server', 'send a message to drone ' + str(droneID) + ': ' + message)
		try:
			droneSocket.send(message + '\t')
		except Exception, e:
			LOG('Server', repr(e))
			droneSocket.shutdown(socket.SHUT_RDWR)
			connection_list.remove(droneSocket)
			drone_list.remove(drone_in_list)
			drone_in_list.__del__()
			return

		output = ('Drone %d gohome' % droneID)
		LOG('Server', output)
		self.signal.emit(output)
	

	def guiRelocationHandler(self, msg):
		LOG('Server', 'relocation message')
		droneID = int(msg[2])
		x = msg[3]
		y = msg[4]
		z = msg[5]
									
		for drone_in_list in drone_list:
			if drone_in_list.getId() == droneID:
				break
		else:
			LOG('Server', 'cannot find drone ' + str(droneID))
			return

		droneSocket = drone_in_list.getSocket()
		message = 'relocation ' + x + ' ' + y + ' ' + z
		LOG('Server', 'send a message to drone ' + str(droneID) + ': '  + message)
		try:
			droneSocket.send(message + '\t')
		except Exception, e:
			LOG('Server', repr(e))
			droneSocket.shutdown(socket.SHUT_RDWR)
			connection_list.remove(droneSocket)
			drone_list.remove(drone_in_list)
			drone_in_list.__del__()
			return

		output = ('Drone relocation: drone %s (%s, %s, %s)' % (droneID, x, y, z))
		LOG('Server', output)
		self.signal.emit(output)
		

	def guiFrameHandler(self):
		output = ('GUI-server initialization complete')
		LOG('Server', output)
		self.signal.emit(output)
		
	def droneNewHandler(self, sock, msg):
		if msg[2] not in MAC_list:
			MAC_list.append(msg[2])
		droneID = MAC_list.index(msg[2]) + 1
		newDrone = Drone(socket = sock, id = droneID)
		drone_list.append(newDrone)

		output = ('Drone %d: connected' % droneID)
		LOG('Server', output)
		self.signal.emit(output)

		output2 = ('new %d' % droneID)
		self.signal.emit(output2)

	def droneStatusHandler(self, sock, msg):
		for drone_in_list in drone_list:
			if drone_in_list.getSocket() == sock:
				break
		else:
			return

		drone_in_list.setLocation(float(msg[2]), float(msg[3]), float(msg[4]))
		drone_in_list.setMAC(msg[5])

		for i in range(6, len(msg)):
			if msg[i] not in drone_in_list.neighborList:
				drone_in_list.neighborList.append(msg[i])

		droneID = drone_in_list.getId()
		if (len(drone_in_list.neighborList) == 1):
			output = ('Drone %d (%s, %s, %s) has %d neighbor' % (droneID, msg[2], msg[3], msg[4], len(drone_in_list.neighborList)))
		else:
			output = ('Drone %d (%s, %s, %s) has %d neighbors' % (droneID, msg[2], msg[3], msg[4], len(drone_in_list.neighborList)))
		LOG('Server', output)
		self.signal.emit(output)

class Drone:
	def __init__(self, socket = -1, id = -1):
		self.socket   = socket
		self.id       = id
		self.location = (0., 0., 0.)
		self.mac = ''
		self.neighborList = []
				
	def getId(self):
		return self.id

	def getSocket(self):
		return self.socket

	def getLocation(self):
		return self.location

	def setLocation(self, x, y, z):
		self.location = (x, y, z)

	def getMAC(self):
		return self.mac

	def setMAC(self, mac):
		self.mac = mac

	def __del__(self):
		print 'drone ', self.id, 'class object destroyed'

""" Customized GUI classes """
class RelocDialog(QDialog):
	def __init__(self, sock):
		super(RelocDialog, self).__init__()

		self.sock = sock

		relocLayout = QGridLayout()
		labelX = QLabel('X')
		labelY = QLabel('Y')
		labelZ = QLabel('Z')
		labelDrone = QLabel('Drone')
		self.relocX = QLineEdit()
		self.relocY = QLineEdit()
		self.relocZ = QLineEdit()
		self.droneListCombo = QComboBox()
		okBtn = QPushButton('OK')



		global drone_list
		for drone in drone_list:
			self.droneListCombo.addItem(str(drone.getId()))
			print drone.getId()

		global curCoordinate
		self.relocX.setText(curCoordinate[0])
		self.relocY.setText(curCoordinate[1])

		relocLayout.addWidget(labelX, 1, 0)
		relocLayout.addWidget(self.relocX, 1, 1)
		relocLayout.addWidget(labelY, 2, 0)
		relocLayout.addWidget(self.relocY, 2, 1)
		relocLayout.addWidget(labelZ, 3, 0)
		relocLayout.addWidget(self.relocZ, 3, 1)
		relocLayout.addWidget(labelDrone, 4, 0)
		relocLayout.addWidget(self.droneListCombo, 4, 1)
		relocLayout.addWidget(okBtn, 5, 0, 1, 2)

		okBtn.clicked.connect(self.on_ok)

		self.setLayout(relocLayout)

	def on_ok(self):
		global drone_list
		droneID = self.droneListCombo.currentText()

		for drone_in_list in drone_list:
			if drone_in_list.getId() == int(droneID):
				break
		else:
			return

		x = self.relocX.text()
		y = self.relocY.text()
		z = self.relocZ.text()

		message = ('gui relocation %s %s %s %s' % (droneID, x, y, z))
		LOG('Relocation', 'send a message to the socket server thread: ' + message)

		try:
			self.sock.send(message + '\t')
		except Exception, e:
			LOG('Relocation', repr(e))
			self.sock.shutdown(socket.SHUT_RDWR)
			connection_list.remove(self.sock)
			self.__del__()
		self.close()


class CmdLayout(QVBoxLayout):
	def __init__(self, sock):
		super(CmdLayout, self).__init__()
		self.sock = sock

		commandLabel = QLabel('Command')
		launchBtn = QPushButton('Launch')
		relocBtn = QPushButton('Relocation')
		landBtn = QPushButton('Land')
		goHomeBtn = QPushButton('Go Home')
		self.gcsLocationBtn = QPushButton('GCS Location set')
		self.droneListCombo = QComboBox()

		droneSelectLabel = QLabel('Drone: ')
		latLabel = QLabel('Lat: ')
		lngLabel = QLabel('Lng: ')
		hgtLabel = QLabel('Hgt: ')
		self.latText = QLineEdit()
		self.lngText = QLineEdit()
		self.hgtText = QLineEdit()
		droneSelectLayout= QHBoxLayout()
		latLayout = QHBoxLayout()
		lngLayout = QHBoxLayout()
		hgtLayout = QHBoxLayout()

		droneSelectLayout.addWidget(droneSelectLabel)
		droneSelectLayout.addWidget(self.droneListCombo)

		latLayout.addWidget(latLabel)
		latLayout.addWidget(self.latText)

		lngLayout.addWidget(lngLabel)
		lngLayout.addWidget(self.lngText)

		hgtLayout.addWidget(hgtLabel)
		hgtLayout.addWidget(self.hgtText)

		launchLayout = QHBoxLayout()
		launchLayout.addWidget(self.droneListCombo)
		launchLayout.addWidget(launchBtn)
		
		self.addWidget(commandLabel)
		self.addLayout(droneSelectLayout)
		self.addLayout(latLayout)
		self.addLayout(lngLayout)
		self.addLayout(hgtLayout)
		self.addWidget(launchBtn)
		self.addWidget(relocBtn)
		self.addWidget(landBtn)
		self.addWidget(goHomeBtn)
		self.addWidget(self.gcsLocationBtn)

		launchBtn.clicked.connect(self.on_launch)
		landBtn.clicked.connect(self.on_landing)
		relocBtn.clicked.connect(self.on_relocation)
		goHomeBtn.clicked.connect(self.on_go_home)
		self.gcsLocationBtn.clicked.connect(self.on_gcs_location)

	def update_drone_list(self, msg_):

		print "dron update msg: " + str(msg_)

		msg = str(msg_).split()

		droneID = msg[1]

		if msg[0] == "new":
			self.droneListCombo.addItem(msg[1])
		elif msg[0] == "closed":
			for i in range(self.droneListCombo.count()):
				if self.droneListCombo.itemText(i) == droneID:
					self.droneListCombo.removeItem(i)
					break
		else:
			LOG('Command', 'wrong input to update_drone_list')

	def on_launch(self, event):
		global drone_list
		droneID = self.droneListCombo.currentText()

		for drone_in_list in drone_list:
			if drone_in_list.getId() == int(droneID):
				break
		else:
			LOG('Launch', 'wrong drone ID')
			return

		LOG('Command', 'button event - launch')
		message = 'gui launch %s' % droneID
		LOG('Launch', 'send a message to the socket server thread: ' + message)
		try:
			self.sock.send(message + '\t')
		except Exception, e:
			LOG('Launch', repr(e))
			self.sock.shutdown(socket.SHUT_RDWR)
			connection_list.remove(self.sock)
			self.__del__()

	def on_relocation(self):
		global drone_list
		droneID = self.droneListCombo.currentText()

		for drone_in_list in drone_list:
			if drone_in_list.getId() == int(droneID):
				break
		else:
			LOG('Relocation', 'wrong drone ID')
			return

		lat = self.latText.text()
		lng = self.lngText.text()
		hgt = self.hgtText.text()

		message = ('gui relocation %s %s %s %s' % (droneID, lat, lng, hgt))
		LOG('Relocation', 'send a message to the socket server thread: ' + message)

		try:
			self.sock.send(message + '\t')
		except Exception, e:
			LOG('Relocation', repr(e))
			self.sock.shutdown(socket.SHUT_RDWR)
			connection_list.remove(self.sock)
			self.__del__()

	def on_landing(self):
		global drone_list
		droneID = self.droneListCombo.currentText()

		for drone_in_list in drone_list:
			if drone_in_list.getId() == int(droneID):
				break
		else:
			return

		message = ('gui landing %s ' % (droneID))
		LOG('Landing', 'send a message to the socket server thread: ' + message)

		try:
			self.sock.send(message + '\t')
		except Exception, e:
			LOG('Relocation', repr(e))
			self.sock.shutdown(socket.SHUT_RDWR)
			connection_list.remove(self.sock)
			self.__del__()

	def on_go_home(self):
		global drone_list
		droneID = self.droneListCombo.currentText()

		for drone_in_list in drone_list:
			if drone_in_list.getId() == int(droneID):
				break
		else:
			return

		message = ('gui gohome %s ' % (droneID))
		LOG('Go Home', 'send a message to the socket server thread: ' + message)

		try:
			self.sock.send(message + '\t')
		except Exception, e:
			LOG('Go Home', repr(e))
			self.sock.shutdown(socket.SHUT_RDWR)
			connection_list.remove(self.sock)
			self.__del__()

	def on_gcs_location(self):
		self.gcsLocationBtn.setEnabled(False)

	def is_gcs_location_enabled(self):
		return self.gcsLocationBtn.isEnabled()

	def set_location(self, lat, lng):
		self.latText.setText(lat)
		self.lngText.setText(lng)

	def set_marker(self, droneID):
		for i in range(self.droneListCombo.count()):
			if self.droneListCombo.itemText(i) == droneID:
				self.droneListCombo.setCurrentIndex(i)
				break

		drone = drone_by_id(droneID)
		hgt = drone.getLocation[2]
		self.hgtText.setText(hgt)


class HistoryLayout(QVBoxLayout):

	def __init__(self):
		super(HistoryLayout, self).__init__()
		historyLabel = QLabel('history')
		self.historyTextbox = QTextEdit()
		self.historyTextbox.setReadOnly(True)
		self.addWidget(historyLabel)
		self.addWidget(self.historyTextbox)

	def update_history_display(self, msg):
		self.historyTextbox.append(str(ctime()) + ' ' + msg + '\n')

	def get_signal(self):
		return self.historySignal

class DroneStatusLayout(QVBoxLayout):
	def __init__(self):
		super(DroneStatusLayout, self).__init__()
		self.statusLabel = QLabel('Status')
		self.coordinateLabel = QLabel('Coornidate')
		self.statusTextbox = QTextEdit()
		self.statusTextbox.setReadOnly(True)
		self.addWidget(self.statusLabel)
		self.addWidget(self.statusTextbox, 2)

	def update_coordinate(self, msg):
		self.coordinateTextbox.setText(msg)

	def update_info_window(self, droneID, dist):
		drone = drone_by_id(droneID)

		if drone != None:
			location = drone.getLocation()
			infoString = """
id: %s
lat: %s
lng: %s
hgt: %s
from gcs: %sm
neighbors: 
		""" % (droneID, location[0], location[1], location[2], dist)
		else:
			infoString = "Drone %s does not exist." % droneID

		self.statusTextbox.setText(infoString)


class JSCommunicator(QObject):
	def __init__(self, signal):
		super(JSCommunicator, self).__init__()

		self.signal = signal

	@pyqtSlot(str)
	def emit_signal(self, msg):
		self.signal.emit(msg)


class GMapWebView(QWebView):

	def __init__(self, signal):
		super(GMapWebView, self).__init__()
		file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "gmap-drone.html"))
		local_url = QUrl.fromLocalFile(file_path)
		self.load(local_url)

		self.signal = signal
		self.jsCommunicator = JSCommunicator(self.signal)

		self.frame = self.page().mainFrame()
		self.frame.addToJavaScriptWindowObject('jsCommunicator', self.jsCommunicator)

	def update_gmap(self):
		global drone_list
		LOG('GUI', 'update gmap')

		for drone in drone_list:
			droneID = drone.getId()
			location = drone.getLocation()
			infoString = self.build_info_string(drone)
			self.update_marker(droneID, location, str(infoString))

		for drone in drone_list:
			self.remove_all_lines()
			maclist = ""
			for mac in drone.neighborList:
				maclist = maclist + mac

			for neighbor in drone.neighborList:

				nbrDrone = drone_by_mac(neighbor)

				if nbrDrone != None:
					print "nbr found: " + str(nbrDrone.getMAC())
					self.draw_line(drone.getLocation(), nbrDrone.getLocation())
				else:
					print "		drone by mac none"


	def update_marker(self, droneID, location, infoString):
		self.frame.evaluateJavaScript('update_marker(%s, %s, %s);' % (droneID, location[0], location[1]))

	def remove_marker(self, droneID):
		self.frame.evaluateJavaScript('remove_marker(%s);' % (droneID))

	def remove_all_markers(self):
		self.frame.evaluateJavaScript('remove_all_markers();')

	def draw_line(self, start, end):
		self.frame.evaluateJavaScript('draw_line(%s, %s, %s, %s);' % (start[0], start[1], end[0], end[1]))

	def remove_all_lines(self):
		self.frame.evaluateJavaScript('remove_all_lines();')

	def build_info_string(self, drone):
		ret = ""

		for neighborMac in drone.neighborList:
			neighbor = drone_by_mac(neighborMac)
			if neighbor != None:
				ret = ret + str(neighbor.getId())

		if ret == "":
			ret = "No neighbor"

		return ret

	def mark_gcs_position(self, lat, lng):
		self.frame.evaluateJavaScript('mark_gcs_position(%s, %s)' % (lat, lng))
		print lat, lng


class MainFrame(QWidget):

	serverSignal = pyqtSignal(str)
	jsSignal = pyqtSignal(str)

	def __init__(self):
		super(MainFrame, self).__init__()

		self.serverSignal.connect(self.server_signal_handler)
		self.jsSignal.connect(self.js_signal_handler)

		# a socket to send message from GUI frame to the socket server
		self.setWindowTitle('Ground Control Station')
		self.guiClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self.grid = QGridLayout()
		self.gmap = GMapWebView(self.jsSignal)

		self.statusLayout = DroneStatusLayout()
		self.historyLayout = HistoryLayout()
		self.commandLayout = CmdLayout(self.guiClient)

		self.grid.addWidget(self.gmap, 0, 0, 5, 10)
		self.grid.addLayout(self.historyLayout, 5, 0, 2, 10)
		self.grid.addLayout(self.statusLayout, 0, 10, 5, 3)
		self.grid.addLayout(self.commandLayout, 5, 10, 2, 3)

		self.setLayout(self.grid)

		try:
			self.server = ServerThread(self.serverSignal)
		except ValueError as e:
			LOG('GUI Frame', repr(e))
			sys.exit()
		self.server.start()

		self.show()

		LOG('GUI Frame', 'try to connect to the socket server thread')
		try:
			self.guiClient.connect(ADDR)
			self.guiClient.send('gui frame\t')
		except Exception, e:
			LOG('GUI Frame', repr(e))
			sys.exit()

		# timer to generate status-report request periodically
		self.timer = QTimer()
		self.timer.timeout.connect(self.timeout)
		self.timer.start(PERIOD)

	def timeout(self):
		message = "gui timer"
		LOG('GUI Frame', 'timer event - send a message to the socket server thread: ' + message)
		try:
			self.guiClient.send(message + '\t')
		except Exception, e:
			LOG('GUI Frame', repr(e))

		self.gmap.update_gmap()

	def server_signal_handler(self, msg_):


		msg = str(msg_).split()
		
		if msg[0] == "new":
			self.commandLayout.update_drone_list(msg_)
		elif msg[0] == "closed":
			self.commandLayout.update_drone_list(msg_)
			self.gmap.remove_marker(msg[1])
		else:
			self.historyLayout.update_history_display(msg_)

	def js_signal_handler(self, msg_):

		msg = str(msg_).split()

		if msg[0] == "marker_click_event":
			self.statusLayout.update_info_window(msg[1], msg[2])
			self.commandLayout.set_marker(msg[1])

		elif msg[0] == "map_click_event":
			if not self.commandLayout.is_gcs_location_enabled():
				self.commandLayout.gcsLocationBtn.setEnabled(True)
				self.gmap.mark_gcs_position(msg[1], msg[2])
			self.commandLayout.set_location(msg[1], msg[2])

		
if __name__ == '__main__':
	app = QApplication(sys.argv)
	frame = MainFrame()
	sys.exit(app.exec_())