import sys, os

from PyQt4.QtGui import QApplication
# from PyQt4.QtCore import QUrl, QTimer, QObject, pyqtSignal
from PyQt4.QtCore import *
from PyQt4.QtWebKit import QWebView, QWebPage
from PyQt4.QtGui import QComboBox, QFrame, QSizePolicy, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QWidget, QHeaderView, QPushButton, QTextEdit, QLabel
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest

import select
import socket
import weakref
from threading import Thread
from time import ctime
import sys

''' Global variables -------------------------------------------------------'''

HOST    = '127.0.0.1'
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

minX=0
minY=0
maxX=0
maxY=0
dcWidth=0
dcHeight=0

def LOG(logger, msg):
	print str(ctime()) + ' [' + logger + '] ' + msg

_emitterCache = weakref.WeakKeyDictionary()

''' Server thread class ----------------------------------------------------'''

class ServerThread(Thread):
	def __init__(self):
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
										self.guiLaunchHandler()
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
								# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
								QObject.emit(SIGNAL("updateHistory"), output)

							else:
								output = ('GUI-server connection closed')
								LOG('Server', output)
								# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
								QObject.emit(SIGNAL("updateHistory"), output)

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
			# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
			QObject.emit(SIGNAL("updateHistory"), output)

	def guiLaunchHandler(self):
		LOG('Server', 'Launch message')
		for drone_in_list in drone_list[:]:
			droneID = drone_in_list.getId()
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

		output = ('Drone launch')
		LOG('Server', output)
		# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
		QObject.emit(SIGNAL("updateHistory"), output)

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
		# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
		QObject.emit(SIGNAL("updateHistory"), output)
	

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
		# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
		QObject.emit(SIGNAL("updateHistory"), output)
		

	def guiFrameHandler(self):
		output = ('GUI-server initialization complete')
		LOG('Server', output)
		# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
		QObject.emit(SIGNAL("updateHistory"), output)
		
	def droneNewHandler(self, sock, msg):
		if msg[2] not in MAC_list:
			MAC_list.append(msg[2])
		droneID = MAC_list.index(msg[2]) + 1
		newDrone = Drone(socket = sock, id = droneID)
		drone_list.append(newDrone)

		output = ('Drone %d: connected' % droneID)
		LOG('Server', output)
		# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
		QObject.emit(SIGNAL("updateHistory"), output)

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
		# wx.CallAfter(Publisher().sendMessage, "updateHistory", output)
		QObject.emit(SIGNAL("updateHistory"), output)

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

class CmdLayout(QVBoxLayout):
	def __init__(self, sock):
		super(CmdLayout, self).__init__()
		self.sock = sock

		commandLabel = QLabel('Command')
		launchBtn = QPushButton('Launch')
		relocBtn = QPushButton('Relocation')
		landBtn = QPushButton('Land')
		relocLayout = QHBoxLayout()
		labelX = QLabel('X')
		labelY = QLabel('Y')
		labelZ = QLabel('Z')
		relocX = QLineEdit()
		relocY = QLineEdit()
		relocZ = QLineEdit()
		droneListCombo = QComboBox()

		droneListCombo.addItem('hello')
		droneListCombo.addItem('hello')
		droneListCombo.addItem('hello')

		relocLayout.addWidget(labelX)
		relocLayout.addWidget(relocX)
		relocLayout.addWidget(labelY)
		relocLayout.addWidget(relocY)
		relocLayout.addWidget(labelZ)
		relocLayout.addWidget(relocZ)

		launchLandLayout = QHBoxLayout()
		launchLandLayout.addWidget(launchBtn)
		launchLandLayout.addWidget(landBtn)

		self.addWidget(commandLabel)
		self.addLayout(launchLandLayout)
		self.addWidget(droneListCombo)
		self.addLayout(relocLayout)
		self.addWidget(relocBtn)
		

		launchBtn.clicked.connect(self.on_launch)
		landBtn.clicked.connect(self.on_relocation)
		relocBtn.clicked.connect(self.on_landing)

	def update_drone_list(self):
		pass

	def on_launch(self, event):
			LOG('Command', 'button event - launch')
			message = 'gui launch'
			LOG('Launch', 'send a message to the socket server thread: ' + message)
			try:
				self.sock.send(message + '\t')
			except Exception, e:
				LOG('Launch', repr(e))
				self.sock.shutdown(socket.SHUT_RDWR)
				connection_list.remove(self.sock)
				self.__del__()

	def on_relocation(self):
		pass

	def on_landing(self):
		pass

class HistoryLayout(QVBoxLayout):
	def __init__(self):
		super(HistoryLayout, self).__init__()
		historyLabel = QLabel('history')
		historyTextbox = QTextEdit()
		historyTextbox.setReadOnly(True)
		self.addWidget(historyLabel)
		self.addWidget(historyTextbox)

		self.connect(self, SIGNAL("updateHistory(QString&)"), self.update_history_display)

	def update_history_display(self, msg):
		self.historyTextbox.appendText(str(ctime()) + ' ' + str(msg.data) + '\n')

class DroneStatusLayout(QVBoxLayout):
	def __init__(self):
		super(DroneStatusLayout, self).__init__()
		statusLabel = QLabel('Status')
		statusTextbox = QTextEdit()
		statusTextbox.setReadOnly(True)
		self.addWidget(statusLabel)
		self.addWidget(statusTextbox)

	def update_drone_list(self, msg):
		pass

class MainFrame(QWidget):
	def __init__(self):
		super(MainFrame, self).__init__()
		# a socket to send message from GUI frame to the socket server
		self.guiClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self.grid = QGridLayout()
		self.browser = QWebView()

		self.commandLayout = CmdLayout(1)
		self.statusLayout = DroneStatusLayout()
		self.historyLayout = HistoryLayout()

		self.button = QPushButton('js')
		self.grid.addWidget(self.browser, 1, 0, 2, 1)
		self.grid.addLayout(self.historyLayout, 3, 0)
		self.grid.addLayout(self.statusLayout, 1, 1)
		self.grid.addLayout(self.commandLayout, 2, 1)
		self.grid.addWidget(self.button, 3, 1)

		self.button.clicked.connect(self.eval_js)
		self.setLayout(self.grid)

		file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "googlemap.html"))
		local_url = QUrl.fromLocalFile(file_path)
		self.browser.load(local_url)

		try:
			self.server = ServerThread()
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
		self.timer.start(1000)

	def timeout(self):
		message = "gui timer"
		LOG('GUI Frame', 'timer event - send a message to the socket server thread: ' + message)
		try:
			self.guiClient.send(message + '\t')
		except Exception, e:
			LOG('GUI Frame', repr(e))

	def eval_js(self):
		frame = self.browser.page().mainFrame()
		lat = 36.374383
		lng = 127.365327
		frame.evaluateJavaScript('change_pos(%.6f, %.6f);' % (lat, lng))

		


if __name__ == '__main__':
	app = QApplication(sys.argv)
	frame = MainFrame()
	sys.exit(app.exec_())