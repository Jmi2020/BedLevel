# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

datas = []
hiddenimports = ['tkinter', 'tkinter._fix', 'matplotlib.backends.backend_tkagg', 'matplotlib.backends._tkagg', 'mpl_toolkits.mplot3d']
datas += collect_data_files('matplotlib')
datas += collect_data_files('mpl_toolkits')
datas += collect_data_files('matplotlib')
hiddenimports += collect_submodules('matplotlib')
hiddenimports += collect_submodules('mpl_toolkits')


a = Analysis(
    ['bed_level_editor_pro.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Bed Level Editor Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Bed Level Editor Pro',
)
app = BUNDLE(
    coll,
    name='Bed Level Editor Pro.app',
    icon=None,
    bundle_identifier='com.bedlevel.editorpro',
)
