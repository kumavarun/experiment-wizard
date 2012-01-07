
        #########################################
        #                                       #
        #           EXPERIMENT WIZARD           #
        #               Main file               #
        #            by Jeroen Kools            #
        #        jkools@science.uva.nl          #
        #              2010-2012                #
        #                                       #
        #########################################

from PyQt4.QtCore import QObject, QString, SIGNAL, Qt
from PyQt4.QtGui import QApplication, QDialog, QComboBox, QDialogButtonBox, \
     QFileDialog, QWidget, QTextEdit, QShortcut, QKeySequence, QMainWindow
from slideshowDialog import slideshow
import sys, os, getpass, re, gui, _winreg, subprocess, pickle, datetime, eyetracker

                
class ExperimentWizard(QMainWindow):
        def __init__(self, app, parent=None):
            QMainWindow.__init__(self)
            
            self.version = '1.21b' ### January 7, 2012
            print 'Starting Experiment Wizard %s' % self.version          
            self.parent = parent
            self.app = app
            self.statusbar = self.statusBar()
            self.statusbar.showMessage("Welcome!", 3500)     
            print ' Loading statistics..'       
            if os.path.exists('stats.cfg'):
                statsfile = open('stats.cfg', 'r')
                self.stats = pickle.load(statsfile)
                self.stats.lastChecked = datetime.datetime.now() 
                statsfile.close()
            else:
                self.stats = stats(datetime.datetime.now()) 
                
            print ' Initializing user interface..'
            self.ui = gui.experimentWizardUi()
            self.ui.setupUi(self)
            print ' Loading configuration..'
            self.settings = Settings(self)
            self.deletedStim = -1           # index of last deleted stimulus
            self.deletedSubj = -1           # index of last deleted subject
            self.lastOpenFolder = ''        # remember and use last stimulus folder
            self.lastSaveFolder = ''        
            self.adderSettings = {}         # attributes of last added stimulus            
            
            # connect dialog buttons
            QObject.connect(self.ui.stimAttAddButton,\
                    SIGNAL("clicked()"),self.showAttributeEditor)
            QObject.connect(self.ui.subjAttAddButton,\
                    SIGNAL("clicked()"),self.showAttributeEditor)    
            QObject.connect(self.ui.stimAttRemoveButton,\
                    SIGNAL("clicked()"),self.removeAttribute)                        
            QObject.connect(self.ui.subjAttRemoveButton,\
                    SIGNAL("clicked()"),self.removeAttribute)
            
            QObject.connect(self.ui.subjAddButton,\
                    SIGNAL("clicked()"),self.showEntityAdder)
            QObject.connect(self.ui.subjDeleteButton,\
                    SIGNAL("clicked()"),self.deleteSubject)
            QObject.connect(self.ui.stimAddButton,\
                    SIGNAL("clicked()"),self.showEntityAdder)
            QObject.connect(self.ui.stimDeleteButton,\
                    SIGNAL("clicked()"),self.deleteSubject)

            QObject.connect(self.ui.recordButton,\
                    SIGNAL("clicked()"),self.runExperiment)
            QObject.connect(self.ui.saveButton,\
                    SIGNAL("clicked()"),self.saveExperiment)
            QObject.connect(self.ui.loadButton,\
                    SIGNAL("clicked()"),self.loadExperiment)
            QObject.connect(self.ui.exitButton,\
                    SIGNAL("clicked()"),self.exit)
            
            QObject.connect(self.ui.stimDownButton,\
                    SIGNAL("clicked()"),self.stimDown)
            QObject.connect(self.ui.stimUpButton,\
                    SIGNAL("clicked()"),self.stimUp)
            QShortcut(QKeySequence("Escape"), self, self.exit )
            
            # connect to eye tracker
            self.eyeTracker = None
            if self.settings.haveEyeTracker: # check if eye tracker software is installed
                try:                         # try connecting
                    print ' Establishing connection to eye tracker..'
                    self.settings.eyetracker = eyetracker.tracker()
                except:                      # eye tracker installed but not connected
                    self.settings.haveEyeTracker = False
            print 'Started successfully!'
            
        def reset(self):
            self.settings.reset(self)
            self.settings.show(self)
            self.refreshAttributes()
            self.refreshEntities()
                
        #@#  button methods #@#
        
        def showAttributeEditor(self):
            # check source of signal: subject or stimulus attribute?
            if self.sender() == self.ui.stimAttAddButton:
                            self.attEditDialog = attributeEditor('stimulus', self)
            if self.sender() == self.ui.subjAttAddButton:
                            self.attEditDialog = attributeEditor('subject', self)   
            self.attEditDialog.show()                       

        # called after an attribute is added/removed
        # to update lists shown in ui
        def refreshAttributes(self):
            self.ui.subjAttList.clear()
            self.ui.stimAttList.clear()       
            
            for (name,vals) in self.settings.subjectAttributes:
                if not name == "":
                    self.ui.subjAttList.addItem(name.simplified())
                    for val in vals:
                        s = "  * "+str(val.simplified())
                        if not s == "":
                            self.ui.subjAttList.addItem(s)
                            
            for (name,vals) in self.settings.stimulusAttributes:
                if not name == "":
                    self.ui.stimAttList.addItem(name.simplified())
                    for val in vals:                
                        s = "  * "+str(val.simplified())
                        if not s == "":
                            self.ui.stimAttList.addItem(s)          

        def removeAttribute(self):
            source = self.sender()
                                    
            if source == self.ui.stimAttRemoveButton:
                selection = self.ui.stimAttList.selectedItems()[0].text()
                selection = selection.replace("  * ","")
                for (name,vals) in self.settings.stimulusAttributes:
                    if name == selection:
                        self.settings.stimulusAttributes.remove((name,vals))
                    if selection in vals:
                        vals.remove(selection)
                            
            if source == self.ui.subjAttRemoveButton:
                selection = self.ui.subjAttList.selectedItems()[0].text()
                selection = selection.replace("  * ","")                        
                for (name,vals) in self.settings.subjectAttributes:
                    if name == selection:
                        self.settings.subjectAttributes.remove((name,vals))                                  
                    if selection in vals:
                        vals.remove(selection)                          
                            
            self.refreshAttributes()
            self.refreshEntities()

        def showEntityAdder(self):
            source = self.sender()

            if source == self.ui.subjAddButton:
                self.entityAdder = entityAdder('subject',self)
            if source == self.ui.stimAddButton:
                self.entityAdder = entityAdder('stimulus',self)

            self.entityAdder.show()

        # updates the list widgets with subjects and stimuli after insertions/deletions
        def refreshEntities(self):
            self.ui.stimulusList.clear()
            self.ui.subjectList.clear()
            self.invalidSubjects = False
            self.invalidStimuli = False

            for i in range(len(self.settings.subjects)):
                subject = self.settings.subjects[i]
                self.ui.subjectList.addItem(subject.name)
                if len(subject.getAttributes()) != len(self.settings.subjectAttributes):
                    self.ui.subjectList.item(i).setBackgroundColor(Qt.red)
                    self.ui.subjectList.item(i).setToolTip("This subject's attributes don't match with the currently defined subject attributes!")
                    self.invalidSubjects = True

            for i in range(len(self.settings.stimuli)):
                stimulus = self.settings.stimuli[i]
                displayname = os.path.basename(str(stimulus.name))
                self.ui.stimulusList.addItem(displayname)
                if len(stimulus.getAttributes()) != len(self.settings.stimulusAttributes):
                    self.ui.stimulusList.item(i).setBackgroundColor(Qt.red)
                    self.ui.stimulusList.item(i).setToolTip("This stimulus' attributes don't match with the currently defined stimulus attributes!")
                    self.invalidStimuli = True                    

            if self.deletedStim != -1:
                self.ui.stimulusList.setCurrentRow(self.deletedStim)
                self.deletedStim = -1

            if self.deletedSubj != -1:
                self.ui.subjectList.setCurrentRow(self.deletedSubj)
                self.deletedSubj = -1

        def deleteSubject(self):
                source = self.sender()

                try:
                    if source == self.ui.subjDeleteButton:
                        selection = self.ui.subjectList.selectedItems()[0].text()
                        selectionItem = self.ui.subjectList.selectedItems()[0]
                        index = min(len(self.settings.subjects)-2,self.ui.subjectList.row(selectionItem))
                        self.deletedSubj = index
                        for subject in self.settings.subjects:
                            if subject.name == selection:
                                self.settings.subjects.remove(subject)
                        self.statusbar.showMessage("Subject deleted", 2000)
                        self.refreshEntities()
                                            
                    if source == self.ui.stimDeleteButton:
                        selection = self.ui.stimulusList.selectedItems()[0].text()
                        selectionItem = self.ui.stimulusList.selectedItems()[0]
                        index = min(len(self.settings.stimuli)-2,self.ui.stimulusList.row(selectionItem))
                        self.deletedStim = index                  
                        for stimulus in self.settings.stimuli:
                            displayname = os.path.basename(stimulus.name)                               
                            if displayname == selection:
                                self.settings.stimuli.remove(stimulus)
                        self.statusbar.showMessage("Stimulus deleted", 2000)
                        self.refreshEntities()

                except:
                        pass

        def stimDown(self):
            try:
                selectionItem = self.ui.stimulusList.selectedItems()[0]
                currentIndex = self.ui.stimulusList.row(selectionItem)
                targetIndex = min(len(self.settings.stimuli) - 1, currentIndex + 1)
                entity = self.settings.stimuli[currentIndex]                        
                
                # remove from ui and app lists
                self.ui.stimulusList.takeItem(currentIndex)
                self.settings.stimuli.remove(entity)                                

                # re-add in new position
                if targetIndex == self.ui.stimulusList.count():
                    self.settings.stimuli.append(entity)
                    self.ui.stimulusList.addItem(selectionItem)
                else:
                    self.ui.stimulusList.insertItem(targetIndex, selectionItem)
                    self.settings.stimuli.insert(targetIndex, entity)
                self.ui.stimulusList.setCurrentItem(selectionItem)
                            
            except Exception as e:
                    print 'Can\'t move selection down! \n'+str(e)

        def stimUp(self):
            try:
                selectionItem = self.ui.stimulusList.selectedItems()[0]
                currentIndex = self.ui.stimulusList.row(selectionItem)
                targetIndex = max(0, currentIndex - 1)
                entity = self.settings.stimuli[currentIndex]

                # remove from ui and app lists
                self.ui.stimulusList.takeItem(currentIndex)
                self.settings.stimuli.remove(entity)

                # re-add in new position
                self.settings.stimuli.insert(targetIndex, entity)
                self.ui.stimulusList.insertItem(targetIndex, selectionItem)
                self.ui.stimulusList.setCurrentItem(selectionItem)
                        
            except Exception as e:
                print 'Can\'t move selection up!\n' +str(e)

        def exit(self):
            if self.settings.hasRunExperiment:
                del self.slide.vp # prevents crash on exit?
            self.stats.save()
            QApplication.closeAllWindows();
            QApplication.exit()
            QApplication.quit()

        def saveExperiment(self):              
            user = getpass.getuser()
            folder = os.path.expanduser('~'+user+'\Desktop')
            if self.lastSaveFolder != '':
                folder = self.lastSaveFolder
            
            filename = str(QFileDialog.getSaveFileName(self, "Save File",\
                folder,"Experiment (*.exp)"))
            if filename == '':
                return

            if os.path.exists(filename):
                os.remove(filename)    # after overwrite confirmation, remove older version
            out = open(filename, 'a')

            out.write('version=%s\n' % str(self.version)) 
            # write options
            out.write('randomizeOrder=%s\n' % str(self.ui.randomizeCheckBox.isChecked()))
            out.write('spaceToContinue=%s\n' % str(self.ui.lastUntilSpaceCheckBox.isChecked()))
            out.write('backgroundColor=%s\n' % str(self.ui.backgroundColorComboBox.currentIndex()))
            out.write('stimulusDuration=%s\n' % str(self.ui.durationSpinbox.value()))
            out.write('interStimulusInterval=%s\n' % str(self.ui.intervalSpinbox.value()))
            out.write('recordKeys=%s\n' % str(self.ui.recordKeysCheckBox.isChecked()))
            
            out.write('generateARFF=%s\n' % str(self.settings.generateARFF))
            out.write('generateCSV=%s\n' % str(self.settings.generateCSV))
            out.write('saveRaw=%s\n' % str(self.settings.saveRawEEG))
            out.write('CSVseparator=%s\n' % str(self.settings.CSVseparator))
            out.write('outputPrefix=%s\n' % str(self.settings.outputPrefix))
            out.write('outputFolder=%s\n' % str(self.settings.outputFolder) )           
            
            out.write('maskFolder=%s\n' % str(self.settings.maskfolder))
            out.write('maskLength=%s\n' % str(self.settings.masklength))
            out.write('masking=%s\n'    % str(self.settings.masking))
            out.write('keysDuringMasks=%s\n'   % str(self.settings.keysDuringMasks))
            out.write('randomizeMasks=%s\n'    % str(self.settings.randomizeMasks))
            
            out.write('countDownFrom=%s\n' % str(self.settings.countdownFrom))
            
            # write subject attributes
            for (attr,vals) in self.settings.subjectAttributes:
                out.write('BeginSubjectAttribute=%s\n' % attr)
                for val in vals:
                    out.write('\tValue=%s\n' % val)
                out.write('EndSubjectAttribute=%s\n' % attr)
            
            # write stimuli attributes
            for (attr,vals) in self.settings.stimulusAttributes:
                out.write('BeginStimulusAttribute=%s\n' % attr)
                for val in vals:
                    out.write('\tValue=%s\n' % val)
                out.write('EndStimulusAttribute=%s\n' % attr)
            
            # write subject names and attr/values
            for subject in self.settings.subjects:
                out.write('BeginSubject=%s\n' % subject.name)
                for (attr,val) in subject.attributes:
                    out.write('\tAttributeValue=(%s,%s)\n' % (attr,val))
                out.write('EndSubject=%s\n' % subject.name)
                    
            # write stimuli file names and attr/values
            for stimulus in self.settings.stimuli:
                out.write('BeginStimulus=%s\n' % stimulus.name)
                for (attr,val) in stimulus.attributes:
                    out.write('\tAttributeValue=(%s,%s)\n' % (attr,val))
                out.write('EndStimulus=%s\n' % stimulus.name)

            out.close()

        def loadExperiment(self):
            self.reset()
        
            user = getpass.getuser()
            folder = os.path.expanduser('~'+user+'\Desktop')
            if self.lastOpenFolder != '':
                    folder = self.lastOpenFolder
            filename = QFileDialog.getOpenFileName(\
                    self, 'Select file',folder,\
                    "Experiment files (*.exp)")

            if filename == '':
                line = ''
            else:
                input = open(filename,'r')
                line = input.readline()
            cycle = 0

            while not (line == ''):         # not at end of file

                cycle += 1
                if cycle > 10000:
                    print 'Error! Invalid experiment file!'
                    break           # prevent eternal loop
                
                var = line.split('=')[0].strip()
                val = line.split('=')[1].strip()
                # TODO: catch invalid lines!

                # options
                if var == 'randomizeOrder':
                    self.ui.randomizeCheckBox.setChecked(val == 'True')                        
                if var == 'spaceToContinue':
                    self.ui.lastUntilSpaceCheckBox.setChecked(val == 'True')
                if var =='recordKeys':
                    self.ui.recordKeysCheckBox.setChecked(val == 'True')                    
                if var == 'backgroundColor':
                    self.ui.backgroundColorComboBox.setCurrentIndex(int(val))
                if var == 'stimulusDuration':
                    self.ui.durationSpinbox.setValue(float(val))
                if var == 'interStimulusInterval':
                    self.ui.intervalSpinbox.setValue(float(val))
                    
                if var == 'generateARFF':
                    self.settings.generateARFF = (val == 'True')
                if var == 'generateCSV':
                    self.settings.generateCSV = (val == 'True')
                if var == 'saveRaw':
                    self.settings.saveRawEEG = (val == 'True')
                if var == 'CSVseparator':
                    self.settings.CSVseparator = val
                if var == 'outputPrefix':
                    self.settings.outputPrefix = val
                if var == 'outputFolder':
                    self.settings.outputFolder = val
                
                if var == 'maskFolder':
                    self.settings.maskfolder = val
                if var == 'maskLength':
                    self.settings.masklength = val
                if var == 'masking':
                    self.settings.masking = val
                if var == 'keysDuringMasks':
                    self.settings.keysDuringMasks = (val == 'True')
                if var == 'randomizeMasks':
                    self.settings.randomizeMasks = (val == 'True')
                  
                # subject attributes
                if var == 'BeginSubjectAttribute':
                    vals = []
                    name = QString(val)

                    while not ('EndSubjectAttribute' in line):
                        line = input.readline()                                        
                        var = QString(line.split('=')[0].strip())
                        val = QString(line.split('=')[1].strip())                               
                        if var == 'Value':
                            vals.append(val)                                               
                    self.settings.subjectAttributes.append((name,vals))
                                
                if var == 'BeginStimulusAttribute':
                    vals = []
                    name = QString(val)
                                                                                   
                    while not ('EndStimulusAttribute' in line):
                        line = input.readline()                                         
                        var = QString(line.split('=')[0].strip())
                        val = QString(line.split('=')[1].strip())
                        if var == 'Value':
                            vals.append(val)                                                                                      
                    self.settings.stimulusAttributes.append((name,vals))

                if var == 'BeginSubject':
                    name = val
                    subj = entity(name, 'subject')
                    
                    while not ('EndSubject' in line):
                        line = input.readline()
                        var = line.split('=')[0].strip()
                        val = line.split('=')[1].strip()
                        if var == 'AttributeValue':
                            parts = re.findall(r'\w+',val)
                            attrName = parts[0]
                            attrVal = parts[1]
                            subj.addAttribute(attrName,attrVal)
                                    
                    self.settings.subjects.append(subj)
                                
                if var == 'BeginStimulus':
                    location = val
                    stim = entity(location, 'stimulus')
                    
                    while not ('EndStimulus' in line):
                        line = input.readline()                                        
                        var = line.split('=')[0].strip()
                        val = line.split('=')[1].strip()
                        if var == 'AttributeValue':
                            parts = re.findall(r'\w+',val)
                            attrName = parts[0]
                            attrVal = ' '.join(parts[1:])
                            stim.addAttribute(attrName,attrVal)

                    self.settings.stimuli.append(stim)

                # after all the ifs, still looping over lines                                        
                line = input.readline()    # get next line

            # done with file
            if filename != '':
                input.close()
                self.refreshAttributes()
                self.refreshEntities()
                self.settings.update(self)

        def runExperiment(self):
            self.statusbar.showMessage("Starting experiment...", 3000)
            self.settings.hasRunExperiment = True
            self.settings.update(self) 

            # Try to use selected subject; if that doesn't work
            # and there's only one subject, use that one
            # else, anonymous
            subj = entity('Anonymous', 'subject')
            if (len(self.settings.subjects) > 0) or (len(self.ui.subjectList.selectedItems()) > 0):
                if len(self.ui.subjectList.selectedItems()) > 0:
                    selectedItem = self.ui.subjectList.selectedItems()[0]
                    i = self.ui.subjectList.row(selectedItem)
                    subj= self.settings.subjects[i]
                elif len(self.settings.subjects) == 1:
                    subj = self.settings.subjects[0]

            if len(self.settings.stimuli) > 0:
                self.slide = slideshow(subj, self.settings, self.app)
                self.slide.show()
                self.slide.setFocus() 
                self.stats.experimentsRun += 1
                self.stats.stimuliDisplayed += len(self.settings.stimuli)
        
        # Menu methods
        
        def about(self):
            self.a = gui.about()
            self.a.show()
        
        def getKeys(self):
            # init return vals with empty strings
            edk = consumer_version = testbench = haveTracker = version = ''
            eyetracker = False
            
            try: 
                edk_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, \
                                      "SOFTWARE\Emotivsystems\currentversion")
                edk = _winreg.QueryValueEx(edk_key, "InstallPath")
                version = _winreg.QueryValueEx(edk_key, "version")[0]
            except:
                pass # fail silently
            
            # TODO: find registry key for Consumer Version                
            try:
                consumer_version_key = ''
                consumer_version = _winreg.QueryValueEx(consumer_version_key, "InstallPath")
            except:
                pass # fail silently
                        
            try:
                testbench_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, \
                                      "SOFTWARE\Emotiv Testbench\currentversion")
                testbench = _winreg.QueryValueEx(testbench_key, "InstallPath")
            except:
                testbench = edk # use EDK path, since there is no separate reg entry in 1.0.0.4
            
            try:
                haveTracker = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, \
                                      "SOFTWARE\Mirametrix\Tracker")
            except:
                pass # fail silently        
            if haveTracker: eyetracker = True
            
            keys = {'edk':edk,
                    'edkVersion': version,
                    'consumer': consumer_version, 
                    'testbench': testbench, 
                    'eyetracker': eyetracker}
            return keys 
            
        def controlPanel(self):
            keys = self.getKeys()
            if keys['edk'] == '':   # no EDK found, try Consumer Version
                if keys['consumer'] == '':
                    self.statusbar.showMessage("Emotiv Control Panel not found", 3000)
                    return
                cp = os.path.realpath(keys['consumer'][0])+'\EmotivControlPanel.exe'
            
            else:                   # EDK
                cp = keys['edk'][0]
                cp = os.path.realpath(cp)+'\EmotivControlPanel.exe'
            self.statusbar.showMessage("Starting Emotiv Control Panel...", 3000)
            subprocess.Popen(cp)
        
        def testBench(self):
            keys = self.getKeys()
            loc = ''
            
            if keys['testbench'] == '':
                    print "Emotiv Testbench not found"    
                    return
            else:
                if os.path.exists(keys['testbench'][0]+'\Testbench.exe'):
                    loc = keys['testbench'][0]
            if loc != '':
                testbench = loc + '\TestBench.exe'
                self.statusbar.showMessage("Starting Emotiv Testbench...", 3000)
                subprocess.Popen(testbench)
            else:
                print 'Could not find Testbench path'
            
        def tutorial(self):
            os.startfile('http://www.beta-lab.nl/content/tutorial')
            
        def showSettings(self):
            self.settingsDialog = SettingsDialog(self)
            self.settingsDialog.show()
            
        def showStats(self):
            self.statsWindow = statsDialog(self)
            self.statsWindow.show()
            

