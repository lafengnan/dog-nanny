#! /usr/bin/env python
# coding=utf-8
# author: panzhongbin@gmail.com

import urllib,httplib,urllib2
import logging
import time
import os
import sys
import string
import subprocess
import random
import threading
import nanny_sns
from device import DeviceFactory, Home, AirCondition, Temper, Camera

WORKDIR = os.getcwd()
TEMPER1 = WORKDIR + '/temper1/temper'
CAPTURE = WORKDIR + '/capture.py'
AC_CONTROL = WORKDIR + '/ac-controller/ac-ctrl'
CONFIG_FILE = os.environ['HOME'] + '/dognanny.rc'
INTERVAL = 30 # 30s
RESOLUTION = '1280x720'

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


class Proxy(object):
	"""docstring for Proxy"""
	m_weibo = None
	def __init__(self):
		pass
	def set_proxy(self, weibo):
		self.m_weibo = weibo
	def action_ping(self, client, fans, msgid):
		logging.debug("%s is pinging me" % fans)
		client.post.comments__create(comment=u"I'm alive %f" % random.random(), id=msgid)
	def action_kill(self, client, fans, msgid):
		logging.info(u"kill myself on order of {0}".format(' '.join(fans)))
		client.post.statuses__update(status=u'下班咯[太开心]' + u' '.join(fans))
		sys.exit(0)


# Commands description and handler
cmds_desc = {
    'poll' : {
             'pattern': u'豆芽呢',
             'desc': u'poll the status',
             'class': 'Home',
             'handler': Home.get_home_info },
    'acon' : {
             'pattern': u'开空调',
             'desc': u'turn on ac',
             'class': 'AirCondition',
             'handler': AirCondition.action_on },
    'acoff': {
             'pattern': u'关空调',
             'desc': u'turn off ac',
             'class': 'AirCondition',
             'handler': AirCondition.action_off },
    'kill' : {
             'pattern': u'下班吧',
             'desc': u'kill myself',
             'instance': 'Proxy',
             'handler': Proxy.action_kill },
    'ping' : {
             'pattern': u'ping',
             'desc': u'debug ping',
             'instance': 'Proxy',
             'handler': Proxy.action_ping },
}
		

