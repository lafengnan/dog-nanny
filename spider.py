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
    'pm2d5_value': '',
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

        city_pattern = re.compile(r'.*jin_caption = .*', re.U)
        value_pattern = re.compile(r'.*jin_value = .*', re.U)
        if os.access(PM2D5_DATA, os.R_OK):
            with open(PM2D5_DATA) as fp:
                lines = fp.readlines()
                for line in lines:
                    match1 = re.search(city_pattern, line)
                    match2 = re.search(value_pattern, line)
                    if match1:
                        city =  match1.group(0).split('=')[-1].decode('utf8').strip()
                        self.m_pm2d5_info['city'] = city.strip(';').strip('"')
                    if match2:
                        value = match2.group(0).split('=')[-1].strip()
                        self.m_pm2d5_info['pm2d5_value'] = value.strip(';').strip('"')
                        if float(self.m_pm2d5_info['pm2d5_value']) < 50:
                            self.m_pm2d5_info['image_path'] = '/1.jpg'
                            self.m_pm2d5_info['message'] = u' 不错 [太开心]'
                        elif float(self.m_pm2d5_info['pm2d5_value']) > 100:
                            self.m_pm2d5_info['image_path'] = '/2.jpg'
                            self.m_pm2d5_info['message'] = u' 霾头苦干吧，亲！[生病]'
                        else:
                            self.m_pm2d5_info['image_path'] = '/3.jpg'
                            self.m_pm2d5_info['message'] = u' 凑活着过吧，亲！[可怜]'
                        logging.info("image path: %s" % self.m_pm2d5_info['image_path'])
                        logging.info("%s: %s" %(self.m_pm2d5_info['city'], self.m_pm2d5_info['pm2d5_value']))
            f.close(PM2D5_DATA)
            os.rename(PM2D5_DATA, PM2D5_DATA_BK)
        else:
            logging.debug("could not access pm2d5.data")



#if __name__ == '__main__':

#    pm2d5 = PM2D5('http://www.pm2d5.com/city/shanghai.html')
#    pm2d5.get_pm2d5()


