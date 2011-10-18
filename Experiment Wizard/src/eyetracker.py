from time import time, sleep
from socket import socket, AF_INET, SOCK_STREAM

'''
Connects to Mirametrix S1 eye tracker
Send/receive commands via tcp/ip socket

Jeroen Kools, May 10 2011
'''

class tracker:
    def __init__(self):
        self.data = ''
        self.sock = self.connect()
        self.trackdata = []
                
    def connect(self):
        sock = socket(AF_INET, SOCK_STREAM)
        #print '* Socket created' 
        try:
            sock.connect(('localhost', 4242))
            sock.settimeout(5.0)
        except Exception as e:
            print ' Eyetracker software found, but device seems to be offline!'
        return sock
    
    def calibrate(self):
        '''Performs calibration sequence, measures error'''
        print '* Calibrating...'
        try:
            self.sock.send('<SET ID="CALIBRATE_SHOW" STATE="1" />\r\n')
            self.sock.send('<SET ID="CALIBRATE_START" STATE="1" />\r\n')     
            self.sock.send('<GET ID="CALIBRATE_RESULT_SUMMARY" />\r\n')
            a = self.sock.recv(1024)
            while not '"CALIB_RESULT"' in a:
                a = self.sock.recv(1024)
                sleep(1)                
        except:
            print '* Error during calibration!!'
        print '* Calibration complete!'
        self.sock.send('<SET ID="CALIBRATE_SHOW" STATE="0" />\r\n')
        self.sock.send('<SET ID="CALIBRATE_START" STATE="0" />\r\n')
    
        return self.sock.recv(1024)
    
    #FPOGX float Fixation point-of-gaze X
    #FPOGY float Fixation point-of-gaze Y
    #FPOGS float Fixation start (seconds)
    #FPOGD float Fixation duration (elapsed time since xation start (seconds))
    #FPOGID int Fixation number ID
    #FPOGV int Fixation point-of-gaze valid ag
    
    def record(self):
        self.sock.settimeout(None)        
        self.sock.send('<SET ID="ENABLE_SEND_POG_FIX" STATE="1" />\r\n')
        self.sock.send('<SET ID="ENABLE_SEND_TIME" STATE="1" />\r\n')
        self.sock.send('<SET ID="ENABLE_SEND_GPI" STATE="1" />\r\n')    
    
    def startStim(self,stimname):
        self.sock.send('<SET ID="ENABLE_SEND_DATA" STATE="1" />\r\n')
        self.sock.send('<SET ID="GPI_NUMBER" VALUE="1" />\r\n')    
        self.sock.send('<SET ID="GPI1" VALUE="%s" />\r\n' % stimname)        
        
    def stopStim(self):
        self.sock.send('<SET ID="ENABLE_SEND_DATA" STATE="0" />\r\n')
        self.trackdata.append(self.collectData()) 
    
    def collectData(self):
        stop = '<ACK ID="ENABLE_SEND_DATA" STATE="0" />'
        alldata = []
        data = ''
        while True:
            try:
                data = self.sock.recv(1024)
            except: break
            #print '--\n', data, '##'
            if stop in data:
                alldata.append(data[:data.find(stop)])
                break
            alldata.append(data)
            if len(alldata)>1:
                #check if stop was split
                last_pair = alldata[-2] + alldata[-1]
                if stop in last_pair:
                    alldata[-2]=last_pair[:last_pair.find(stop)]
                    all.pop()
                    break                      
        return ''.join(alldata)
    
    def getData(self):
        return ''.join(self.trackdata)
