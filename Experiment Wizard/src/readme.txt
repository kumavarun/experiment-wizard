                           ********
                    Beta Lab Experiment Wizard 
                            README
                           ********
        
Experiment Wizard is a tool that allows users to design and perform 
stimulus-response experiments on human subjects. It can present image,
video and audio stimuli and record both keystrokes and brain activity.
The program is specially designed to cooperate with the Emotiv EPOC,
a 14 sensor EEG device.

Experiment Wizard was developed for the Amsterdam University College in 
2010-2011 for a course on Information, Communication and Cognition. In 
this course, freshman students perform their own EEG experiments using 
Emotiv equipment and this program. For more info, see www.beta-lab.nl
        
******** I. Installation instructions ********

1. Download from http://code.google.com/p/experiment-wizard
   You can either download the most recent binary (i.e. a compiled exe,
   from the "Download" tab) or the source code (under "Source"). Unless
   you know what you're doing it is advisable to download the binary.
   
2. To run Experiment Wizard from source, the following applications 
   need to be installed. Skip this step if you have the binary.
    * Python 2.6 or 2.7
    * PyQt 4.7 or 4.8
    * NumPy

3. In addition, to use the EEG recording features, make sure that the
   files edk.dll and edk_utils.dll from the Emotiv Development Kit are
   copied into the Experiment Wizard folder.
   
4. Start by running experimentWizard.exe (binary) /
                    experimentWizard.py  (source)

************ II. Compatibility ***************

Only designed for and tested on Windows XP/Vista/7 computers.

*************** III. License *****************

The binaries and source are released under GNU GPL 3.
In brief, this means that every user has the freedom to
* use the software for any purpose,
* change the software to suit their needs,
* share the software with their friends and neighbors
* share the changes they make

Note that the Emotiv(c) DLLs and any other Emotiv content used by this
program is explicitly excepted from this license.

Finally, the original author would like to request that if you use this
software for education or research, please cite the following:

- http://www.beta-lab.nl                            (the lab course)
- http://code.google.com/p/experiment-wizard        (the program)


Jeroen Kools
April 28 2011