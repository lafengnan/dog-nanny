# coding: utf-8
# author: panzhongbin@gmail.com

from weibo import APIClient, APIError
import urllib,httplib,urllib2
import logging
import os
import sys
import string
import threading


# stores config information
class ConfigInfo(object):
	"""docstring for ConfigInfo"""
	m_appinfo = {'key':'', 'secret':''}
	m_account = {'id':'', 'passwd':''}
	m_callback_url = ''
	m_admins = []
	def __init__(self, config_file):
		if os.access(config_file, os.R_OK):
			with open(config_file) as fp:
				lines = fp.readlines()
				if len(lines) is 6:
					self.m_appinfo['key'] = lines[0].strip('\n')
					self.m_appinfo['secret'] = lines[1].strip('\n')
					self.m_account['id'] = lines[2].strip('\n')
					self.m_account['passwd'] = lines[3].strip('\n')
					self.m_callback_url = lines[4].strip('\n')
					admin = unicode(lines[5].strip('\n'), 'utf8')
					self.m_admins = admin.split()

				else:
				    fp.close()
				    logging.error("Content of config file error")
				    sys.exit(1)
		else:
		    logging.error("Read config file denied")
		    sys.exit(1)

	def get_config_info(self):
		return (self.m_appinfo, self.m_account, self.m_callback_url, self.m_admins)


# Base class of all weibos
class Weibo(object):
	"""docstring for Weibo"""
	m_client = None
	m_weibo_op = ''
	m_oauth2_code = ''
	def __init__(self):
		pass
	def set_client(self, key, secret, call_back_url):
		pass
	def get_client(self):
		pass
	def status_update(self, new_status = ''):
		pass
	def set_access_token(self, auth2_code = ''):
		pass
	def set_oauth2_code(self, app, acc, cb_url, au_url):
		pass
	def get_oauth2_code(self):
		pass

# Sina weibo 
class SinaWeibo(Weibo):
	"""docstring for SinaWeibo"""
	m_client = None
	m_weibo_op = ''
	def __init__(self):
		self.m_weibo_op = 'sina'
	def set_client(self, app_key, app_secret, call_back_url):
		if self.m_client is None:
			self.m_client = APIClient(app_key, app_secret, call_back_url)
	def get_client(self):
		if self.m_client:
			return self.m_client
		else:
			logging.error("client is None, please set it first!")
			sys.exit(1)
	def update_status(self, new_status):
		if self.m_client:
			self.m_client.post.statuses__update(status=new_status)
		else:
			logging.error("client is None, please set_client first!")
			sys.exit(1)
	def set_oauth2_code(self, app, acc, cb_url, au_url):
		conn = httplib.HTTPSConnection('api.weibo.com')
		postdata = urllib.urlencode({'client_id':app['key'], 'response_type':'code',
			                         'redirect_uri':cb_url, 'action':'submit',
			                         'userId':acc['id'], 'passwd':acc['passwd'],
			                         'isLoginSina':0, 'from':'',
			                         'regCallback':'', 'state':'',
			                         'ticket':'', 'withOfficalFlag':0})
		conn.request('POST','/oauth2/authorize',postdata,{'Referer':au_url,'Content-Type': 'application/x-www-form-urlencoded'})
		res = conn.getresponse()
		location = res.getheader('location')
		self.m_oauth2_code = location.split('=')[1]
		conn.close()
	def get_oauth2_code(self):
		if self.m_oauth2_code != '':
			return self.m_oauth2_code
		else:
			logging.error("get oauth2 code error !")
			sys.exit(1)
	def set_access_token(self, oauth2_code):
		if self.m_client:
			try:
				request = self.m_client.request_access_token(oauth2_code)
				logging.info("Get access token:{0} expire:{1}".format(request.access_token, request.expires_in))
				# Save the access token
				self.m_client.set_access_token(request.access_token, request.expires_in)
			except APIError as e:
				logging.error("Set access token error: (error_code: %d, error: %s, request: %s" % (e.error_code, e.error, e.request))
				sys.exit(1)
		else:
			logging.error("Error:set_access_token with oauth2_code:%s" % oauth2_code)
			sys.exit(1)

class WeiboFactory(object):
	"""docstring for WeiboFactory"""
	__m_instance = None
	__m_lock = threading.Lock()
	__m_weibo_table = {'sina': SinaWeibo, 
	                   'tencent': Weibo,
	                   'twitter': Weibo
	                   }
	def __init__(self):
		"Disabled"
	@staticmethod
	def get_instance():
		WeiboFactory.__m_lock.acquire()
		if not WeiboFactory.__m_instance:
			WeiboFactory.__m_instance = object.__new__(WeiboFactory)
			object.__init__(WeiboFactory.__m_instance)
		WeiboFactory.__m_lock.release()
		return WeiboFactory.__m_instance
	def create_weibo(self, weibo_op):
		if weibo_op in self.__m_weibo_table:
			return self.__m_weibo_table[weibo_op]()
		else:
			logging.debug("Oops! %s is not supported now!" % weibo_op)
			return None

class User(object):
	"""docstring for User"""
	m_name = ''
	m_uid = 0
	def __init__(self, name = '', uid = 0):
	    self.m_uid = uid
	    self.m_name = name
	def set_uid_and_name(self, weibo):
		if weibo.m_weibo_op == "sina":
			msg = weibo.m_client.get.account__get_uid()
			self.m_uid = msg.__getattr__('uid')
			if self.m_uid == 0:
				logging.error("Cannot get the nanny account uid")
				sys.exit(1)

			msg = weibo.m_client.get.users__show(uid=self.m_uid)
			self.m_name = msg.__getattr__('screen_name')
			if len(self.m_name) == 0:
				logging.error("Cannot get the nanny account screen name:%d" % self.m_name)
				sys.exit(1)

			logging.debug("Get nanny's uid:%d screen_name:%s" % (self.m_uid, self.m_name))
		else:
			logging.error("Oops! Unknown weibo client!")
			sys.exit(1)

	def get_uid(self):
		return self.m_uid
	def get_screen_name(self):
		return self.m_name

