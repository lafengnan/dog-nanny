# coding: utf-8
# author: panzhongbin@gmail.com

import urllib2
import logging
import re
import os, sys
import string
from HTMLParser import HTMLParser

PM2D5_DATA = os.getcwd() + '/pm2d5.data'
PM2D5_DATA_BK = os.getcwd() + '/pm2d5.data.bk'


class MyHTMLParser(HTMLParser):
    """docstring for MyHTMLParser"""
    def handle_starttag(self, tag, attrs):
        return tag
    def handle_endtag(self, tag):
        return tag
    def handle_data(self, data):
        logging.info("data is: %s" % data)
        f = open(PM2D5_DATA, 'a')
        try:
            f.write(data)
            f.close()
        except IOError as e:
            f.close()
            logging.error("could not write info %s", e.error)
            sys.exit(1)

class PM2D5(object):
    """docstring for PM2D5"""
    m_pm2d5_info = {
    'city': '',
    'city_us': u'美领馆',
    'view': '',
    'view_us': '',
    'pm2d5_value': '',
	'pm2d5_value_us':'',
    'message': u'',
    'image_path': ''
    }
    def __init__(self, url):
        self.m_url = url

    def __getattr__(self, attr):
        return attr
    def get_pm2d5(self):
        #content = urllib2.urlopen('http://www.pm2d5.com/city/shanghai.html').read()
        content = urllib2.urlopen(self.m_url).read()
        parser = MyHTMLParser()
        parser.feed(content)
        city = []
        view = []
        value = []

        city_pattern = re.compile(r'.*cityname = .*', re.U)
        view_pattern = re.compile(r'.*jin_caption = cityname \+ .*.', re.U)
        value_pattern = re.compile(r'.*jin_value = "\d+".*', re.U)
        if os.access(PM2D5_DATA, os.R_OK):
            with open(PM2D5_DATA) as fp:
                lines = fp.readlines()
                for line in lines:
                    match_city = re.search(city_pattern, line)
                    match_view = re.search(view_pattern, line)
                    match_value = re.search(value_pattern, line)
                    if match_city:
                        city.append(match_city.group(0).split('=')[-1].decode('utf8').strip())
                        self.m_pm2d5_info['city'] = city[0].strip(';').strip('"')
                    if match_view:
                        view.append(match_view.group(0).split('+')[-1].decode('utf8').strip())
                        self.m_pm2d5_info['view'] = view[0].strip(';').strip('"')
                        logging.info("debug view:%s" %(self.m_pm2d5_info['view']))
                        if len(view) > 1:
                           self.m_pm2d5_info['view_us'] = view[1].strip(';').strip('"')
                           logging.info("debug view_us:%s" %(self.m_pm2d5_info['view_us']))
                    if match_value:
                        value.append(match_value.group(0).split('=')[-1].strip())
                        self.m_pm2d5_info['pm2d5_value'] = value[0].strip(';').strip('"')
                        logging.info("debug city_value: %s %s: %s" %(self.m_pm2d5_info['city'], self.m_pm2d5_info['view'], self.m_pm2d5_info['pm2d5_value']))
                        if (len(value) > 1):
                            self.m_pm2d5_info['pm2d5_value_us'] = value[1].strip(';').strip('"')
                            logging.info("debug city_value_us: %s %s: %s" %(self.m_pm2d5_info['city'], self.m_pm2d5_info['view_us'], self.m_pm2d5_info['pm2d5_value_us']))
                        try:
                            if max(float(self.m_pm2d5_info['pm2d5_value']), float(self.m_pm2d5_info['pm2d5_value_us'])) < 50:
                                self.m_pm2d5_info['image_path'] = '/1.jpg'
                                self.m_pm2d5_info['message'] = u' 不错 [太开心]'
                            elif max(float(self.m_pm2d5_info['pm2d5_value']), float(self.m_pm2d5_info['pm2d5_value_us'])) > 100:
                                self.m_pm2d5_info['image_path'] = '/2.jpg'
                                self.m_pm2d5_info['message'] = u' 霾头苦干吧，亲！[生病]'
                            else:
                                self.m_pm2d5_info['image_path'] = '/3.jpg'
                                self.m_pm2d5_info['message'] = u' 凑活着过吧，亲！[可怜]'
                            logging.info("image path: %s" % self.m_pm2d5_info['image_path'])
                            logging.info("%s: %s" %(self.m_pm2d5_info['city'], self.m_pm2d5_info['pm2d5_value']))
                        except ValueError as e:
                            logging.error("%s " % e)
            fp.close()
            os.rename(PM2D5_DATA, PM2D5_DATA_BK)
        else:
            logging.debug("could not access pm2d5.data")



#if __name__ == '__main__':

#    logging.basicConfig(
#            level=logging.DEBUG,
#            format='%(asctime)s %(levelname)s %(message)s',
#            filename='/tmp/spider.log',
#            filemode='w')
#    pm2d5 = PM2D5('http://www.pm2d5.com/city/shanghai.html')
#    pm2d5.get_pm2d5()


