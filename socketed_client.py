#!/usr/bin/env python


import socket
import subprocess
from threading import Thread
from time import ctime, sleep
import threading

from dji_sdk.dji_drone import DJIDrone
import dji_sdk.msg 
import time
import sys
import math

HOST = '10.10.0.111'
PORT = 56789
ADDR = (HOST, PORT)
BUFSIZE = 1024

launchFlag = False
relocationFlag = False
landingFlag = False
gohomeFlag = False

KEEP_CONNECT = True

statusLock = threading.Lock()
launchLock = threading.Lock()
relocationLock = threading.Lock()
landingLock = threading.Lock()
gohomeLock = threading.Lock()

curX = 0.
curY = 0.
curZ = 0.

dstX = 0.
dstY = 0.
dstZ = 0.


Done = False

drone = DJIDrone()

def LOG(logger, msg):
	print str(ctime()) + ' [' + logger + '] ' + msg

class M100Thread(Thread):
	def __init__(self):
		global curX, curY, curZ

		Thread.__init__(self)
		LOG('M100', 'Initialize drone control system...')

		self.drone = DJIDrone()
		#while self.drone.sdk_permission_opened == False:
		#self.drone.request_sdk_permission_control()
		#time.sleep(0.5)

		curX = self.drone.global_position.latitude
		curY = self.drone.global_position.longitude
		curZ = self.drone.local_position.z

	def run(self):
		global curX, curY, curZ, dstX, dstY, dstZ
		global launchFlag, relocationFlag, landingFlag, gohomeFlag
		global Done

		while not Done:
			try:
				statusLock.acquire()
				curX = self.drone.global_position.latitude
				curY = self.drone.global_position.longitude
				curZ = self.drone.local_position.z
				statusLock.release()

				launchLock.acquire()

				if launchFlag:
                                        print '        launch pass'
					self.drone.request_sdk_permission_control()
					if self.drone.flight_status.data == 1:
						self.drone.takeoff()
					launchFlag = False
				launchLock.release()

				relocationLock.acquire()
				if relocationFlag:
					# call some function for moving the drone
					# "some function" not yet defined
					# self.drone.global_position_control(dstX, dstY, dstZ, 0)
					self.drone.request_sdk_permission_control()
					waypoint_task = dji_sdk.msg.MissionWaypointTask()
					waypoint1 = dji_sdk.msg.MissionWaypoint()
					waypoint2 = dji_sdk.msg.MissionWaypoint()

					del waypoint_task.mission_waypoint[:]

					waypoint_task.velocity_range = 2
					waypoint_task.idle_velocity = 1
					waypoint_task.action_on_finish = 0
					waypoint_task.mission_exec_times = 1
					waypoint_task.yaw_mode = 4
					waypoint_task.trace_mode = 0
					waypoint_task.action_on_rc_lost = 0
					waypoint_task.gimbal_pitch_mode = 0

					waypoint1.latitude = self.drone.global_position.latitude
					waypoint1.longitude = self.drone.global_position.longitude
					waypoint1.altitude = float(dstZ)
					waypoint1.damping_distance = 0
					waypoint1.target_yaw = 0
					waypoint1.target_gimbal_pitch = 0
					waypoint1.turn_mode = 0
					waypoint1.has_action = 0

					waypoint_task.mission_waypoint.append(waypoint1)

					waypoint2.latitude = float(dstX)
					waypoint2.longitude = float(dstY)
					waypoint2.altitude = float(dstZ)
					waypoint2.damping_distance = 0
					waypoint2.target_yaw = 0
					waypoint2.target_gimbal_pitch = 0
					waypoint2.turn_mode = 0
					waypoint2.has_action = 0

					waypoint_task.mission_waypoint.append(waypoint2)

					self.drone.mission_waypoint_upload(waypoint_task)
					
					time.sleep(0.5)
					if self.drone.global_position.health < 4 :
						print "Unreliable GPS!"
					else :
						self.drone.mission_start()

					relocationFlag = False
				relocationLock.release()

				landingLock.acquire()
				if landingFlag:
					self.drone.request_sdk_permission_control()
					if self.drone.flight_status.data == 3:
						self.drone.landing()
					landingFlag = False
				landingLock.release()

				gohomeLock.acquire()
				if gohomeFlag:
					if self.drone.flight_status.data == 3:
						self.drone.gohome()
					gohomeFlag = False
				gohomeLock.release()

				time.sleep(0.1)


			except Exception, e:
				LOG('M100', repr(e))
				self.destroy()
				break


	def destroy(self):
		if self.drone.flight_status.data == 3:
			self.drone.landing()
		if self.drone.flight_status.data == 1:
			self.drone.release_sdk_permission_control()


