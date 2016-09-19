#!/usr/bin/env python


import socket
import subprocess
from threading import Thread
from time import ctime
import threading

from dji_sdk.dji_drone import DJIDrone
import dji_sdk.msg 
import time
import sys
import math

def display_main_menu():
	print("+-------------------------- < Main menu > ------------------------+");
	print("| [a] Request Control           | [s]                             |");
	print("| [b] Release Control           | [t]                             |");    
	print("| [c] Takeoff                   | [u]                             |");    
	print("| [d] Landing                   | [v] Waypoint Mission Upload     |");    
	print("| [e] Go Home                   | [w]                             |");    
	print("| [f] Local Navi Test           | [x]                             |");    
	print("| [g] Global Navi Test          | [y] Mission Start               |");    
	print("| [h] Status Report             | [z] Mission Pause               |");    
	print("| [i]                           | [A] Mission Resume              |");    
	print("| [j] Local Velocity Test       | [B] Mission Cancel              |");    
	print("| [k] Global Velocity Test      | [C] Mission Waypoint Download   |");    
	print("| [l]                           | [D] Mission Waypoint Set Speed  |");     
	print("| [m]                           | [E] Mission Waypoint Get Speed  |");    
	print("| [n]                           | [F]                             |");    
	print("| [o]                           | [G]                             |");    
	print("| [p]                           | [H]                             |");    
	print("| [q] Exit                      | [I]                             |");    
	print("| [r]                           | [J]                             |");
	print("+-----------------------------------------------------------------+");
	print "\ninput a/b/c etc..then press enter key"
	print "\nuse `rostopic echo` to query drone status"
	print "----------------------------------------"
	print "input: "



HOST = '10.10.0.103'
PORT = 56789
ADDR = (HOST, PORT)
BUFSIZE = 1024

launchFlag = False
relocationFlag = False
landingFlag = False
gohomeFlag = False

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
#display_main_menu()



def LOG(logger, msg):
	print str(ctime()) + ' {' + logger + '} ' + msg



'''
dfddf
'''

