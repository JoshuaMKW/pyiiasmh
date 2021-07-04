import subprocess
import sys

if sys.platform == "win32":
    subprocess.Popen('pyinstaller --noconfirm --onefile --console --icon "PyiiASMH.ico" --name "PyiiASMH" --clean --add-data "__includes.s;." --add-data "PyiiASMH.ico;." --add-data "lib;lib/" "pyiiasmh.py"', shell=True)
else:
    subprocess.Popen('pyinstaller --noconfirm --onefile --console --icon "PyiiASMH.ico" --name "PyiiASMH" --clean --add-data "__includes.s:." --add-data "PyiiASMH.ico:." --add-data "lib:lib/" "pyiiasmh.py"', shell=True)