def main():
	''' This is main routine of program. The process is as follows:
	1. parse the config file to fetch configurations
	   config_info = (appinfo, m_account, callback_url, admins)
	2. Get a weibo client via invoking weibo API
	   client = APIClient(xxxx)
	3. Fetch the msg content via invoking weibo API
	4. Build a dog-house for monitorring
	5. As per the message content to call the respective functions 
	   to implement command
	6. The concrete command send reply messages
	'''

    #1. Parse config file
	config_info = ConfigInfo(CONFIG_FILE)

	(appinfo, account, callback_url, admins) = config_info.get_config_info()
	logging.info("Get app info: {0}".format(appinfo))
	logging.info("Get account info: {0}".format(account))
	logging.info("Get callback URL: {0}".format(callback_url))
	logging.info(u"Get Admin account: {0}".format(' '.join(admins)))

	#2. create a weibo
	weibo_fc = nanny_sns.WeiboFactory()
	sina_weibo = weibo_fc.create_weibo('sina')

	#3. Set weibo client
	sina_weibo.set_client(appinfo['key'], appinfo['secret'], callback_url)

	auth_url = sina_weibo.m_client.get_authorize_url()
	logging.info("OAuth authorize URL:%s" % auth_url)

	sina_weibo.set_oauth2_code(appinfo, account, callback_url, auth_url)
	code = sina_weibo.get_oauth2_code()
	#code = get_oauth2_code(appinfo, account, callback_url, auth_url)

	#oauth2_code = get_oauth2_code(appinfo, account, callback_url, auth_url)
	#logging.info("Get auth code:%s" % sina_weibo.m_oauth2_code)
	logging.info("Get auth code:%s" % code)
	#4. Set and save access token
	request = sina_weibo.set_access_token(code)

	#5. Create a user nanny and set it with weibo info
	nanny = nanny_sns.User()
	nanny.set_uid_and_name(sina_weibo)

	#6. Initialize the since_id
	since_id = 0

	#7. Get emotions
	emotions = []
	emotions_id = 0
	get_emotions = sina_weibo.m_client.get.emotions()
	for emotion in get_emotions:
		emotions.append(emotion['phrase'])

	#8. Update the last id, drop the expired command message
	msg = sina_weibo.m_client.get.statuses__mentions(filter_by_author='1', trim_user='1', since_id=since_id)
	get_statuses = msg.__getattr__('statuses')
	if (len(get_statuses) > 0) and get_statuses[0].has_key('id'):
		since_id = get_statuses[0]['id']
	logging.debug("Start to get command message from id:%s" % since_id)

	#9. Update init message
	sina_weibo.update_status(u'要干活了[委屈]')

	#10. main loop
	# Create a routine proxy
	nanny_proxy = Proxy()
	nanny_proxy.set_proxy(sina_weibo)
	# Create Home instance
	dev_fc = DeviceFactory()
	nanny_home = Home(dev_fc)
	while True:
		now = time.time()
		tmp_id = since_id
		cmd_queue = {}

		# Debug to get a rate limit status
		while True:
			try:
				msg = sina_weibo.m_client.get.account__rate_limit_status()
			except (urllib2.URLError, httplib.BadStatusLine) as e:
				logging.error("Get rate limit error: {0}".format(e))
				continue
			break
		if msg.has_key('api_rate_limits'):
			del msg['api_rate_limits']
		logging.debug("Get rate limit:{0}".format(msg))

		# Get the lastest @ message by since_id
		logging.debug("Get mentions by since_id:%d" % since_id)
		while True:
			try:
				msg = sina_weibo.m_client.get.statuses__mentions(filter_by_author='1', trim_user='1', since_id=since_id)
			except (urllib2.URLError, httplib.BadStatusLine) as e:
				logging.error("Get mentions error: {0}".format(e))
				continue
			break
		get_statuses = msg.__getattr__('statuses')

		for msg in get_statuses:
		    # Fetch commands
		    msg_content = nanny_sns.MessageContent(msg)
		    (msgid, fans, cmd) = msg_content.get_msg_content(nanny)

		    if tmp_id < msgid:
		    	tmp_id = msgid
		    # If the message is parsed with error
		    if msgid == 0 or cmd == '':
		    	continue
		    # Filter the commands sent by non admin
		    if (cmd is not 'poll') and (admins.count(fans) == 0):
		    	# Comment the message
		    	deny_comment = u"貌似您不是豆芽主人唉%s" % (emotions[emotion_id])
		    	sina_weibo.m_client.post.comments__create(id=msgid, comment=deny_comment)
		    	emotion_id = (emotion_id + 1) % len(emotions)
		    	logging.debug("no prividge for %s to do %s" % (fans, cmd))
		    	continue

		    # Handle ping command separately
		    if cmd is 'ping':
		    	Proxy.action_ping(nanny_proxy, sina_weibo.m_client, fans, msgid)
		    	continue

		    # TODO:queue the command, and combine same requests
		    if cmd_queue.has_key(cmd):
		    	atwho = u'@' + fans
		    	if not atwho in cmd_queue[cmd]:
		    		cmd_queue[cmd].append(atwho)
		    else:
		    	cmd_queue[cmd] = [u'@' + fans, ]

		# If there's no new message or command, sleep
		if tmp_id == since_id or len(cmd_queue) == 0:
			logging.debug("on message handle this cycle")
			since_id = tmp_id
			time.sleep(INTERVAL)
			continue

		# TODO: save the acon/off, kill lastest message id for response
		# execute commands after queueing msg
		if len(cmd_queue) > 0:
			instance = None
			for key, value in cmd_queue.items():
				logging.debug(u"execute cmd:{0} for {1}".format(key, u''.join(value)))
				for each_instance in (nanny_home, nanny_home.m_air_condition, nanny_proxy):
					if each_instance.__class__.__name__ == cmds_desc[key]['class']:
						instance = each_instance
						break
				ret = cmds_desc[key]['handler'](instance, sina_webo.m_client, value, msgid)


		cmd_queue.clear()
		since_id = tmp_id
		time.sleep(INTERVAL)



if __name__ == '__main__':

    # setup the logging
    logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s',
            filename='/tmp/dognanny.log',
            filemode='w')
    main()

		
