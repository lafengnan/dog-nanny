# coding: utf-8
# author: panzhongbin@gmail.com

import urllib,httplib,urllib2
from weibo import APIError
import logging
import time
import re
from re import split
import os
import sys
import string
import random
import threading
from nanny_sns import ConfigInfo, SinaWeibo, WeiboFactory, User
from device import DeviceFactory, AirCondition, Temper, Camera, WORKDIR
from spider import PM2D5


CONFIG_FILE = os.environ['HOME'] + '/dognanny.rc'
INTERVAL = 30 # 30s



class Proxy(object):
	"""docstring for Proxy"""
	m_weibo = None
	m_ac = None
	m_temper = None
	m_camera = None
	def __init__(self):
		pass
	def set_weibo(self, weibo):
		self.m_weibo = weibo
	def set_ac(self, ac):
		self.m_ac = ac
	def set_temper(self, temper):
		self.m_temper = temper
	def set_camera(self, camera):
		self.m_camera = camera
	def action_ping(self, client, fans, msgid):
		logging.debug("%s is pinging me" % fans)
		client.post.comments__create(comment=u"I'm alive %f" % random.random(), id=msgid)
	def action_kill(self, client, fans, msgid):
		logging.info(u"kill myself on order of {0}".format(' '.join(fans)))
		client.post.statuses__update(status=u'下班咯[太开心]' + u' '.join(fans))
		sys.exit(0)
	def action_poll(self, client, fans, msgid):
		print self.m_ac.get_status() 
		ac_message = u'空调状态: ' + self.m_ac.get_status() + '\n'
		temper_message = self.m_temper.get_temp_value()
		message = ac_message + temper_message + u" {at}".format(at=u' '.join(fans)) 
		# capture a shot
		self.m_camera.capture()
		image_path = self.m_camera.get_image_path()
		try:
			image_file = open(image_path.strip('\n'))
			client.upload.statuses__upload(status=message, pic=image_file)
		except IOError as e:
			message += u' 照片读取失败 [可怜]'
			client.post.statuses__update(status=message)

	def action_on(self, client, fans, msgid):
		self.m_ac.action_on()
		message = self.m_ac.m_reply + u" {at}".format(at=u' '.join(fans))
		try:
			client.post.comments__create(comment=u"%s %f" % (message, random.random()), id=msgid)
		except APIError as e:
			logging.error("reply ac on command error: {0}".format(e))

	def action_off(self, client, fans, msgid):
		self.m_ac.action_off()
		message = self.m_ac.m_reply + u" {at}".format(at=u' '.join(fans))
		try:
			client.post.comments__create(comment=u"%s %f" % (message, random.random()), id=msgid)
		except APIError as e:
			logging.error("reply ac on command error: {0}".format(e))


	def get_pm2d5(self, client, fans, msgid):

		url = 'http://www.pm2d5.com/city/shanghai.html'
		pm2d5 = PM2D5(url)
		pm2d5.get_pm2d5()
		image_path = WORKDIR + pm2d5.m_pm2d5_info['image_path']
		city = pm2d5.m_pm2d5_info['city']
		pm2d5_value = pm2d5.m_pm2d5_info['pm2d5_value']
		pm2d5_message = pm2d5.m_pm2d5_info['message']
		logging.info("my_main: image_path is %s, %s: %s" %(image_path, city, pm2d5_value))

		message = city + ": " + pm2d5_value + pm2d5_message + u" {at}".format(at=u' '.join(fans))
		try:
			image_file = open(image_path)
			client.upload.statuses__upload(status=message, pic=image_file)
		except APIError as e:
			logging.error("reply ac on command error: {0}".format(e))





class MessageContent():
	"""docstring for MessageContent"""
	def __init__(self, msg):
		self.m_date = msg['created_at']
		self.m_text = msg['text'].strip()
		self.m_name = msg['user']['name']
		self.m_msgid = msg['id']
		self.m_cmd = ''
	def get_msg_content(self, user):
        #analysis the @ message
        #return: (id, sender_name, cmd)
		pair = re.compile(r"@(\w+) (\w+).*", re.U)

		for key, desc in cmds_desc.items():
			match = pair.match(self.m_text)
			if match is not None:
				if match.group(1) != user.m_name:
					logging.warning("%s has send a wrong msg on %s" % (match.group(1), self.m_date))
					return (0, '', '')
				idx = string.find(match.group(2), desc['pattern'])
				if 0 == idx:
					self.m_cmd = key
					break
		logging.debug("return command(%s): [%s]: (%s) by %s" % (self.m_date, self.m_cmd, self.m_text, self.m_name))
		return (self.m_msgid, self.m_name, self.m_cmd)


# Commands description and handler
cmds_desc = {
    'poll' : {
             'pattern': u'豆芽呢',
             'desc': u'poll the status',
             'handler': Proxy.action_poll},
    'acon' : {
             'pattern': u'开空调',
             'desc': u'turn on ac',
             'handler': Proxy.action_on },
    'acoff': {
             'pattern': u'关空调',
             'desc': u'turn off ac',
             'handler': Proxy.action_off },
    'kill' : {
             'pattern': u'下班吧',
             'desc': u'kill myself',
             'handler': Proxy.action_kill },
    'ping' : {
             'pattern': u'ping',
             'desc': u'debug ping',
             'handler': Proxy.action_ping },
    'pm2d5' : {
              'pattern': u'现在空气怎样啊',
              'desc': u'get pm2.5 info',
              'handler': Proxy.get_pm2d5}
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
	weibo_fc = WeiboFactory.get_instance()
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
	nanny = User()
	nanny.set_uid_and_name(sina_weibo)

	#6. Initialize the since_id
	since_id = 0

	#7. Get emotions
	emotions = []
	emotion_id = 0
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
	sina_weibo.update_status(u'开始工作了!![委屈]')

	#10. main loop
	# Create device
	dev_fc = DeviceFactory.get_instance()
	nanny_ac = dev_fc.create_dev('ac')
	nanny_temper = dev_fc.create_dev('temper')
	nanny_camera = dev_fc.create_dev('camera')

	# Create a routine proxy
	nanny_proxy = Proxy()
	nanny_proxy.set_weibo(sina_weibo)
	nanny_proxy.set_camera(nanny_camera)
	nanny_proxy.set_temper(nanny_temper)
	nanny_proxy.set_ac(nanny_ac)

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
		    msg_content = MessageContent(msg)
		    (msgid, fans, cmd) = msg_content.get_msg_content(nanny)

		    if tmp_id < msgid:
		    	tmp_id = msgid
		    # If the message is parsed with error
		    if msgid == 0 or cmd == '':
		    	continue
		    # Filter the commands sent by non admin
		    if (cmd is not 'poll') and (cmd is not 'pm2d5') and (admins.count(fans) == 0):
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
				ret = cmds_desc[key]['handler'](nanny_proxy, sina_weibo.m_client, value, msgid)


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

    # make it daemon
    try:
        pid = os.fork()
	if pid > 0:
           sys.exit(0)
    except OSError, e:
        logging.error("fork #1 failed: %d (%s)" % (e.errno, e.strerror))
        sys.exit(1)

    os.chdir("/")
    os.setsid()
    os.umask(0)

    try:
        pid = os.fork()
	if pid > 0:
           logging.info("Daemon pid: %d" % pid)
           sys.exit(0)
    except OSError, e:
        logging.error("fork #2 failed: %d (%s)" % (e.errno, e.strerror))
        sys.exit(1)

    # main loop
    main()

