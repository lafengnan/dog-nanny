# coding=utf-8
# author: panzhongbin@gmail.com

import logging
import time
import os
import sys
import string
import subprocess
import random
import threading



# Device is the base class of all controlled devices
class Device:
	"""docstring for Devic"""
	def __init__(self, name = ''):
		self.m_name = name
		self.m_cmd = ''
		self.m_status = 'off'
		self.m_cur_time = time.strftime("%H点%M分%S秒", time.localtime())
	def action(self, cmd):
		self.get_cur_time()
		logging.debug("%s: device receive %s command" % (self.m_cur_time, cmd))
		return True
	def action_on(self, client):
		self.m_cmd = 'on'
		if self.m_status == 'on':
			reply = 'device is on, no need to turn on again'
		elif self.m_status == 'off':
			if self.action(self.m_cmd):
				self.m_status = 'on'
				reply = 'device is turned on successfully!'
			else:
				self.m_status = 'off'
				reply = 'Oops! device turned on failed!'
		print reply
	def action_off(self, cilent):
		self.m_cmd = 'off'
		if self.m_status == 'off':
			reply = 'device is off, no need to turn off again'
		elif self.m_status == 'on':
			if self.action(self.m_cmd):
				self.m_status = 'off'
				reply = 'device is turned off successfully!'
			else:
				self.m_status = 'on'
				reply = 'Oops! device turned off failed!'
		print reply

	def get_status(self, client):
		return self.m_status;
	def get_name(self, client):
		return self.m_name
	def get_cur_time(self, client):
		self.m_cur_time = time.strftime("%H点%M分%S秒", time.localtime())
		return self.m_cur_time

class AirCondition(Device):
	"""docstring for AirCondition"""
	def action(self, cmd):
		self.get_cur_time()
		logging.debug("%s: 空调收到 %s 命令" % (self.m_cur_time, cmd))
		# if there's ac control command
		# send ac ctrl command
		cmd_line = "%s %s" % (AC_CONTROL, cmd)
		try:
			subprocess.check_call(cmd_line , shell=True)
		except subprocess.CalledProcessError as e:
			logging.error("exec ac-ctrl error:%s" % e.output)
			return False
		return True
	def action_on(self, client, executor, msgid):
		self.m_cmd = 'on'
		if self.m_status == 'off':
			if self.action(self.m_cmd):
				self.m_status = 'on'
				reply = '空调已经打开'	
			else:
				self.m_status = tmp_status
				reply = '空调打开失败'
		elif self.m_status == 'on':
			self.m_status = 'on'
			reply = '空调已经打开，无须再开'

		try:
			client.post.comments__create(comment=u"%s %f" % (reply, random.random()), id=msgid)
		except APIError as e:
			logging.error("reply ac on command error: {0}".format(e))

	def action_off(self, client, executor, msgid):
		self.m_cmd = 'off'
		if self.m_status == 'off':
			self.m_status = 'off'
			reply = '空调已经关闭，无须再关'
		elif self.m_status == 'on':
			if self.action(self.m_cmd):
				self.m_status = 'off'
				reply = '空调已经关闭'	
			else:
				reply = '空调关闭失败'
		try:
			client.post.comments__create(comment=u"%s %f" % (reply, random.random()), id=msgid)
		except APIError as e:
			logging.error("reply ac on command error: {0}".format(e))


class Temper(Device):
	"""docstring for Temp"""
	__m_tempr = 1000.0
	def __init__(self, name = ''):
		self.m_name = name
		self.m_status = 'on'
		self.m_emotion = '[兔子]'
	def action(self, cmd):
		flag = True
		self.get_cur_time()
		logging.debug("%s: 温度计收到 %s 命令" % (self.m_cur_time, cmd))
		if 'get_tempr' == cmd:
		    #self.__m_tempr = random.randrange(-10, 40, 1) + random.random()
		    #print "北京时间：%s 温度: %f度" % (self.m_cur_time, self.__m_tempr)
			try:
				tempr = subprocess.check_output(TEMPER1, shell=True)
			except subprocess.CalledProcessError as e:
				logging.error("exec temper1 error:%s" % e.output)
				flag = False
				self.m_status = 'sick'

			logging.debug("run temper1 to get temperature:%s" % tempr)
			if len(tempr):
				self.m_status = 'health'
				tempr = tempr.strip('\n')
				try:
					self.__m_tempr = float(tempr)
					if self.__m_tempr < 5:
						self.m_emotion = '[可怜]'
					elif self.__m_tempr <= 20:
						self.m_emotion = '[兔子]'
					elif self.__m_tempr <= 28:
						self.m_emotion = '[太开心]'
					elif self.__m_tempr < -10 or self.__m_tempr > 28:
						self.m_emotion = '[生病]'
					logging.debug("current temperature:%s" % tempr)
				except ValueError as e:
					self.__m_tempr = 1000.0
					self.m_status = 'sick'
					flag = False
		else:
			logging.debug("%s is not supported now!" % cmd)
			flag = False
		return flag

	def get_tempr(self, client, executor, msgid):
		logging.debug("run temper1 to get temperature:%f" % self.__m_temper)
		self.m_cmd = 'get_tempr'
		executor = client.account__get_uid.__getattr__('screen_name')
		if self.action_on(self.m_cmd):
			# send one weibo message with pic & @sender 
			message = u"{emotion}主人，豆芽房间当前温度：{temper}℃  -- {time} {at}".format(
				        emotion = self.m_emotion
                        temper = self.__m_temper, 
                        time = time.strftime("%H点%M分", time.localtime()).decode('utf8'),
                        at = u' '.join(executor))
			return message