class ClientThread(Thread):
	def __init__(self):

		Thread.__init__(self)

		self.setDaemon(True)
		self.socket = None

		self.connect()		
		self.run()

	def connect(self):
		if self.socket:
			# self.socket.shutdown(socket.SHUT_RDWR)
			self.socket.close()
		while KEEP_CONNECT:
			sleep(1)
			try:
				LOG('Client', 'create socket')
				self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.socket.settimeout(5)
				LOG('Client', 'try to access to server')
				self.socket.connect(ADDR)
				break
			except KeyboardInterrupt:
				sys.exit()
			except Exception, e:
				if e.errno == 4:
					return
				LOG('Client', repr(e))
				LOG('Client', 'try to reconnect...')
			

	def register(self):
		batctlOut = subprocess.Popen(["sudo batctl o"], stdout=subprocess.PIPE, shell=True).communicate()[0]
		grepOut = subprocess.Popen(["grep '(bat0'"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True).communicate(input=batctlOut)[0]
		selfMac = subprocess.Popen(["awk '{print $5}'"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True).communicate(input=grepOut)[0]
		selfMac = selfMac.split('\n')
		selfMac.pop()
		selfMac = selfMac[0][6:]

		LOG('Client', 'send drone registration request to server')
		self.socket.send('drone new %s\t' %(selfMac))


	def run(self):

		global curX, curY, curZ, dstX, dstY, dstZ
		global launchFlag, relocationFlag, landingFlag, gohomeFlag
		batctlOut = subprocess.Popen(["sudo batctl o"], stdout=subprocess.PIPE, shell=True).communicate()[0]
		grepOut = subprocess.Popen(["grep '(bat0'"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True).communicate(input=batctlOut)[0]
		selfMac = subprocess.Popen(["awk '{print $5}'"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True).communicate(input=grepOut)[0]
		selfMac = selfMac.split('\n')
		selfMac.pop()
		selfMac = selfMac[0][6:]

		LOG('Client', 'send drone registration request to server')
		try:
			self.socket.send('drone new %s\t' %(selfMac))
		except KeyboardInterrupt:
				sys.exit()
		except Exception, e:
			if e.errno == 4:
				return
			LOG('Client', repr(e))
			self.connect()
		


		while True:
			try:
				batctlOut = subprocess.Popen(["sudo batctl o"], stdout=subprocess.PIPE, shell=True).communicate()[0]
				neighborMac_ = batctlOut.split("\n")[2:-1]
				neighborMac = ""
				for i in neighborMac_:
					i_split = i.split()

					if i_split[0] == i_split[3]:
						neighborMac = neighborMac + i_split[0] + " "

				neighborMac = neighborMac.rstrip()
					
				try:
					data = self.socket.recv(BUFSIZE)
				except KeyboardInterrupt:
					sys.exit()

				if not data:
					LOG('Client', 'the end of connection')
					self.connect()
					self.register()
					continue

				LOG('Client', 'received message from server: ' + data)

				msgList = data.split('\t')
				msgList.pop()
				for curMsg in msgList:
					msg = curMsg.split(' ')
					if msg[0] == 'status':
						LOG('Client', 'status report')
						statusLock.acquire()
						report = ('drone status %.6f %.6f %.6f %s' %(curX, curY, curZ, selfMac))
						statusLock.release()
						neighborMacList = neighborMac.split('\n')
						neighborMacList.pop()
						report = report + " " + neighborMac
						print "report: " + report
						try:
							self.socket.send(report + '\t')
						except KeyboardInterrupt:
							sys.exit()
						except Exception, e:
							if e.errno == 4:
								return
							LOG('Client', repr(e))
							self.socket.shutdown(socket.SHUT_RDWR)
							self.socket.close()
							return

					elif msg[0] == 'launch':
						LOG('Client', 'launch')
						launchLock.acquire()
						launchFlag = True
						launchLock.release()

					elif msg[0] == 'relocation':
						LOG('Client', 'relocation')
						relocationLock.acquire()
						dstX = float(msg[1])
						dstY = float(msg[2])
						dstZ = float(msg[3])
						relocationFlag = True
						relocationLock.release()
		
					elif msg[0] == 'landing':
						LOG('Client', 'landing')
						landingLock.acquire()
						landingFlag = True
						landingLock.release()

					elif msg[0] == 'gohome':
						LOG('Client', 'go home')
						gohomeLock.acquire()
						gohomeFlag = True
						gohomeLock.release()

					elif msg[0] == 'videoShare':
						LOG('Client', 'video share')

						dstAddr = msg[1]

						# share video (file) to the other
						# ...
						
						LOG('Client', 'video share to ' + dstAddr)

					else:
						print data

			except KeyboardInterrupt:
				sys.exit()

			except Exception, e:
				if e.errno == 4:
					return
				LOG('Client', repr(e))
				self.connect()
				self.register()
				print '		exception e asdlkfja;lskdjf;laks'

''' main start '''
if __name__ == '__main__':

	psOut = subprocess.Popen(["ps -al"], stdout=subprocess.PIPE, shell=True).communicate()[0]
	grepOut = subprocess.Popen(["grep 'roslaunch'"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True).communicate(input=psOut)[0]
	if not grepOut:
		LOG('Client', 'Roslaunch not running yet!\nLaunching ROS now')
		subprocess.Popen(["roslaunch dji_sdk sdk_manifold.launch"], stdout=subprocess.PIPE, shell=True).communicate()[0]
		time.sleep(1)

	M100thread = M100Thread()
	M100thread.start()

	clientthread = ClientThread()
	clientthread.socket.shutdown(socket.SHUT_RDWR)
	clientthread.socket.close()

	Done = True
	M100thread.join()

	sys.exit()