class SettingsDialog(QDialog):
    def __init__(self, parent):
        QWidget.__init__(self,parent)
        self.ui = gui.settingsUi()
        self.ui.setupUi(self)  
        self.parent = parent      
        
        # Load current settings in dialog
        # output settings
        self.ui.generateARFFCheckBox.setChecked(self.parent.settings.generateARFF) 
        self.ui.generateCSVCheckBox.setChecked(self.parent.settings.generateCSV)
        self.ui.saveRawEEGCheckBox.setChecked(self.parent.settings.saveRawEEG)
        self.ui.comboBox.setCurrentIndex(self.ui.comboBox.findText(\
                                self.parent.settings.CSVseparator)) 
        self.ui.lineEdit_2.setText(self.parent.settings.outputPrefix)  
        self.ui.lineEdit.setText(self.parent.settings.outputFolder)    
        
        # masking settings
        self.ui.comboBox_3.setCurrentIndex(self.ui.comboBox_3.findText(\
                                self.parent.settings.masking) )
        self.ui.comboBox_2.setCurrentIndex(self.ui.comboBox_2.findText(\
                                self.parent.settings.masklength))
        self.ui.lineEdit_3.setText(self.parent.settings.maskfolder) 
        self.ui.checkBox_4.setChecked(self.parent.settings.keysDuringMasks) 
        self.ui.checkBox_5.setChecked(self.parent.settings.randomizeMasks)
        # processing settings
        # nothing yet
        
        # misc settings
        self.ui.spinBox.setValue(self.parent.settings.countdownFrom)
        self.ui.calibrateButton.setEnabled(self.parent.settings.haveEyeTracker)
        self.ui.eyetrackCheckBox.setChecked(self.parent.settings.enableEyeTracker)
        self.ui.eyetrackCheckBox.setEnabled(self.parent.settings.haveCalibrated)
        
    def accept(self):
        self.parent.statusBar().showMessage('Settings changed', 2000)
        
        # output settings
        self.parent.settings.generateARFF = self.ui.generateARFFCheckBox.isChecked()
        self.parent.settings.generateCSV = self.ui.generateCSVCheckBox.isChecked()
        self.parent.settings.saveRawEEG = self.ui.saveRawEEGCheckBox.isChecked()
            # TODO: generate spectrograms
        self.parent.settings.CSVseparator = self.ui.comboBox.currentText()
        self.parent.settings.outputPrefix = self.ui.lineEdit_2.text().trimmed() # TODO: remove invalid chars 
        self.parent.settings.outputFolder = self.ui.lineEdit.text().trimmed()    
        # masking settings
        self.parent.settings.masking = self.ui.comboBox_3.currentText()
        self.parent.settings.masklength = self.ui.comboBox_2.currentText()
        self.parent.settings.maskfolder = self.ui.lineEdit_3.text()
        self.parent.settings.keysDuringMasks = self.ui.checkBox_4.isChecked()
        self.parent.settings.randomizeMasks = self.ui.checkBox_5.isChecked()       
        # processing settings
        # nothing yet
        # misc settings
        self.parent.settings.countdownFrom = self.ui.spinBox.value()
        self.parent.settings.enableEyeTracker = self.ui.eyetrackCheckBox.isChecked()
        
        self.close()
        
    def setMaskFolder(self):
        user = getpass.getuser()
        folder1 = os.path.expanduser('~'+user+'\Desktop')
        if self.parent.lastOpenFolder != '':
                folder1 = self.parent.lastOpenFolder
        maskfolder = QFileDialog.getExistingDirectory(\
                self, 'Select folder',folder1)
        self.ui.lineEdit_3.setText(maskfolder)

    def setOutputFolder(self):
        user = getpass.getuser()
        folder1 = os.path.expanduser('~'+user+'\Desktop')
        if self.parent.lastOpenFolder != '':
                folder1 = self.parent.lastOpenFolder
        outputfolder = QFileDialog.getExistingDirectory(\
                self, 'Select folder',folder1)
        self.ui.lineEdit.setText(outputfolder) 
        
    def calibrate(self):
        if self.parent.settings.haveEyeTracker:
            self.ui.eyetrackCheckBox.setEnabled(True)
            self.parent.settings.eyetracker.calibrate()
            self.parent.settings.haveCalibrated = True

