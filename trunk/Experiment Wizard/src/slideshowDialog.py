# -*- coding: utf-8 -*-

        #############################################################
        #                                                           #
        #                   slideshowDialog.py                      #
        #                                                           #
        #       Present a set of images and record EEG              #
        #       data from connected Emotiv EPOC devices             #
        #                                                           #
        # Requires:                                                 #
        #  Python 2.6, PyQt4, ctypes, Emotiv SDK, Emotiv hardware   #
        #                                                           #
        #                   by Jeroen Kools                         #
        #                       2010-2011                         	#
        #                                                           #
        #############################################################

### Load dependencies ###
from PyQt4 import QtCore, QtGui # Qt top library
from PyQt4.phonon import Phonon # Qt media library
from ctypes import byref, c_char_p, c_double, c_uint, c_ulong, cdll
from fourier import doFFT
from gui import slideshowUi
from re import match
import os, time, random
libc = cdll.msvcrt # load C library
EDK_loaded = True


try:
    edk = cdll.LoadLibrary("edk.dll")
    edk_utils = cdll.LoadLibrary("edk_utils.dll")    
except:
    print 'Error importing Emotiv Library!'
    EDK_loaded = False


class slideshow(QtGui.QFrame, slideshowUi):   
    movietypes = "*.avi *.mp4 *.mpg *.mpeg *.mov *.wmv *.mp3 *.wav"
    audiotypes = "*.mp3 *.wav"    
    mediatypes = movietypes+' '+audiotypes
    
    def __init__(self,subject, settings, app):
        print '\n***** Starting experiment! ******' 
        QtGui.QFrame.__init__(self)
        self.settings = settings
        self.ui = slideshowUi
        self.ui.setupUi(self)
        self.setFocus()
        self.app = app
        self.playingAV = False        
        self.trackerData = '' 
        if self.settings.enableEyeTracker:
            self.settings.eyetracker.record()
            print 'Eye tracker recording!'

        # make sure text is in readable color
        self.bgcolor = settings.bgColor
        if self.bgcolor == 'Black':
            self.textcolor = 'white'
        else:
            self.textcolor = 'black'
            
        self.setStyleSheet("QFrame { background-color: %s; }" % self.bgcolor)

        self.fullScreen = True
        self.online = True
        self.haveHadKeypresses = False
        self.recordKeys = settings.recordKeys
        self.intervalNext = False
        
        self.nextPhase = "stimulus"  # stimulus/interval/mask
        self.masks = []
        if settings.masking != 'None':            
            for f in os.listdir(settings.maskfolder):
                ext = os.path.splitext(f)[1]
                ext = ext.lower() 
                if ext in ['.jpg','.gif','.bmp','.jpeg','.png']:
                    self.masks.append(os.path.join(str(settings.maskfolder),f))
            if settings.randomizeMasks:
                random.shuffle(self.masks)
        print '%s masks found in %s' % (len(self.masks), settings.maskfolder)
        if 'space' in settings.masklength:
            self.maskLength = 60e3
        else:
            m = match('[\d\.]+', settings.masklength)            
            self.maskLength = int(1000*float(m.group()))
        
        self.subject = subject
        self.disp.setText(self.txt('Now recording subject '+str(self.subject.name)))

        # map shortcut keys
        QtGui.QShortcut(QtGui.QKeySequence("Escape"), self,\
                        self.quitApp )     
        
        self.images = settings.stimuli
        self.numimages = len(self.images)
        self.millis_per_img  = settings.millisPerImg
        self.millisInterval = settings.millisMaskDuration
        self.transparant = QtGui.QMovie('transparant.gif',QtCore.QByteArray(), self)
        self.date = time.strftime(' %b %d %Hh%M')       
        self.displaytime = time.clock() 

        self.outputdir = os.getcwd()+'\\recordings\\'  # where to save data
        self.delay = 50                                # extra time in ms per loop to allow for calculation        
        if settings.outputFolder != '':
            self.outputdir = settings.outputFolder + '/'
        if not os.path.exists(self.outputdir):
            os.mkdir(self.outputdir)
        self.csvname = self.outputdir+self.subject.name+self.date+'.csv'
        self.arffname = self.outputdir+self.subject.name+self.date+'.arff'
        
        self.alldata = []
        self.response = 'None'
        self.responsetime = 0
        self.movieSamples = 0
        self.totalSamples = 0

        self.channelnames = ['AF3','F7','F3','FC5',\
                        'T7','P7','O1','O2','P8','T8',\
                        'FC6','F4','F8','AF4']         

        if settings.shuffle:
            from random import shuffle      # shuffle image list if settings say so
            shuffle(self.images)

        # Create link to Emotiv engine
        connected = edk.EE_EngineConnect()
        if connected == 0x0000:
            print 'Connected to EmoEngine!'
        else:
            print 'Failed to connect to EmoEngine'
            self.online = False

        # Intro/countdown
        self.iCountdown = self.settings.countdownFrom + 1
        self.atImage = -1

        # update timer
        self.timer = QtCore.QTimer(self)
        self.connect(self.timer,
                     QtCore.SIGNAL("timeout()"),
                     self.update_image)

        # countdown timer
        self.countdownTimer = QtCore.QTimer(self)
        self.connect(self.countdownTimer,
                     QtCore.SIGNAL("timeout()"),
                     self.countdown)

        self.countdownTimer.start(1000)
        
        self.movieSegmentTimer = QtCore.QTimer(self)
        self.connect(self.movieSegmentTimer,
                     QtCore.SIGNAL("timeout()"),
                     self.processMovieSegment)
        
        self.connect(self.vp,
                     QtCore.SIGNAL('finished()'),
                     self.movieSegmentTimer,
                     QtCore.SLOT('stop()'))   
        
        self.connect(self.vp,
                     QtCore.SIGNAL('finished()'),
                     self.update_image)             



