from time import time, sleep
from socket import socket, AF_INET, SOCK_STREAM
from ctypes import *
from ctypes import wintypes
import re, datetime

'''
Connects to Mirametrix S1 eye tracker
Send/receive commands via tcp/ip socket

Jeroen Kools, May 10 2011
Last change: Jan 18 2012
'''

class tracker:
    def __init__(self):
        self.data = ''
        self.sock = self.connect()
        self.trackdata = []
        raise
                
    def connect(self):
        sock = socket(AF_INET, SOCK_STREAM)
        #print '* Socket created' 
        try:
            sock.connect(('localhost', 4242))
            sock.settimeout(100.0)
        except Exception as e:
            print ' Eye tracker appears to be offline. If you want to use it, start the tracker first, then restart Experiment Wizard'
            return -1
        return sock
    
    def calibrate(self):
        '''Performs calibration sequence, measures error'''
        
        freq = c_longlong(0)
        timev = c_longlong(0)
        windll.kernel32.QueryPerformanceFrequency(byref(freq))
        self.timetickfrequency = float(freq.value)
        
        windll.kernel32.QueryPerformanceCounter(byref(timev))
        self.startCPUTime = float(timev.value)
        self.startWallTime = time.time()
        
        print '* Calibrating...'
        a = ''
        self.calibrated = 0
        try:
            self.sock.send('<SET ID="CALIBRATE_SHOW" STATE="1" />\r\n')
            self.sock.send('<SET ID="CALIBRATE_START" STATE="1" />\r\n')     
            self.sock.send('<GET ID="CALIBRATE_RESULT_SUMMARY" />\r\n')
            a = self.sock.recv(1024)
            while not '"CALIB_RESULT"' in a:
                b = self.sock.recv(1024)
                if 'CALIB_RESULT_PT' in b:
                    self.calibrated += 1
                a += b
                time.sleep(0.5)
        except Exception:
            print '* Error during calibration: %s'
        
        validl = len(re.findall('LV\d="1"',a))
        validr = len(re.findall('RV\d="1"',a))
        self.valid = max(validl,validr)
        self.valid = min(self.calibrated, self.valid)
        print '* Calibration complete\n %s out of 9 targets done' % self.calibrated
        print ' Valid: %s/%s' % (self.valid, self.calibrated)
        self.sock.send('<SET ID="CALIBRATE_SHOW" STATE="0" />\r\n')
        self.sock.send('<SET ID="CALIBRATE_START" STATE="0" />\r\n')
    
    #FPOGX float Fixation point-of-gaze X
    #FPOGY float Fixation point-of-gaze Y
    #FPOGS float Fixation start (seconds)
    #FPOGD float Fixation duration (elapsed time since fixation start (seconds))
    #FPOGID int Fixation number ID
    #FPOGV int Fixation point-of-gaze valid ag
    
    def record(self):
        self.sock.settimeout(None)        
        self.sock.send('<SET ID="ENABLE_SEND_POG_FIX" STATE="1" />\r\n')
        self.sock.send('<SET ID="ENABLE_SEND_TIME" STATE="1" />\r\n')
        self.sock.send('<SET ID="ENABLE_SEND_TIME_TICK" STATE="1" />\r\n')
        self.sock.send('<SET ID="ENABLE_SEND_DATA" STATE="1" />\r\n')
        self.sock.send('<SET ID="ENABLE_SEND_PUPIL_LEFT" STATE="1" />\r\n')
        self.sock.send('<SET ID="ENABLE_SEND_PUPIL_RIGHT" STATE="1" />\r\n')
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
                data = self.sock.recv(12000)
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
    
    def convertTime(self, txt):
        # convert processor tick time to absolute time
        
        for n in range(len(txt)):
            line = txt[n]
            t = float(line[0])                                            # ticks passed
            t = (t-self.startCPUTime)/self.timetickfrequency              # seconds passed
            t = datetime.datetime.fromtimestamp(self.startWallTime+t)     # wall time struct
            t = "%02i:%02i:%02i.%03i" %\
                (t.hour, t.minute, t.second, t.microsecond/1000.)         # wall time string
            txt[n] = (t,) + txt[n][1:]
            
        return txt
    
    def getData(self):
        return ''.join(self.trackdata)
    
    def clean(self):
        self.data = ''
        self.trackdata = []
