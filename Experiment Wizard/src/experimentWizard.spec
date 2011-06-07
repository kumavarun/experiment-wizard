# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'), os.path.join(HOMEPATH,'support\\useUnicode.py'), 'experimentWizard.py'],
             pathex=['C:\\Users\\Junuxx\\Eclipse workspace\\Experiment Wizard\\src'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build\\pyi.win32\\experimentWizard', 'experimentWizard.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='icon_brain64.ico')
coll = COLLECT( exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name=os.path.join('dist', 'experimentWizard'))
app = BUNDLE(coll,
             name=os.path.join('dist', 'experimentWizard.app'))
