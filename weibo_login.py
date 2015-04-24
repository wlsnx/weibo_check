#!/usr/bin/env python
# encoding: utf-8


import re
import json
import cookielib


class WeiboLogin(object):

    def __init__(self, username, password, cookie_file="/tmp/weibo_cookie"):
        self.username = username
        self.password = password
        self.cookie_file = cookie_file
        self.logged = False
        from requests import Session
        self.session = Session()

    def get_username(self):
        from urllib import quote
        from base64 import encodestring
        return encodestring(quote(self.username))[:-1]

    def get_password(self):
        weibo_rsa_n = "EB2A38568661887FA180BDDB5CABD5F21C7BFD59C090CB2D245" \
                      "A87AC253062882729293E5506350508E7F9AA3BB77F43332314" \
                      "90F915F6D63C55FE2F08A49B353F444AD3993CACC02DB784ABB" \
                      "B8E42A9B1BBFFFB38BE18D78E87A0E41B9B8F73A928EE0CCEE1" \
                      "F6739884B9777E4FE9E88A1BBE495927AC4A799B3181D6442443"
        weibo_rsa_e = 65537
        message = "{}\t{}\n{}".format(self.servertime,
                                    self.nonce,
                                    self.password)
        import rsa
        key = rsa.PublicKey(int(weibo_rsa_n, 16), weibo_rsa_e)
        encropy_pwd = rsa.encrypt(message, key)
        import binascii
        return binascii.b2a_hex(encropy_pwd)

    def get_prelogin_data(self):
        prelogin_url = "http://login.sina.com.cn/sso/prelogin.php"
        prelogin_data = {"entry": "weibo",
                         "callback": "sinaSSOController.preloginCallBack",
                         "su": self.get_username(),
                         "rsakt": "mod",
                         "checkpin": "1",
                         "client": "ssologin.js(v1.4.18)"}
        response = self.session.get(prelogin_url,
                                    params=prelogin_data).content
        matched = re.search("\((.*)\)", response)
        if matched:
            json_data = matched.group(1)
            data = json.loads(json_data)
            self.__dict__.update(data)

    def get_pin_image(self):
        import random
        pin_url = "http://login.sina.com.cn/cgi/pin.php"
        pin_data = {"s": "0",
                    "r": random.randint(10000000, 99999999),
                    "p": self.pcid}
        pin_image = self.session.get(pin_url, params=pin_data)
        return pin_image.content

    def load_cookies(self):
        lwpcookiejar = cookielib.LWPCookieJar(self.cookie_file)
        try:
            lwpcookiejar.load(ignore_expires=True, ignore_discard=True)
            for cookie in lwpcookiejar:
                self.session.cookies.set_cookie(cookie)
            return self.test_log_status()
        except:
            return self.logged

    def get_login_data(self):
        self.get_prelogin_data()
        self.login_data = {"entry": "weibo",
                           "gateway": "1",
                           "from": "",
                           "savestate": "7",
                           "userticket": "1",
                           "pagerefer": "",
                           "vsnf": "1",
                           "su": self.get_username(),
                           "service": "miniblog",
                           "servertime": self.servertime,
                           "nonce": self.nonce,
                           "pwencode": "rsa2",
                           "rsakv": self.rsakv,
                           "sp": self.get_password(),
                           "encoding": "UTF-8",
                           "prelt": "45",
                           "url": "http://weibo.com/ajaxlogin.php?framelogin=1&" \
                                   "callback=parent.sina.SSOController.feedBackUrlCallBack",
                           "returntype": "META"}
        if self.showpin:
            self.login_data["pcid"] = self.pcid
            return self.get_pin_image()

    def login(self, door=None):
        if door:
            self.login_data["door"] = door
        login_url = "http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.18)"
        login_response = self.session.post(login_url,
                                           data=self.login_data).content
        login_matched = re.search("setCrossDomainUrlList\((.*?)\).*?location\.replace\([\'|\"](.*?)[\'|\"]\)",
                                  login_response)
        if login_matched:
            cross_domain = login_matched.group(1)
            callback_url = login_matched.group(2)
            cross_domain_data = json.loads(cross_domain)
            retcode = cross_domain_data["retcode"]
            if retcode:
                return False
            else:
                arr_url = cross_domain_data["arrURL"]
                #url_formatter = "{}&callback=sinaSSOController.doCrossDomainCallBack&scriptId=ssoscript{}&client=ssologin.js(v1.4.18)"
                for index, url in enumerate(arr_url):
                    #self.session.get(url_formatter.format(url, index))
                    self.session.get(url)
                self.session.get(callback_url)
                logged = self.test_log_status()
                if logged:
                    lwpcookiejar = cookielib.LWPCookieJar(self.cookie_file)
                    for cookie in self.session.cookies:
                        lwpcookiejar.set_cookie(cookie)
                    lwpcookiejar.save(ignore_discard=True, ignore_expires=True)
        return self.logged
        #login_matched = re.search("location\.replace\(['|\"](.*?)['|\"]\)",
                                  #login_response)
        #if login_matched:
            #redirect_url = login_matched.group(1)
            #if "retcode=0" not in redirect_url:
                #return False
            #redirect_response = self.session.get(redirect_url).content
            #redirect_matched = re.search("feedBackUrlCallBack\((.*?)\)",
                                         #redirect_response,
                                         #re.M)
            #if redirect_matched:
                #feedback_json = redirect_matched.group(1)
                #feedback_data = json.loads(feedback_json)
                #if feedback_data["result"]:
                    #lwpcookiejar = cookielib.LWPCookieJar(self.cookie_file)
                    #for cookie in self.session.cookies:
                        #lwpcookiejar.set_cookie(cookie)
                    #lwpcookiejar.save()
                    #self.logged = True
                    #return True
                #else:
                    #return False
            #else:
                #return False
        #else:
            #return False

    def test_log_status(self):
        response = self.session.get("http://weibo.com").content
        if "$CONFIG" in response:
            self.logged = True
        else:
            self.logged = False
        return self.logged

    def get(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.session.post(*args, **kwargs)

