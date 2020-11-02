import sys
from cx_Freeze import setup, Executable

include_files = [ "PyiiASMH.ico",
                  "__includes.s",
                  "lib/" ]

excludes = [ "tkinter" ]

options = {
    "build_exe": {
        "optimize": 4,
        "excludes": excludes,
        "include_files": include_files
    }
}
  
setup(name = "PyiiASMH 3", 
      version = "4.1.0", 
      description = "A cross platform gecko code compiler for PowerPC assembly", 
      executables = [Executable("pyiiasmh.py", icon="PyiiASMH.ico")],
      author = "JoshuaMK",
      author_email = "joshuamkw2002@gmail.com",
      options = options
      )