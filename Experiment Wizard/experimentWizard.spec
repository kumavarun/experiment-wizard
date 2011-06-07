# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH,'support\\_mountzlib.py'), os.path.join(HOMEPATH,'support\\useUnicode.py'), 'src\\experimentWizard.py'],
             pathex=['C:\\Users\\Junuxx\\Eclipse workspace\\Experiment Wizard'])
pyz = PYZ(a.pure)
exe = EXE( pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', 'experimentWizard.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=True , icon='src\\images\\icon_brain64.ico')
