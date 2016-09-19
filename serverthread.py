import sys, os

from PyQt4.QtGui import QApplication
# from PyQt4.QtCore import QUrl, QTimer, QObject, pyqtSignal
from PyQt4.QtCore import *
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtGui import QDialog, QComboBox, QFrame, QSizePolicy, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QWidget, QHeaderView, QPushButton, QTextEdit, QLabel
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest

import select
import socket
import weakref
from threading import Thread
from time import ctime
import sys

''' Global variables -------------------------------------------------------'''

HOST    = '10.10.0.103'
PORT    = 56789
ADDR    = (HOST, PORT)
BUFSIZE = 1024
PERIOD  = 1000  # msec - send status report request to every drone periodically
DEFAULT_SIZE = (800, 700) # default window size
drone_list = [] # list of the connected drones
MAC_list = [] # list of the MAC address of all drone clients
selected_drone = []
STATUS_OUTPUT = 'select a drone\n'
droneSize = 30
curCoordinate = ("0", "0")

minX=0
minY=0
maxX=0
maxY=0
dcWidth=0
dcHeight=0

def LOG(logger, msg):
	print str(ctime()) + ' [' + logger + '] ' + msg

# Emitter hack for emitting from non-QObject
_emitterCache = weakref.WeakKeyDictionary()

def emitter(ob):
	if ob not in _emitterCache:
		_emitterCache[ob] = QObject()
	return _emitterCache[ob]

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
										self.guiLandingHandler()
									elif msg[1] == 'relocation':
										self.guiRelocationHandler(msg)
									elif msg[1] == 'videoShare':
										self.guiVideoShareHandler(msg)
									elif msg[1] == 'frame':
										self.guiFrameHandler()
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

		# for drone_in_list in drone_list[:]:
		# 	droneID = drone_in_list.getId()
		# 	droneSocket = drone_in_list.getSocket()
		# 	message = 'launch'
		# 	LOG('Server', 'send a message to drone ' + str(droneID) + ': ' + message)
		# 	try:
		# 		droneSocket.send(message + '\t')
		# 	except Exception, e:
		# 		LOG('Server', repr(e))
		# 		droneSocket.shutdown(socket.SHUT_RDWR)
		# 		connection_list.remove(droneSocket)
		# 		drone_list.remove(drone_in_list)
		# 		drone_in_list.__del__()
		# 		return

		output = ('Drone %d launch' % droneID)
		LOG('Server', output)
		self.signal.emit(output)

	def guiLandingHandler(self):
		LOG('Server', 'Landing message')
		for drone_in_list in drone_list[:]:
			droneID = drone_in_list.getId()
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

		output = ('Drone landing')
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
	def __init__(self, sock, signal):
		super(CmdLayout, self).__init__()
		self.sock = sock
		self.signal = signal

		commandLabel = QLabel('Command')
		launchBtn = QPushButton('Launch')
		relocBtn = QPushButton('Relocation')
		landBtn = QPushButton('Land')
		self.droneListCombo = QComboBox()

		launchLayout = QHBoxLayout()
		launchLayout.addWidget(self.droneListCombo)
		launchLayout.addWidget(launchBtn)
		
		self.addWidget(commandLabel)
		self.addLayout(launchLayout)
		self.addWidget(relocBtn)
		self.addWidget(landBtn)

		launchBtn.clicked.connect(self.on_launch)
		landBtn.clicked.connect(self.on_landing)
		relocBtn.clicked.connect(self.on_relocation)

		# self.timer = QTimer()
		# self.timer.timeout.connect(self.update_drone_list)
		# self.timer.start(PERIOD)

	def update_drone_list(self):
		self.droneListCombo.clear()
		global drone_list
		for drone in drone_list:
			self.droneListCombo.addItem(str(drone.getId()))
			print drone.getId()

	def on_launch(self, event):
		global drone_list
		droneID = self.droneListCombo.currentText()

		for drone_in_list in drone_list:
			if drone_in_list.getId() == int(droneID):
				break
		else:
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
		print 'hello!!!'
		relocDialog = RelocDialog(self.sock)
		relocDialog.exec_()

	def on_landing(self):
		print 'hello!'
		self.signal.emit('hello')

