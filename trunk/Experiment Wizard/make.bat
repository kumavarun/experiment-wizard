python "C:\Program Files\pyinstaller-1.5.1\Makespec.py" -F --icon=src\images\icon_brain64.ico src\experimentWizard.py

python "C:\Program Files\pyinstaller-1.5.1\Build.py" experimentWizard.spec
copy src\edk.dll dist
copy src\edk_utils.dll dist
mkdir dist\images
copy src\images\*.* dist\images\

