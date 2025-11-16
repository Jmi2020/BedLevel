"""
py2app build script for packaging bed_level_editor_pro.py as a macOS app.

Usage:
    python3 setup.py py2app

The generated .app bundle will be located in the dist/ directory.
"""
from setuptools import setup

APP = ['bed_level_editor_pro.py']
DATA_FILES = []

COMMON_PACKAGES = [
    "tkinter",
    "numpy",
    "matplotlib",
    "scipy",
    "cycler",
    "kiwisolver",
    "PIL",
    "dateutil",
    "pyparsing",
    "packaging",
    "six",
    "networkx",
    "trimesh",
]

OPTIONS = {
    "argv_emulation": True,
    "packages": COMMON_PACKAGES,
    "includes": [
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends._tkagg",
        "mpl_toolkits.mplot3d",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter._fix",
    ],
    "plist": {
        "CFBundleName": "Bed Level Editor Pro",
        "CFBundleDisplayName": "Bed Level Editor Pro",
        "CFBundleIdentifier": "com.bedlevel.editorpro",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
