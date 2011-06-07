python %HOMEPATH%\desktop\progging\pyinstaller-1.5-rc1\Makespec.py -F --icon=src\images\icon_brain64.ico src\experimentWizard.py

python %HOMEPATH%\desktop\progging\pyinstaller-1.5-rc1\Build.py experimentWizard.spec
copy src\edk.dll dist
copy src\edk_utils.dll dist
mkdir src\images
copy src\images\*.* dist\images\