class Settings:
    def __init__(self, parent):
        self.subjectAttributes = []
        self.stimulusAttributes = []
        self.subjects = []
        self.stimuli = []
            
        self.hasRunExperiment = False # used in shutdown
        
        self.recordKeys =  True
        self.shuffle = False
        self.untilSpacePressed = False
        parent.ui.recordKeysCheckBox.setChecked(True)
        parent.ui.randomizeCheckBox.setChecked(False)
        parent.ui.lastUntilSpaceCheckBox.setChecked(False)
        self.millisPerImg = 5000
        self.millisMaskDuration = 1000
        self.bgColor = 'Grey'
        
        # output settings
        self.generateARFF = True
        self.generateCSV = True
        self.saveRawEEG = False
        self.CSVseparator = 'Semicolon'
        self.outputPrefix = '' 
        self.outputFolder = ''
         
        # masking settings
        self.masking = 'None'
        self.masklength = 'Until <space>'
        self.maskfolder = ''
        self.keysDuringMasks = False
        self.randomizeMasks = False
        
        # processing settings
        # nothing yet
        
        # misc settings
        self.countdownFrom = 3  
        self.enableEyeTracker = False            
        self.haveCalibrated = False    
        self.haveEyeTracker = parent.getKeys()['eyetracker']
        
    def reset(self, parent):
        # prevent some values from being reset
        ThaveCalibrated = self.haveCalibrated
        TenableEyetracker = self.enableEyeTracker
        
        self.__init__(parent)
        
        self.haveCalibrated = ThaveCalibrated
        self.enableEyeTracker = TenableEyetracker
        
    # take values from UI to settings
    def update(self, parent):
        self.shuffle = parent.ui.randomizeCheckBox.isChecked()
        self.recordKeys = parent.ui.recordKeysCheckBox.isChecked()
        self.untilSpacePressed = parent.ui.lastUntilSpaceCheckBox.isChecked()
             
        self.millisPerImg = 1000 * parent.ui.durationSpinbox.value()
        if self.untilSpacePressed:
            self.millisPerImg = 600e3                       # 10 minutes
        self.millisMaskDuration = 1000 * parent.ui.intervalSpinbox.value()
        self.bgColor = str(parent.ui.backgroundColorComboBox.currentText())
    
    # set UI to match settings (reverse of update)    
    def show(self, parent):
        parent.ui.randomizeCheckBox.setChecked(self.shuffle)
        parent.ui.recordKeysCheckBox.setChecked(self.recordKeys)
        parent.ui.lastUntilSpaceCheckBox.setChecked(self.untilSpacePressed)
             
        if not self.untilSpacePressed:
            parent.ui.durationSpinbox.setValue(self.millisPerImg/1000)
        parent.ui.intervalSpinbox.setValue(self.millisMaskDuration/1000)
        parent.ui.backgroundColorComboBox.setCurrentIndex(\
            parent.ui.backgroundColorComboBox.findText(self.bgColor))