class M100Thread(Thread):
	def __init__(self):
		global curX, curY, curZ

		Thread.__init__(self)
		LOG('M100', 'Initialize drone control system...')

		self.drone = DJIDrone()
		#while self.drone.sdk_permission_opened == False:
		self.drone.request_sdk_permission_control()
		time.sleep(0.5)

		curX = self.drone.global_position.latitude
		curY = self.drone.global_position.longitude
		curZ = self.drone.global_position.altitude

	def run(self):
		global curX, curY, curZ, dstX, dstY, dstZ
		global launchFlag, relocationFlag, landingFlag, gohomeFlag
		global Done

		while not Done:
			try:
				statusLock.acquire()
				curX = self.drone.global_position.latitude
				curY = self.drone.global_position.longitude
				curZ = self.drone.global_position.altitude
				statusLock.release()

				launchLock.acquire()
				if launchFlag:
					if self.drone.flight_status.data == 1:
						self.drone.takeoff()
					launchFlag = False
				launchLock.release()

				relocationLock.acquire()
				if relocationFlag:
					# call some function for moving the drone
					# "some function" not yet defined
					# self.drone.global_position_control(dstX, dstY, dstZ, 0)
					
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
		global curX, curY, curZ, dstX, dstY, dstZ
		global launchFlag, relocationFlag, landingFlag

		Thread.__init__(self)

		try:
			LOG('Client', 'create socket')
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			
			#Uncomment this if you get [Errno 98] Address already in use
			#self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			
			LOG('Client', 'try to access to server')
			self.socket.connect(ADDR)

		except Exception, e:
			LOG('Client', repr(e))
			return

	def run(self):

		batctlOut = subprocess.Popen(["sudo batctl o"], stdout=subprocess.PIPE, shell=True).communicate()[0]
		grepOut = subprocess.Popen(["grep '(bat0'"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True).communicate(input=batctlOut)[0]
		selfMac = subprocess.Popen(["awk '{print $5}'"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True).communicate(input=grepOut)[0]
		selfMac = selfMac.split('\n')
		selfMac.pop()
		selfMac = selfMac[0][6:]

		LOG('Client', 'send drone registration request to server')
		try:
			self.socket.send('drone new %s\t' %(selfMac))
		except Exception, e:
			LOG('Client', repr(e))
			return


		while True:
			try:
				batctlOut = subprocess.Popen(["sudo batctl o"], stdout=subprocess.PIPE, shell=True).communicate()[0]
				neighborMac_ = batctlOut.split("\n")[2:-1]
				neighborMac = ""
				for i in neighborMac_:
					neighborMac = neighborMac + i.split(" ")[0] + " "
					
				try:
					data = self.socket.recv(BUFSIZE)
				except KeyboardInterrupt:
					return

				if not data:
					LOG('Client', 'the end of connection')
					break

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
						except Exception, e:
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

			except Exception, e:
				LOG('Client', repr(e))
				return

''' main start '''
if __name__ = '__main__':

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






'''
while True:
	main_operate_code = raw_input()
	if main_operate_code == 'a':
		drone.request_sdk_permission_control()
	elif main_operate_code == 'b':
		drone.release_sdk_permission_control()
	elif main_operate_code == 'c':
		drone.takeoff()
	elif main_operate_code == 'd':
		drone.landing()
	elif main_operate_code =='e':
		drone.gohome()
	elif main_operate_code == 'f':
		# Local Navi Test
		position_list = raw_input("x y z : ")
		[x, y, z] = position_list.split(" ")
		fx = float(x)
		fy = float(y)
		fz = float(z)
		drone.local_position_navigation_send_request(fx, fy, fz)
		#while(drone.local_position.x -fx > 0.01 or drone.local_position.x - fx <-0.01): 
			#if(drone.velocity.vx > 0.1) : 
			   # drone.velocity_control(255,0.1,0.1,0.1,0)
		   # drone.attitude_control(DJIDrone.HORIZ_POS|DJIDrone.VERT_VEL|DJIDrone.YAW_ANG|DJIDrone.HORIZ_BODY|DJIDrone.YAW_BODY, 1, 1, 0, 0)
			#time.sleep(0.02)

	elif main_operate_code == 'g':
		# Global Navi Test
		position_list = raw_input("lat long alt : ")
		[x, y, z] = position_list.split(" ")
		fx = float(x)
		fy = float(y)
		fz = float(z)
		drone.global_position_navigation_send_request(fx, fy, fz)
	
	elif main_operate_code == 'h':
		print "GPS : [%f, %f, %f]" %(drone.global_position.latitude, drone.global_position.longitude, drone.global_position.altitude)
		print "Local : [%f, %f, %f]"  %(drone.local_position.x, drone.local_position.y, drone.local_position.z)
		print "GPS reliability(0~5) : %d (higher is more reliability)" %(drone.global_position.health)
 
		#print "velocity :[%f, %f, %f]" %(drone.velocity.vx, drone.velocity.vy, drone.velocity.vz)
		#print (drone.velocity)
		#print "acceleraation : [%f, %f, %f]" %(drone.acceleration.ax, drone.acceleration.ay, drone.acceleration.az)
	


	# local velocity control 
	elif main_operate_code == 'j':
		position_list = raw_input("x y z : ")
		[x, y, z] = position_list.split(" ")
		fx = float(x)
		fy = float(y)
		fz = float(z)
		#vx = (drone.local_position.x-fx)/20
		#vy = (drone.local_position.y-fy)/20
		#vz = (drone.local_position.z-fz)/20
		dx = fx - drone.local_position.x
		dy = fy - drone.local_position.y
		dz = fz - drone.local_position.z
		vx = dx / math.sqrt(dx*dx + dy*dy)
		vy = dy / math.sqrt(dx*dx + dy*dy)
		vz = dz / abs(dz)
		num = int(math.floor(25* math.sqrt(dx*dx+dy*dy)))
		for i in range(num):
			if(math.sqrt((fx-drone.local_position.x)*(fx-drone.local_position.x) + (fy - drone.local_position.y)*(fy - drone.local_position.y)) > 1):
				drone.attitude_control(DJIDrone.HORIZ_POS|DJIDrone.VERT_VEL|DJIDrone.YAW_ANG|DJIDrone.HORIZ_BODY|DJIDrone.YAW_BODY,vx,vy,0,0)
			else :
				break
			time.sleep(0.02)
		for i in range(int(abs(math.floor(25*dz)))):
			if( abs(fz - drone.local_position.z) > 1):
				drone.attitude_control(0x40,0,0,vz,0)
			else : 
				break
			time.sleep(0.02)

	# global velocity control 
	elif main_operate_code == 'k':
		position_list = raw_input("lat long alt : ")
		[x, y, z] = position_list.split(" ")
		fx = float(x)
		fy = float(y)
		fz = float(z)
		#vx = (drone.local_position.x-fx)/20
		#vy = (drone.local_position.y-fy)/20
		#vz = (drone.local_position.z-fz)/20
		dx = (fx - drone.global_position.latitude) * 110000
		dy = (fy - drone.global_position.longitude) * 88740
		dz = fz - drone.global_position.altitude
		#num = int(math.floor(25* math.sqrt(dx*dx+dy*dy)))
		vz = dz / abs(dz)
		while (math.sqrt(dx*dx + dy*dy) > 0.1):
			dx = (fx - drone.global_position.latitude) * 110000
			dy = (fy - drone.global_position.longitude) * 88740
			
			vx = dx / math.sqrt(dx*dx + dy*dy)
			vy = dy / math.sqrt(dx*dx + dy*dy)
			
			#if(math.sqrt((fx-drone.global_position.latitude)*(fx-drone.global_position.latitude) + (fy - drone.global_position.longitude)*(fy - drone.global_position.longitude)) > 0.000001):
			drone.attitude_control(DJIDrone.HORIZ_POS|DJIDrone.VERT_VEL|DJIDrone.YAW_ANG|DJIDrone.HORIZ_BODY|DJIDrone.YAW_BODY,vx,vy,0,0)
			#else :
			#    break
			time.sleep(0.02)

		for i in range(int(abs(math.floor(25*dz)))):
			if( abs(fz - drone.global_position.altitude) > 1):
				drone.attitude_control(0x40,0,0,vz,0)
			else : 
				break
			time.sleep(0.02)

		
	elif main_operate_code == 'q':
		break


	#Waypoint Mission Upload 
	elif main_operate_code == 'v':
		waypoint_task = dji_sdk.msg.MissionWaypointTask()
		waypoint1 = dji_sdk.msg.MissionWaypoint()
		waypoint2 = dji_sdk.msg.MissionWaypoint()
 #       waypoint3 = dji_sdk.msg.MissionWaypoint()
		#clear the previous waypoint list 
		del waypoint_task.mission_waypoint[:]
		
		waypoint_task.velocity_range = 10
		waypoint_task.idle_velocity = 2
		waypoint_task.action_on_finish = 0
		waypoint_task.mission_exec_times = 1
		waypoint_task.yaw_mode = 4
		waypoint_task.trace_mode = 0
		waypoint_task.action_on_rc_lost = 0
		waypoint_task.gimbal_pitch_mode = 0

		position_list = raw_input("lat long alt : ")
		[lat, lon, alt] = position_list.split(" ")

		#waypoint.latitude = float(lat)
		#waypoint.longitude = float(lon)
		waypoint1.latitude = drone.global_position.latitude
		waypoint1.longitude = drone.global_position.longitude

		waypoint1.altitude = float(alt)
		waypoint1.damping_distance = 0
		waypoint1.target_yaw = 0
		waypoint1.target_gimbal_pitch = 0
		waypoint1.turn_mode = 0
		waypoint1.has_action = 0
		
		waypoint_task.mission_waypoint.append(waypoint1)
		#waypoint_task.mission_waypoint.append(waypoint)

		waypoint2.latitude = float(lat)
		waypoint2.longitude = float(lon)
		waypoint2.altitude = float(alt)
		waypoint2.damping_distance = 0
		waypoint2.target_yaw = 0
		waypoint2.target_gimbal_pitch = 0
		waypoint2.turn_mode = 0
		waypoint2.has_action = 0

		waypoint_task.mission_waypoint.append(waypoint2)

#        waypoint3.latitude = drone.global_position.latitude
#        waypoint3.longitude = float(lon)
#        waypoint3.altitude = drone.global_position.altitude
#        waypoint3.damping_distance = 0
#        waypoint3.target_yaw = 0
#        waypoint3.target_gimbal_pitch = 0
#        waypoint3.turn_mode = 0
#        waypoint3.has_action = 0
		
#        waypoint_task.mission_waypoint.append(waypoint3)




		drone.mission_waypoint_upload(waypoint_task)

	#Mission Start     
	elif main_operate_code == 'y':
		drone.mission_start()

	#Mission Pause
	elif main_operate_code == 'z': 
		drone.mission_pause()

	#Mission Resume
	elif main_operate_code == 'A':
		drone.mission_resume()

	#Mission Cancle
	elif main_operate_code == 'B':
		drone.mission_cancle()

	#Mission Waypoint Download
	elif main_operate_code == 'C':
		drone.mission_waypoint_download()

	#Mission Waypoint Set Speed
	elif main_operate_code == 'D':
		vel = raw_input("velocity request : ")
		drone.mission_waypoint_set_speed(float(vel))

	#Mission Waypoint Get Speed
	elif main_operate_code == 'E':
		drone.mission_waypoint_get_speed()



	else:
		display_main_menu()
'''        
		
