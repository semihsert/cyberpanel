import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import socket#!/usr/local/CyberCP/bin/python
import sys
import os
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import paramiko
import os
import json
import threading as multi
import time
import asyncio
'''
This is a simple Websocket Echo server that uses the Tornado websocket handler.
Please run `pip install tornado` with python of version 2.7.9 or greater to install tornado.
This program will echo back the reverse of whatever it recieves.
Messages are output to the terminal for debuggin purposes. 
'''


class SSHServer(multi.Thread):
    OKGREEN = '\033[92m'
    ENDC = '\033[0m'

    DEFAULT_PORT = 22

    @staticmethod
    def findSSHPort():
        try:
            sshData = open('/etc/ssh/sshd_config', 'r').readlines()

            for items in sshData:
                if items.find('Port') > -1:
                    if items[0] == 0:
                        pass
                    else:
                        SSHServer.DEFAULT_PORT = int(items.split(' ')[1])
        except BaseException as msg:
            logging.writeToFile('%s. [SSHServer.findSSHPort]' % (str(msg)))

    def loadPublicKey(self):
        pubkey = '/root/.ssh/cyberpanel.pub'
        data = open(pubkey, 'r').read()
        authFile = '/root/.ssh/authorized_keys'

        checker = 1

        try:
            authData = open(authFile, 'r').read()
            if authData.find(data) > -1:
                checker = 0
        except:
            pass

        if checker:
            writeToFile = open(authFile, 'a')
            writeToFile.writelines(data)
            writeToFile.close()

    def __init__(self, websocket):
        multi.Thread.__init__(self)
        self.sshclient = paramiko.SSHClient()
        self.sshclient.load_system_host_keys()
        self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        k = paramiko.RSAKey.from_private_key_file('/root/.ssh/cyberpanel')

        ## Load Public Key
        self.loadPublicKey()

        self.sshclient.connect('127.0.0.1', SSHServer.DEFAULT_PORT, username='root', pkey=k)
        self.shell = self.sshclient.invoke_shell(term='xterm')
        self.shell.settimeout(0)

        self.websocket = websocket
        self.color = 0

    def recvData(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        while True:
            try:
                if self.websocket.running:
                    if os.path.exists(self.verifyPath) and self.filePassword == self.password:
                        if self.shell.recv_ready():
                            self.websocket.write_message(self.shell.recv(9000).decode("utf-8"))
                        else:
                            time.sleep(0.001)
                    else:
                        return 0
                else:
                    return 0
            except BaseException as msg:
                print('%s. [recvData]' % str(msg))
                time.sleep(0.001)

    def run(self):
        try:
            self.recvData()
        except BaseException as msg:
            print('%s. [SSHServer.run]' % (str(msg)))


class WSHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        print('connected')
        self.running = 1
        self.sh = SSHServer(self)
        self.shell = self.sh.shell
        self.sh.start()
        self.init = 1
        print('connect ok')

    def on_message(self, message):
        try:
            print('handle message')
            data = json.loads(message)

            if self.init:
                self.sh.verifyPath = str(data['data']['verifyPath'])
                self.sh.password = str(data['data']['password'])
                self.sh.filePassword = open(self.sh.verifyPath, 'r').read()
                self.init = 0
            else:
                if os.path.exists(self.sh.verifyPath):
                    if self.sh.filePassword == self.sh.password:
                        self.shell.send(str(data['data']))

        except BaseException as msg:
            print('%s. [WebTerminalServer.handleMessage]' % (str(msg)))

    def on_close(self):
        print('connection closed')

    def check_origin(self, origin):
        return True


application = tornado.web.Application([
    (r'/', WSHandler),
])

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application, ssl_options={
        "certfile": "/usr/local/lscp/conf/cert.pem",
        "keyfile": "/usr/local/lscp/conf/key.pem",
    }, )
    ADDR = '0.0.0.0'
    http_server.listen(5678, ADDR)
    print('*** Websocket Server Started at %s***' % ADDR)
    tornado.ioloop.IOLoop.instance().start()