class statsDialog(QDialog):
    def __init__(self, parent=None):
        QWidget.__init__(self,parent)
        self.ui = gui.statsUi()
        self.ui.setupUi(self)
        self.setWindowTitle("Statistics")
        
        parent.stats.refresh()
        self.stats = parent.stats
        l1 = str(self.stats.experimentsRun)
        l2 = str(self.stats.stimuliDisplayed)
        l3 = self.stats.installDate.strftime('%b %d %Y %H:%M')
        l4 = self.stats.totalRunTime 
        hours = l4.seconds/3600
        minutes = (l4.seconds%3600)/60
        seconds = l4.seconds%60
        m4 = '%s days, %i:%02i:%02i' % (l4.days,hours,minutes,seconds)
                
        self.ui.label.setText( "Experiments run: %42s " % l1 )
        self.ui.label_2.setText("Stimuli displayed: %42s " % l2 )
        self.ui.label_3.setText("Installed: %43s " % l3 )
        self.ui.label_4.setText("Total running time: %31s " % m4 )
        
class stats:
    def __init__(self, lastChecked):
        self.experimentsRun = 0
        self.stimuliDisplayed = 0
        self.installDate = datetime.datetime.now()
        self.totalRunTime = datetime.timedelta(0)
        self.lastChecked = lastChecked
        
    def refresh(self):
        self.totalRunTime += (datetime.datetime.now() - self.lastChecked)
        self.lastChecked = datetime.datetime.now()
        
    def save(self):
        self.refresh() 
        statsfile = open('stats.cfg', 'w')
        pickle.dump(self, statsfile)
        statsfile.close()
        
