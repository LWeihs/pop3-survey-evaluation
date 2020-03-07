# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files

added_files = collect_data_files('pyphen')
extra_imports = ['pkg_resources.py2_warn', 'pyphen']

a = Analysis(['survey_evaluation.py'],
             pathex=['C:\\Users\\Lennart Weihs\\Documents\\GitHub\\pop3-survey-evaluation'],
             binaries=[],
             datas=added_files,
             hiddenimports=extra_imports,
             hookspath=None,
             runtime_hooks=None,
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [('W ignore', None, 'OPTION')],
          name='survey_evaluation',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True)