class HistoryLayout(QVBoxLayout):

	historySignal = pyqtSignal(str)

	def __init__(self):
		super(HistoryLayout, self).__init__()
		historyLabel = QLabel('history')
		self.historyTextbox = QTextEdit()
		self.historyTextbox.setReadOnly(True)
		self.addWidget(historyLabel)
		self.addWidget(self.historyTextbox)

		self.historySignal.connect(self.update_history_display)

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
		self.coordinateTextbox = QTextEdit()
		self.coordinateTextbox.setReadOnly(True)
		self.addWidget(self.statusLabel)
		self.addWidget(self.statusTextbox, 2)
		self.addWidget(self.coordinateLabel)
		self.addWidget(self.coordinateTextbox, 1)

		# self.timer = QTimer()
		# self.timer.timeout.connect(self.update_drone_list)
		# self.timer.start(PERIOD)


	def update_drone_list(self):
		global STATUS_OUTPUT, selected_drone
		for drone in selected_drone:
			location = drone.getLocation()
			STATUS_OUTPUT += ('Drone %d\n- latitude: %s\n- longitude: %s\n- altitude: %s\n' % (drone.getId(), location[0], location[1], location[2]))

		self.statusTextbox.clear()
		self.statusTextbox.setText(STATUS_OUTPUT)
		STATUS_OUTPUT = ''

	def update_coordinate(self):
		global curCoordinate
		self.coordinateTextbox.clear()
		text = "lat: " + str(curCoordinate[0]) + "\nlng: " + str(curCoordinate[1])
		self.coordinateTextbox.setText(text)

class CoordinateUpdater(QObject):
	def __init__(self):
		super(CoordinateUpdater, self).__init__()

	@pyqtSlot(str, str)
	def update(self, lat, lng):
		global curCoordinate
		curCoordinate = (lat, lng)


class GMapWebView(QWebView):

	def __init__(self):
		super(GMapWebView, self).__init__()
		file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "gmap-drone.html"))
		local_url = QUrl.fromLocalFile(file_path)
		self.load(local_url)

		# self.timer = QTimer()
		# self.timer.timeout.connect(self.update_gmap)
		# self.timer.start(PERIOD)

		self.coordinateUpdater = CoordinateUpdater()

		self.frame = self.page().mainFrame()
		self.frame.addToJavaScriptWindowObject('coordinateUpdater', self.coordinateUpdater)

	def update_gmap(self):
		global drone_list
		# print '		gmap update!'
		LOG('GUI', 'update gmap')

		# self.remove_all_markers()

		for drone in drone_list:
			# self.remove_all_markers()
			droneID = drone.getId()
			location = drone.getLocation()
			infoString = self.build_info_string(drone)
			self.update_marker(droneID, location, str(infoString))

		for drone in drone_list:
			self.remove_all_lines()
			maclist = ""
			for mac in drone.neighborList:
				maclist = maclist + mac

			print "maclist: " + maclist

			for neighbor in drone.neighborList:

				nbrDrone = drone_by_mac(neighbor)

				if nbrDrone != None:
					print "nbr found: " + str(nbrDrone.getMAC())
					self.draw_line(drone.getLocation(), nbrDrone.getLocation())
				else:
					print "		drone by mac none"


	def update_marker(self, droneID, location, infoString):
		# print "info string: " + infoString
		# print " ".join([str(droneID), str(location[0]), str(location[1]), str(infoString)])
		self.frame.evaluateJavaScript('update_marker(%s, %s, %s);' % (str(droneID), str(location[0]), str(location[1])))

	def remove_marker(self, droneID):
		self.frame.evaluateJavaScript('remove_marker(%s);' % (droneID))

	def remove_all_markers(self):
		self.frame.evaluateJavaScript('remove_all_markers();')

	def draw_line(self, start, end):
		# print " ".join([str(start[0]), start[1], end[0], end[1]])
		self.frame.evaluateJavaScript('draw_line(%s, %s, %s, %s);' % (start[0], start[1], end[0], end[1]))

	def remove_all_lines(self):
		self.frame.evaluateJavaScript('remove_all_lines();')

	def build_info_string(self, drone):
		ret = ""

		for neighborMac in drone.neighborList:
			neighbor = drone_by_mac(neighborMac)
			if neighbor != None:
				ret = ret + str(neighbor.getId())

		return ret



class MainFrame(QWidget):
	def __init__(self):
		super(MainFrame, self).__init__()
		# a socket to send message from GUI frame to the socket server
		self.setWindowTitle('Ground Control Station')
		self.guiClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self.grid = QGridLayout()
		self.gmap = GMapWebView()

		self.statusLayout = DroneStatusLayout()
		self.historyLayout = HistoryLayout()
		self.commandLayout = CmdLayout(self.guiClient, self.historyLayout.get_signal())

		self.grid.addWidget(self.gmap, 1, 0, 2, 1)
		self.grid.addLayout(self.historyLayout, 3, 0)
		self.grid.addLayout(self.statusLayout, 1, 1)
		self.grid.addLayout(self.commandLayout, 2, 1)

		self.setLayout(self.grid)

		try:
			self.server = ServerThread(self.historyLayout.get_signal())
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
		self.commandLayout.update_drone_list()
		self.statusLayout.update_coordinate()



		
if __name__ == '__main__':
	app = QApplication(sys.argv)
	frame = MainFrame()
	sys.exit(app.exec_())