class attributeEditor(QDialog):
    def __init__(self, type, parent=None):
        QWidget.__init__(self,parent)
        self.ui = gui.attributeEditorUi()
        self.ui.setupUi(self)
        self.ui.attributeName.setFocus()
        
        self.parent = parent
        self.type = type
        self.setWindowTitle("Add "+type+" attribute")
                
        # connect buttons
        QObject.connect(self.ui.buttonBox, SIGNAL("accepted()"), self.submitAttr)
        QObject.connect(self.ui.attributesText, SIGNAL("textChanged()"), self.changed)
        # cancel just closes the dialog, no connect needed
            
    # button methods

    ### catch enter
    def changed(self):
        txt = self.ui.attributesText.toPlainText()
        if ('\r' in txt) or ('\n' in txt):
                self.submitAttr()
                self.parent.refreshAttributes()
                self.close()
    
    def submitAttr(self):
        name = self.ui.attributeName.text()
        name = name.simplified().replace(' ','_')  
        values = self.ui.attributesText.toPlainText()
        values = values.replace(",",";")
        values = list(values.split(";"))        
        for i in range(len(values)):                    
            values[i] = values[i].simplified().replace(' ','_')                                
        
        if self.type == 'stimulus':
                self.parent.settings.stimulusAttributes.append((name,values))
        if self.type == 'subject':
                self.parent.settings.subjectAttributes.append((name,values))
        
        self.parent.refreshEntities()
        self.parent.refreshAttributes()