### helper functions

    def txt(self,text):
        s =  "<font color='%s'>%s</font>" % (self.textcolor,text)
        return s

    def countdown(self):
        self.iCountdown -= 1
        self.disp.setText(self.txt('Starting in '+str(self.iCountdown)))

        # initialize data collection now
        if self.iCountdown == 0:

            # Setup EDK interface
            self.eventHandle = edk.EE_EmoEngineEventCreate()
            self.state = edk.EE_EmoStateCreate()
            userID = c_uint(999)

            self.data  = edk.EE_DataCreate()
            bufferset = edk.EE_DataSetBufferSizeInSec(int(self.millis_per_img/1000.))

            if bufferset != 0:
                print 'Failed to initialize buffer!'

            # Add user
            self.userAdded = False
            attempts = 0
            maxAttempts = 50000
            while(not(self.userAdded) and (attempts < maxAttempts)):
                attempts += 1
                eventstate = edk.EE_EngineGetNextEvent(self.eventHandle)
                if eventstate == 0x0000:
                    eventType = edk.EE_EmoEngineEventGetType(self.eventHandle)
                    edk.EE_EmoEngineEventGetUserId(self.eventHandle, byref(userID))
                    if eventType == 0x0010: # UserAdded
                        print 'User added at attempt '+str(attempts)
                        self.userAdded = True
                        print 'Connected to EPOC wifi receiver!'
                        print 'User: '+str(userID.value)
                        edk.EE_DataAcquisitionEnable(userID,True)
                        version = c_char_p("version number")
                        vchars = c_uint(25)
                        build = c_ulong()
                        edk.EE_SoftwareGetVersion(version,vchars,
                                                  byref(build))
                        print 'SDK version: '+version.value

            if (attempts >= maxAttempts-1 and not(self.userAdded)):
                print 'Time-out error: Failed to connect to headset..'
                self.online = False

            self.atImage = 0
            self.countdownTimer.stop()
            self.timer.start(self.millis_per_img+self.delay)
            self.update_image()

    # file type checks, used by list filters
    def isRecord(self,i):
        if '.csv' in str(i):
            return True
        return False

    def update_image(self):
        self.timer.start(self.millis_per_img+self.delay)
        self.movieSegmentTimer.stop()
        self.displaytime = time.clock()
        self.disp.setText("")
        self.disp.clear() # clear previous image
        self.vp.hide()
            
        
        # collect data from device buffer
        # only do this here for images, for video this is done per
        # segment in processMovieSegment()      
          
        # C calls to store EEG data for previous image
        if(self.atImage >= 0 and self.movieSamples == 0):
            if (self.atImage > 0):
                print '** Processing stimulus '+str(self.atImage)+' **'

            # update emostate and eventhandle
            try:
                errorCode = edk.EE_DataUpdateHandle(c_uint(0), self.data)
                errorCode1 = edk.EE_EngineGetNextEvent(self.eventHandle)
                errorCode2 = edk.EE_EmoEngineEventGetEmoState(
                    self.eventHandle,
                    self.state
                )
                if errorCode1 == 0x600:
                    if self.atImage == 1:
                        print 'Device appears to be off-line'
                        print 'No brain data will be recorded!'
                    self.online = False
                else:
                    self.online = True
            except:
                print 'An error occurred while communicating with the device'
                self.online = False
                #self.quitApp()
            if (self.atImage > 0):
                print '  status: ', errorCode, errorCode1, errorCode2

        samplesTaken = c_uint(0)
        if (self.movieSamples == 0):
            edk.EE_DataGetNumberOfSample(self.data,byref(samplesTaken))
            
        self.iSamples = samplesTaken.value + self.movieSamples
        self.totalSamples += self.iSamples        
        if  (self.atImage > 0): # completed showing a stimulus
            print '-----------------'
            print '  samples collected for stimulus '+str(self.atImage)+\
                  ': '+str(self.iSamples)

        # save data from relevant sensors to file
        
        #  at least 20 samples OR device offline (test run)
        if (self.iSamples > 20) or (not self.userAdded):             

            # channels 3-16 exported
            # other channels are sensor quality, gyro etc; useless
            channels = range(3, 17)
            channelDataType = c_double*self.iSamples
            stimdata = {}       # dict of 14 channels of data
            stimdata['channels'] = {}

            if (1 <= self.atImage <= len(self.images) and self.movieSamples == 0):
                
                for i in range(len(channels)):
                    channelData = channelDataType()
                    _check = edk.EE_DataGet(self.data,channels[i],
                                           channelData,samplesTaken)
                    channelname = self.channelnames[i]
                    stimdata['channels'][channelname] = channelData

                stimdata['attributes'] = self.images[self.atImage-1].attributes
                stimdata['response'] = self.response
                stimdata['responsetime'] = self.responsetime
                stimdata['name'] = self.images[self.atImage-1].name      
                
                # store results in alldata list          
                if not self.playingAV:
                    if self.nextPhase == "interval":
                        if self.settings.keysDuringMasks:
                            # save key presses during mask in stimulus entry                         
                            self.alldata[-1]['response'] = self.response
                            self.alldata[-1]['responsetime'] = self.responsetime                        
                    elif self.nextPhase == "mask": # just shown stimulus                       
                        self.alldata.append(stimdata)
                        
                else:   # append last audio/video segment !                    
                    stimdata['name'] += ' segment '+str(self.movieSegment)+' (incomplete)'
                    self.alldata.append(stimdata)

        # while there are images left
        if self.atImage < len(self.images):

            stimname = self.images[self.atImage].name
            self.atImage += 1
            self.movieSegment = 0
            self.movieSamples = 0            
            self.setStyleSheet(
                "QFrame { background-color: %s; \
                background-repeat: no-repeat; \
                background-position: center center; }" % self.bgcolor)
            
            # show next image
            extension = stimname.split('.')[1]
            
            # VIDEO and AUDIO            
            if str(extension) in slideshow.mediatypes:
                print 'Presenting %s' % stimname
                self.playingAV = True
                media = Phonon.MediaSource(stimname)                 
                self.vp.load(media)
                self.timer.stop()       
                self.movieSegmentTimer.start(self.millis_per_img)
                self.vp.show()
                self.vp.play()
                
            # IMAGE
            else:   
                self.playingAV = False   
                action = True
                # masks and intervals #
                if self.nextPhase == "mask":
                    self.nextPhase = "interval"
                    self.atImage -= 1          
                    if self.settings.masking == "Backward":
                        maskNr = self.atImage % len(self.masks)
                        mask = QtGui.QMovie(self.masks[maskNr],QtCore.QByteArray(), self)                         
                        self.timer.start(self.maskLength)
                        self.disp.setMovie(mask)
                        mask.start()
                    # TODO: forward masking
                    action = False
                elif self.nextPhase == "interval" and action:
                    self.nextPhase = "stimulus"
                    self.atImage -= 1   
                    if self.millisInterval > 0:
                        self.timer.start(self.millisInterval)                    
                        self.disp.setMovie(self.transparant)
                        self.transparant.start()
                    if self.settings.enableEyeTracker:
                        self.settings.eyetracker.stopStim()
                    action = False
                elif self.nextPhase =='stimulus' and action:
                    print 'Presenting %s' % stimname
                    stimulus = QtGui.QMovie(stimname,QtCore.QByteArray(), self) 
                    self.disp.setMovie(stimulus)
                    stimulus.start()
                    if self.settings.masking != 'None': self.nextPhase = "mask"
                    else: self.nextPhase = "interval"
                    if self.settings.enableEyeTracker:
                        self.settings.eyetracker.startStim(stimname)                        

            self.response = 'None'
            self.responsetime = 0

        # Last mask
        elif (self.atImage == len(self.images)) and (self.nextPhase == 'mask')\
            and self.settings.masking == "Backward":
            if not self.playingAV:          
                maskNr = self.atImage % len(self.masks)
                mask = QtGui.QMovie(self.masks[maskNr],QtCore.QByteArray(), self)                         
                self.timer.start(self.maskLength)
                self.disp.setMovie(mask)
                mask.start()
                self.nextPhase = 'lastMask'
                    
        elif self.nextPhase == 'lastMask':
            self.alldata[-1]['response'] = self.response
            self.alldata[-1]['responsetime'] = self.responsetime   
            self.nextPhase = 'done!'

        else:
            print '\nAll images shown!'
            self.disp.setText('')
            if self.settings.enableEyeTracker:
                self.settings.eyetracker.stopStim()
                self.trackerData = 'Tracker data:\n'+\
                    self.settings.eyetracker.getData()
            self.writeOutput()
                        
    def writeOutput(self):
            ##############################################
            # Save data recorded in self.alldata to file #
            # and perform Fourier transformation         #
            ##############################################
        
        print 'Saving data...'
        wavebands = ['alpha', 'beta', 'delta', 'theta']

        if self.online or self.recordKeys:
            self.csv = open(self.csvname,'w')
            self.arff = open(self.arffname,'w')
            print 'Processing data for %s stimuli' % str(len(self.alldata))            
            if self.online:
                print 'Performing Fast Fourier Transform...'
                                            
            # CSV; write column headers
            headers = 'Index;Stimulus'
            for a in self.images[0].attributes:
                (attr,_val) = a
                headers = ';'.join([headers,str(attr)])
            if self.recordKeys:
                headers = ';'.join([headers,'Response','Resp time'])
            if self.online:
                for channel in self.channelnames:
                    for waveband in wavebands:
                        name = '%s %s' % (channel,waveband)
                        headers = ';'.join([headers,name])            
            self.csv.write(headers+'\n')
            
            ## ARFF; write column headers
            title = (self.subject.name+self.date).replace(' ','_')
            title = title.replace('\'','')
            self.arff.write("@RELATION "+title+"\n\n")
            
            # find all key responses for ARFF nominal attribute declaration 
            responses = []
            for stimulus in self.alldata:
                response = stimulus['response']
                response = response.replace(';','semicolon')
                if not response in responses:
                    responses.append(response)
            responseStr = '{'+','.join(responses)+'}'
            
            for at in range(len(self.images[0].attributes)):
                (attr,val) = self.images[0].attributes[at]
                values = []
                for i in range(len(self.images)):
                    (_imat, imval) = self.images[i].attributes[at]                    
                    if not(imval in values):
                        values.append(str(imval))                                            
                valueStr = '{'+','.join(values)+'}'             
                   
                self.arff.write('@ATTRIBUTE '+str(attr)+valueStr+'\n')
            if self.recordKeys:
                self.arff.write('@ATTRIBUTE Response '+responseStr+'\n')
                self.arff.write('@ATTRIBUTE Response_time REAL\n')
            if self.online:
                for channel in self.channelnames:
                    for waveband in wavebands:
                        self.arff.write('@ATTRIBUTE %s-%s REAL\n' % (channel,waveband))
            self.arff.write('\n@DATA\n\n')

            # write values for every stimulus  
            ## CSV + ARFF
            for i in range(len(self.alldata)):
                stimulus = self.alldata[i]
                name = os.path.basename(stimulus['name'])
                csv = ';'.join([str(i+1),name])
                arff = ''
                
                for a in stimulus['attributes']:
                    (attr,val) = a
                    csv = ';'.join([csv,str(val)])
                    if arff == '':
                        arff = str(val)
                    else:
                        arff = ','.join([arff,str(val)])
                if self.recordKeys:
                    r = str(stimulus['response'])
                    rs = str(stimulus['responsetime'])
                    csv = ';'.join([csv,r,rs])
                    arff = ','.join([arff,r,rs])
                if self.online:
                    for channel in stimulus['channels']:
                        channeldata = stimulus['channels'][channel]
                        bandscores = doFFT(channeldata, channel)
                        for waveband in bandscores:
                            csv = ';'.join([csv,str(bandscores[waveband])])
                            arff = ','.join([arff,str(bandscores[waveband])])
                self.csv.write(csv+'\n')
                self.arff.write(arff+'\n')

            print 'Done! Closing output file'
            self.csv.close()
            self.arff.close()
            
        if self.settings.enableEyeTracker:
            eyetrackname = self.outputdir+self.subject.name+self.date+'.eye'
            eyetrackfile = open(eyetrackname,'w')
            from win32api import GetSystemMetrics
            import re
            width = GetSystemMetrics (0)
            height = GetSystemMetrics (1)
            txtcoords = re.findall(r'FPOGX="([\d\.]*).*FPOGY="([\d\.]*).*STIM([\d]*)',\
                                    self.trackerData)
            for x,y,name in txtcoords:
                fixed = [name, float(x)*width, float(y)*height]
                eyetrackfile.write('\t'.join(fixed))
                
            eyetrackfile.write(self.trackerData)
            eyetrackfile.close()            
            
        else:
            print 'No brain activity or user data recorded, no output file created'
        self.quitApp()
    
        
    # called every few seconds when a movie is playing             
    def processMovieSegment(self):        
        print 'Movie segment', self.movieSegment
        
        # C calls to store EEG data for previous segment
            # update emostate and eventhandle
        try:
            edk.EE_DataUpdateHandle(c_uint(0), self.data)
            edk.EE_EngineGetNextEvent(self.eventHandle)
            edk.EE_EmoEngineEventGetEmoState(
                self.eventHandle,
                self.state
            )
        except:
            print 'An error occurred while communicating with the device!'
            #self.quitApp()        
        
        samplesTaken = c_uint(0)
        edk.EE_DataGetNumberOfSample(self.data,byref(samplesTaken))
        samples = samplesTaken.value
        self.movieSamples += samples # total number of samples for this movie
        print '  samples collected for movie segment '+str(self.movieSegment)+\
            ': '+str(samples)
            
        # save data from relevant sensors to file
        
        #  at least 20 samples OR device off-line (test run)
        if (samples > 20) or (not self.userAdded):             

            # channels 3-16 exported
            # other channels are sensor quality, gyro etc; not relevant
            channels = range(3, 17)
            channelDataType = c_double*samples
            stimdata = {}     # dict of 14 channels of data
            stimdata['channels'] = {}     
            
                
            for i in range(len(channels)):
                channelData = channelDataType()
                _check = edk.EE_DataGet(self.data,channels[i],
                                       channelData,samplesTaken)
                channelname = self.channelnames[i]
                stimdata['channels'][channelname] = channelData

            stimdata['attributes'] = self.images[self.atImage-1].attributes
            stimdata['response'] = self.response
            stimdata['responsetime'] = self.responsetime
            stimdata['name'] = self.images[self.atImage-1].name + " segment " + str(self.movieSegment)
            self.alldata.append(stimdata)
            self.movieSegmentTimer.start(self.millis_per_img)    

            # reset necessary values
            self.movieSegment += 1
            self.response = 'None'
            self.responsetime = 0
            self.displaytime = time.clock()

    def keyPressEvent(self, event):
        if type(event) == QtGui.QKeyEvent:
            self.haveHadKeypresses = True            
            responsetime = time.clock() - self.displaytime
            resp = str(event.text()).upper()
            if resp == ' ':
                if self.response == 'None':
                    self.response = 'Space'
                    self.responsetime = responsetime
                self.update_image()
            elif resp.strip() == '':
                self.response = 'None'
                self.responsetime = 0                
            else:
                self.response = resp
                self.responsetime = responsetime
            event.accept()            
        else:
            event.ignore()  

    # close down properly
    # called with Escape or by errors
    def quitApp(self):
        self.timer.stop()
        self.countdownTimer.stop()
        self.movieSegmentTimer.stop()
        self.vp.stop()
        try:
            edk.EE_EngineDisconnect()
            print 'Disconnected from EmoEngine, closing down..'
            edk.EE_EmoStateFree(self.state)
            edk.EE_EmoEngineEventFree(self.eventHandle)
        except:
            pass

        self.close()
        time.sleep(1)
        return 0
