# coding: utf-8
# author: panzhongbin@gmail.com

import logging
import time
import os
import sys
import string
import subprocess
import random
import threading


WORKDIR = os.getcwd()
TEMPER1 = WORKDIR + '/temper1/temper'
CAPTURE = WORKDIR + '/capture.py'
AC_CONTROL = WORKDIR + '/ac-controller/ac-ctrl'
RESOLUTION = '1280x720'

# Device is the base class of all controlled devices
class Device:
	"""docstring for Devic"""
	def __init__(self, name = ''):
		self.m_name = name
		self.m_cmd = ''
		self.m_status = 'off'
		self.m_reply = ' '
		self.m_cur_time = time.strftime("%H点%M分%S秒", time.localtime())
	def action(self, cmd):
		self.get_cur_time()
		logging.debug("%s: device receive %s command" % (self.m_cur_time, cmd))
		return True
	def action_on(self):
		self.m_cmd = 'on'
		if self.m_status == 'on':
			self.m_reply = 'device is on, no need to turn on again'
		elif self.m_status == 'off':
			if self.action(self.m_cmd):
				self.m_status = 'on'
				self.m_reply = 'device is turned on successfully!'
			else:
				self.m_status = 'off'
				self.m_reply = 'Oops! device turned on failed!'
	def action_off(self):
		self.m_cmd = 'off'
		if self.m_status == 'off':
			self.m_reply = 'device is off, no need to turn off again'
		elif self.m_status == 'on':
			if self.action(self.m_cmd):
				self.m_status = 'off'
				self.m_reply = 'device is turned off successfully!'
			else:
				self.m_status = 'on'
				self.m_reply = 'Oops! device turned off failed!'

	def get_status(self):
		return self.m_status;
	def get_name(self):
		return self.m_name
	def get_cur_time(self):
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
	def action_on(self):
		self.m_cmd = 'on'
		if self.m_status == 'off':
			if self.action(self.m_cmd):
				self.m_status = 'on'
				self.m_reply = u'空调已经打开'	
			else:
				self.m_status = tmp_status
				self.m_reply = u'空调打开失败'
		elif self.m_status == 'on':
			self.m_status = 'on'
			self.m_reply = u'空调已经打开，无须再开'

	def action_off(self):
		self.m_cmd = 'off'
		if self.m_status == 'off':
			self.m_status = 'off'
			self.m_reply = u'空调已经关闭，无须再关'
		elif self.m_status == 'on':
			if self.action(self.m_cmd):
				self.m_status = 'off'
				self.m_reply = u'空调已经关闭'	
			else:
				self.m_reply = u'空调关闭失败'


class Temper(Device):
	"""docstring for Temp"""
	__m_temper = ' '
	def __init__(self, name = ''):
		self.m_name = name
		self.m_status = 'on'
		self.m_emotion = '[兔子]'
	def action(self, cmd):
		flag = True
		self.get_cur_time()
		logging.debug("%s: 温度计收到 %s 命令" % (self.m_cur_time, cmd))
		if 'get_temper' == cmd:
		    #self.__m_temper = random.randrange(-10, 40, 1) + random.random()
		    #print "北京时间：%s 温度: %f度" % (self.m_cur_time, self.__m_temper)
			try:
				self.__m_temper = subprocess.check_output(TEMPER1, shell=True)
			except subprocess.CalledProcessError as e:
				logging.error("exec temper1 error:%s" % e.output)
				flag = False
				self.m_status = 'sick'

			logging.debug("run temper1 to get temperature: %s" % self.__m_temper)
			if len(self.__m_temper):
				self.m_status = 'health'
				self.__m_temper = self.__m_temper.strip('\n')
				try:
					temper_float = float(self.__m_temper)
					if temper_float < 5:
						self.m_emotion = '[可怜]'
					elif temper_float <= 20:
						self.m_emotion = '[兔子]'
					elif temper_float <= 28:
						self.m_emotion = '[太开心]'
					elif temper_float < -10 or temper_float > 28:
						self.m_emotion = '[生病]'
					logging.debug("current temperature:%s" % self.__m_temper)
				except ValueError as e:
					self.__m_temper = u'1000.0'
					self.m_status = 'sick'
					flag = False
			else:
				self.__m_temper = u'1000.0'
		else:
			logging.debug("%s is not supported now!" % cmd)
			flag = False
		return flag

	def get_temp_value(self):
		logging.debug("run temper1 to get temperature: %s" % self.__m_temper)
		self.m_cmd = 'get_temper'
		self.action(self.m_cmd)
		reply = u"{emotion}主人，豆芽房间当前温度：{temper}℃  -- {time}".format(
			            emotion = self.m_emotion.decode('utf8'),
                        temper = self.__m_temper, 
                        time = time.strftime("%H点%M分", time.localtime()).decode('utf8'))
		return reply

class Camera(Device):
	"""docstring for Camera"""
	def __init__(self):
		self.m_status = 'on'
		self.m_image_path = WORKDIR + "/shot.jpg"
	def action(self, cmd):
		flag = True
		self.m_cur_time = self.get_cur_time()
		logging.debug("%s: 摄像头收到 %s 命令" %(self.m_cur_time, cmd))
		if 'capture' == cmd:
			now = time.time()
			self.m_cmd = "fswebcam -r %s -q -D 0.5 %s" % (RESOLUTION, self.m_image_path)
			try:
				subprocess.check_call(self.m_cmd, shell=True)
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
	
	def capture(self):
		self.m_cmd = 'capture'
		if self.action(self.m_cmd):
			if self.m_image_path is '':
				logging.debug("Did not find new image")
	def set_image_path(self, path = ""):
		self.m_image_path = path
	def get_image_path(self):
		return self.m_image_path


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
		if dev in self.__m_device_table:
			return self.__m_device_table[dev]()
		else:
			print "Oops! %s is not supported now!" % dev
			return None