# add subject or stimulus, with attribute values
class entityAdder(QDialog):
        def __init__(self, type, parent=None):
            QWidget.__init__(self,parent)
            self.ui = gui.entityAdderUi()
            self.ui.setupUi(self)
            # only show 'cancel' button until valid name has been given
            self.ui.buttonBox.setStandardButtons(\
                    QDialogButtonBox.Cancel|QDialogButtonBox.NoButton)                
            self.ui.formLayout.setHorizontalSpacing(120)
            self.ui.formLayout.setFieldGrowthPolicy(0)
            self.parent = parent
            self.type = type
            self.setWindowTitle("Add "+type)
            self.parent = parent  
            self.names = ['']              

            # dynamically add buttons depending on type and defined attributes
            if self.type == 'subject':
                self.attributes = parent.settings.subjectAttributes
                self.ui.openButton.hide()
                QObject.connect(self.ui.lineEdit, SIGNAL("returnPressed()"), self.submitSubject)
                QObject.connect(self.ui.lineEdit, SIGNAL("returnPressed()"), self.parent.refreshEntities)
            if self.type == 'stimulus':
                self.attributes = parent.settings.stimulusAttributes
                self.ui.label.hide()
                QObject.connect(self.ui.openButton, SIGNAL("clicked()"), self.selectStimulus)

            for (name,vals) in self.attributes:
                combobox = QComboBox(self)
                combobox.addItems(vals)
                combobox.setMinimumContentsLength(9)
                if name in self.parent.adderSettings:
                    i = combobox.findText(self.parent.adderSettings[name])
                    combobox.setCurrentIndex(i)
                self.ui.formLayout.addRow(name, combobox)

            # connect buttons
            QObject.connect(self.ui.lineEdit, SIGNAL("textChanged(QString)"), self.enableOK)
            QObject.connect(self.ui.buttonBox, SIGNAL("accepted()"), self.submitEntity)
            QObject.connect(self.ui.buttonBox, SIGNAL("accepted()"), self.parent.refreshEntities)
            
        # button methods
        def selectStimulus(self):
            # start in last folder or on user's desktop
            user = getpass.getuser()
            folder = os.path.expanduser('~'+user+'\Desktop')
            if self.parent.lastOpenFolder != '':
                folder = self.parent.lastOpenFolder
            
            types = "Media files ( *.png *.gif *.jpg *.bmp *.jpeg " +\
                slideshow.movietypes +' '+\
                slideshow.audiotypes
            #self.OK = False
            filenames = QFileDialog.getOpenFileNames(self, 'Select file',folder,types)
            f = filenames
            if filenames.count() >= 1:
                self.parent.lastOpenFolder = QString(os.path.dirname(str(filenames[0])))
                self.names = filenames
            if filenames.count() == 1:
                f = filenames   
                self.ui.lineEdit.setText(f[0]) # TODO: fix 
            if filenames.count() > 1:
                f = str(len(filenames)) + ' files selected'
                self.ui.lineEdit.setText(f)                             
                
        def enableOK(self,text):
            if (os.path.exists(self.names[0])) or (self.type == 'subject'):
                self.ui.buttonBox.setStandardButtons(\
                            QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
            if (self.type == 'stimulus') and not self.names == []:
                if not os.path.exists(self.names[0]):
                    self.ui.buttonBox.setStandardButtons(\
                            QDialogButtonBox.Cancel|QDialogButtonBox.NoButton)

        def submitSubject(self):
            # called if enter pressed in lineEdit        
            self.names = [self.ui.lineEdit.text()]
            self.submitEntity()
            self.close()

        def submitEntity(self): 

            if self.names == [''] and self.type == 'subject':
                self.names = [self.ui.lineEdit.text()]                
            for name in self.names:  
                name = str(name).strip()             
                e = entity(name, self.type)

                n = self.ui.formLayout.rowCount()
                for i in range(n):
                    item = self.ui.formLayout.itemAt(i,1).widget()
                    if item.__class__ == QComboBox:
                        attr = self.ui.formLayout.itemAt(i,0).widget().text()
                        value = item.currentText()
                        e.addAttribute(attr,value)
                        self.parent.adderSettings[attr] = value
                    elif item.__class__ == QTextEdit:
                        text = item.toPlainText()
                        e.addAttribute("Instruction", text)
                    else:
                        pass # ignore QLabels
                                
                if self.type == 'stimulus':
                    self.parent.settings.stimuli.append(e)
                if self.type == 'subject':
                    self.parent.settings.subjects.append(e)
            
            if len(self.names) == 1:        
                self.parent.statusBar().showMessage(self.type.capitalize()+" added!", 2000)
            else:
                self.parent.statusBar().showMessage(str(len(self.names))+\
                                                    " stimuli added!", 2000)

# describes a stimulus or subject, with a set of attributes
class entity:
        def __init__(self,name,type):
            self.name = name
            self.type = type
            self.attributes = [] # list of attribute/value tuples
            self.data = ''       # location of recording file

        def addAttribute(self,attr,val):
            self.attributes.append((attr,val))
                
        def getAttributes(self):
            return self.attributes         
        
# main loop
if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setApplicationName("Experiment Wizard")
    myapp = ExperimentWizard(app)
    myapp.show()
    sys.exit(app.exec_())