class Camera(Device):
	"""docstring for Camera"""
	m_image_path = ''
	def __init__(self):
		self.m_status = 'on'
		self.m_image_path = ""
	def action(self, cmd):
		flag = True
		self.m_cur_time = self.get_cur_time()
		logging.debug("%s: 摄像头收到 %s 命令" %(self.m_cur_time, cmd))
		if 'capture' == cmd:
			now = time.time()
			self.m_cmd = "fswebcam -r %s -q -D 0.5 %s" % (RESOLUTION, self.m_image_path)
			try:
				subprocess.check_all(self.m_cmd, shell=True)
			except subprocess.CalledProcessError as e:
				logging.error("exec fswebcam error: %s" % e.output)
				self.m_status = 'sick'
				flag = False

			statinfo = os.stat(self.m_image_path)
			if statinfo.st_ctime < now:
				self.m_image_path = ''
			logging.debug("Get the captured file:%s" % self.m_image_path)
		else:
			flag = False
			logging.debug("Oops! the command %s is not supported now!" % cmd)

		return flag
	
	def capture(self, client):
		self.m_cmd = 'capture'
		if self.action(self.m_cmd):
			if self.m_image_path is '':
				logging.debug("Did not find new image")
	def set_image_path(self, path = ""):
		self.m_image_path = path
	def get_image_path(self):
		return self.m_image_path


class Home:
	"""docstring for NannyHome"""
	m_air_condition = None
	m_cammera = None
	m_temperature = None
	def __init__(self, dev_fc):
		if dev_fc is None:
			logging.debug("Are you kidding me? Without fc, how to build Nanny's home?")
			sys.exit(1)
		else:
			self.m_air_condition = dev_fc.create_dev('ac')
			self.m_cammera = dev_fc.create_dev('camera')
			self.m_temperature = dev_fc.create_dev('temper')
	def get_home_info(self, client, executor, msgid):
		# 1. get images
		# 2. get temperature value
		# 3. poll as message
		if self.m_air_condition:
			ac_message = self.m_air_condition.get_status()
		if self.m_temperature and self.m_temperature.get_status() == 'on':
			temper_message = self.m_temperature.get_tempr(client)
		if self.m_cammera and self.m_cammera.m_status == 'on':
			self.m_cammera.capture(client)

		camera_status = self.m_cammera.get_status()
		message = temper_message + u'空调目前:%s' % ac_message

		if camera_status is 'sick':
			client.post.statuses__update(status=message + u'摄像头故障')
		elif camera_status is 'on' and self.m_cammera.get_image_path() is '':
			client.post.statuses__update(status=message)
		elif camera_status is 'on' and self.m_cammera.get_image_path() is not '':
			try:
				image_file = open(self.m_cammera.get_image_path().strip('\n'))
				client.upload.statuses__upload(status=message, pic=image_file)
			except IOError as e:
					client.post.statuses__update(status=message + u'照片读取失败')


# Factory Class, only one dev fac and only one weibo fac, 
class DeviceFactory(object):
	"""docstring for DeviceFactory"""
	__m_instance = None
	__m_lock = threading.Lock()
	__m_device_table = {'ac': AirCondition, 
	                    'camera': Camera, 
	                    'temper': Temper
	                    }
	def __init__(self):
		"Disabled"
	@staticmethod
	def get_instance():
		DeviceFactory.__m_lock.acquire()
		if not DeviceFactory.__m_instance:
			DeviceFactory.__m_instance = object.__new__(DeviceFactory)
			object.__init__(DeviceFactory.__m_instance)
		DeviceFactory.__m_lock.release()
		return DeviceFactory.__m_instance
	def create_dev(self, dev):
		if dev in __m_device_table:
			return self.__m_device_table[dev]()
		else:
			print "Oops! %s is not supported now!" % dev
			return None




