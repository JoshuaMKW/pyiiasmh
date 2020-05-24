#  PyiiASMH (pyiiasmh.py)
#  Copyright (c) 2011, 2012, Sean Power
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#      * Neither the names of the authors nor the
#        names of its contributors may be used to endorse or promote products
#        derived from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL SEAN POWER BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import signal
import logging
import pickle as cPickle

from PyQt5 import QtCore, QtWidgets, QtGui, sip

from pyiiasmh_cli import PyiiAsmhApp
import mainwindow_ui
import prefs_ui

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

class PyiiAsmhGui(PyiiAsmhApp):

    def __init__(self):
        super(PyiiAsmhGui, self).__init__()

        self.app = None
        self.ui = None
        self.uiprefs = None
        self.filename = None
        self.prefs = {"confirm": True, "loadlast": False,
                      "codetype": "RAW", "qtstyle": "Default"}
        self.default_qtstyle = None

    def convert(self, action):
        self.get_uivars(action)
        stbar = self.ui.statusBar()

        if action == "asm":
            self.geckocodes = self.assemble(self.opcodes, None, None)
            self.ui.geckocodesPTextEdit.setPlainText(self.geckocodes)
            try:
                int(self.geckocodes.replace("\n", "").replace(" ", ""), 16)
                stbar.showMessage("Assembled opcodes into gecko codes.", 3000)
            except ValueError:
                stbar.showMessage("Failed to assemble opcodes into gecko codes.", 3000)
        else:
            dsm_out = self.disassemble(self.geckocodes, None, None)
            self.opcodes = dsm_out[0]
            self.bapo = dsm_out[1][0]
            self.xor = dsm_out[1][1]
            self.chksum = dsm_out[1][2]
            self.codetype = dsm_out[1][3]

            self.ui.opcodesPTextEdit.setPlainText(self.opcodes)
            if self.bapo is not None:
                self.ui.bapoLineEdit.setText(self.bapo)
            if self.xor is not None:
                self.ui.xorLineEdit.setText(self.xor)
            if self.chksum is not None:
                self.ui.checksumLineEdit.setText(self.chksum)
            self.radio = {"C0": self.ui.c0Radio,
                          "C2D2": self.ui.c2d2Radio,
                          "F2F4": self.ui.f2f4Radio}
            self.radio.get(self.codetype, self.ui.rawRadio).setChecked(True)
            stbar.showMessage("Disassembled gecko codes into opcodes.", 3000)

    def get_uivars(self, action):
        if action == "dsm":
            self.geckocodes = str(self.ui.geckocodesPTextEdit.toPlainText())
        else:
            self.bapo = str(self.ui.bapoLineEdit.text())
            self.xor = str(self.ui.xorLineEdit.text())
            self.chksum = str(self.ui.checksumLineEdit.text())
            self.opcodes = str(self.ui.opcodesPTextEdit.toPlainText())+"\n"

            if self.ui.c0Radio.isChecked():
                self.codetype = "C0"
            elif self.ui.c2d2Radio.isChecked():
                self.codetype = "C2D2"
            elif self.ui.f2f4Radio.isChecked():
                self.codetype = "F2F4"
            else:
                self.codetype = None

            if self.bapo == "":
                if self.codetype not in ("C0", None):
                    self.bapo = "80000000"
                else:
                    self.bapo = None
            if self.xor == "":
                if self.codetype == "F2F4":
                    self.xor = "0000"
                else:
                    self.xor = None
            if self.chksum == "":
                if self.codetype == "F2F4":
                    self.chksum = "00"
                else:
                    self.chksum = None

    def confirm_prompt(self, title, text, inform_text, detailed_text=None):
        cp = QtWidgets.QMessageBox(self.app.activeWindow())
        cp.setWindowTitle(title)
        cp.setText(text)
        cp.setInformativeText(inform_text)

        if detailed_text is not None:
            cp.setDetailedText(detailed_text)

        cp.setIcon(QtWidgets.QMessageBox.Warning)
        cp.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        cp.setDefaultButton(QtWidgets.QMessageBox.No)

        return cp.exec_() == QtWidgets.QMessageBox.No

    def confirm_helper(self, action, reload_file=False):
        if self.prefs.get("confirm"):
            inform_text = "Unsaved data will be lost."

            if action.__name__ == "open_session":
                if reload_file:
                    title = "Reload"
                    text = "reload this session?"
                else:
                    title = "Open"
                    text = "open an existing session?"
                title += " Session"
                text = "Are you sure you want to " + text
            elif action.__name__ == "new_session":
                title = "New Session"
                text = "Are you sure you want to start a new session?"
            else:
                title = "Quit PyiiASMH"
                text = "Are you sure you want to quit?"

            if self.confirm_prompt(title, text, inform_text):
                return

        if action.__name__ == "open_session":
            action(reload_file)
        else:
            action()

    def show_dialog(self, dialog_type=None):
        if dialog_type == "aboutqt":
            QtWidgets.QMessageBox.aboutQt(self.app.activeWindow())
        elif dialog_type == "aboutpyiiasmh":
            ext = ""
            if sys.platform == "win32":
                ext += ".txt"

            desc = "PyiiASMH is a cross-platform WiiRd helper tool that "
            desc += "is designed to help users with making WiiRd ready ASM "
            desc += "codes. This application supports assembling powerpc "
            desc += "opcodes into WiiRd codes using any of the WiiRd ASM "
            desc += "codetypes (C0, C2/D2, and F2/F4), or you can assemble "
            desc += "them into raw hex. Disassembling of WiiRd codes or "
            desc += "raw hex into PPC assembly opcodes is also supported. "
            desc += "\n\n"
            desc += "Please see the readme (README"+ext+") for more details."
            desc += "\n\n"
            desc += "Copyright (c) 2009, 2010, 2011, 2012\n\n"
            desc += "Sean Power <hawkeye2777[at]gmail[dot]com> \n\n"
            desc += "All rights reserved."

            QtWidgets.QMessageBox.about(self.app.activeWindow(),
                                    "About PyiiASMH", desc)
        else:  # dialog_type == "preferences":
            self.uiprefs.show()

    def new_session(self):
        self.ui.bapoLineEdit.setText("")
        self.ui.xorLineEdit.setText("")
        self.ui.checksumLineEdit.setText("")
        self.ui.opcodesPTextEdit.setPlainText("")
        self.ui.geckocodesPTextEdit.setPlainText("")
        self.ui.actionSave.setEnabled(False)
        self.ui.actionReload.setEnabled(False)
        self.filename = None
        self.save_prefs()

        if self.prefs.get("codetype") == "C0":
            self.ui.c0Radio.setChecked(True)
        elif self.prefs.get("codetype") == "C2/D2":
            self.ui.c2d2Radio.setChecked(True)
        elif self.prefs.get("codetype") == "F2/F4":
            self.ui.f2f4Radio.setChecked(True)
        else:
            self.ui.rawRadio.setChecked(True)

        self.ui.setWindowTitle("PyiiASMH - untitled")
        self.ui.statusBar().showMessage("New session started.", 3000)

    def open_session(self, reload_file=False):
        if not reload_file:
            if self.filename is None:  # Just start in the home directory
                fname = str(QtWidgets.QFileDialog.getOpenFileName(self.ui,
                                                              "Open Session", os.path.expanduser(
                                                                  "~"),
                                                              "PyiiASMH session files (*.psav);;All files (*)")[0])
            else:  # Start in the last directory used by the user
                fname = str(QtWidgets.QFileDialog.getOpenFileName(self.ui,
                                                              "Open Session", os.path.split(
                                                                  self.filename)[0],
                                                              "PyiiASMH session files (*.psav);;All files (*)")[0])

            if fname == "":  # Make sure we have something to open
                return
            else:
                self.filename = fname

        try:
            f = open(self.filename, "rb")
        except IOError as e:
            self.log.exception(e)
        else:
            try:
                data = cPickle.load(f)
            except cPickle.UnpicklingError as e:
                self.log.exception(e)
            else:
                self.ui.bapoLineEdit.setText(data.get("bapo"))
                self.ui.xorLineEdit.setText(data.get("xor"))
                self.ui.checksumLineEdit.setText(data.get("chksum"))
                self.ui.opcodesPTextEdit.setPlainText(data.get("opcodes"))
                self.ui.geckocodesPTextEdit.setPlainText(
                    data.get("geckocodes"))
                self.ui.actionSave.setEnabled(True)
                self.ui.actionReload.setEnabled(True)

                if data.get("codetype") == "C0":
                    self.ui.c0Radio.setChecked(True)
                elif data.get("codetype") == "C2/D2":
                    self.ui.c2d2Radio.setChecked(True)
                elif data.get("codetype") == "F2/F4":
                    self.ui.f2f4Radio.setChecked(True)
                else:
                    self.ui.rawRadio.setChecked(True)

                self.save_prefs()
                self.ui.setWindowTitle("PyiiASMH - " +
                                       os.path.split(self.filename)[1])
                self.ui.statusBar().showMessage("Loaded session '" +
                                                os.path.split(self.filename)[1] + "'.", 3000)
            finally:
                f.close()

    def save_session(self, save_as=True):
        if save_as:
            if self.filename is None:  # Just start in the home directory
                fname = str(QtWidgets.QFileDialog.getSaveFileName(self.ui,
                                                              "Save Session", os.path.expanduser(
                                                                  "~"),
                                                              "PyiiASMH session files (*.psav);;All files (*)")[0])
            else:  # Start in the last directory used by the user
                fname = str(QtWidgets.QFileDialog.getSaveFileName(self.ui,
                                                              "Save Session", os.path.split(
                                                                  self.filename)[0],
                                                              "PyiiASMH session files (*.psav);;All files (*)")[0])

            if fname == "":  # Make sure we have something to open
                return
            else:
                self.filename = fname

        try:
            f = open(self.filename, "wb")
        except IOError as e:
            self.log.exception(e)
        else:
            data = {}
            data["bapo"] = str(self.ui.bapoLineEdit.text())
            data["xor"] = str(self.ui.xorLineEdit.text())
            data["chksum"] = str(self.ui.checksumLineEdit.text())
            data["opcodes"] = str(self.ui.opcodesPTextEdit.toPlainText())+"\n"
            data["geckocodes"] = str(self.ui.geckocodesPTextEdit.toPlainText())

            if self.ui.c0Radio.isChecked():
                data["codetype"] = "C0"
            elif self.ui.c2d2Radio.isChecked():
                data["codetype"] = "C2/D2"
            elif self.ui.f2f4Radio.isChecked():
                data["codetype"] = "F2/F4"
            else:
                data["codetype"] = "RAW"

            cPickle.dump(data, f, 2)
            self.ui.actionSave.setEnabled(True)
            self.ui.actionReload.setEnabled(True)

            self.save_prefs()
            self.ui.setWindowTitle("PyiiASMH - " +
                                   os.path.split(self.filename)[1])
            self.ui.statusBar().showMessage("Saved session '" +
                                            os.path.split(self.filename)[1] + "'.", 3000)
            f.close()

    def load_prefs(self):
        try:
            f = open(".last.psav", "rb")
        except IOError:
            self.log.warning("No last session found.")
        else:
            try:
                filename = cPickle.load(f)
            except cPickle.UnpicklingError as e:
                self.log.exception(e)
            else:
                if filename is not None:
                    self.filename = filename
            finally:
                f.close()
        try:
            f = open(".PyiiASMH.conf", "rb")
        except IOError:
            self.log.warning("No preferences file found; using defaults.")
        else:
            try:
                p = cPickle.load(f)
            except cPickle.UnpicklingError as e:
                self.log.exception(e)  # Use defaults for prefs
            else:
                # Input validation
                if p.get("confirm") in (True, False):
                    self.prefs["confirm"] = p.get("confirm")

                if p.get("loadlast") in (True, False):
                    self.prefs["loadlast"] = p.get("loadlast")

                if p.get("codetype") in ("C0", "C2/D2", "F2/F4", "RAW"):
                    self.prefs["codetype"] = p.get("codetype")

                    if p.get("codetype") == "C0":
                        self.ui.c0Radio.setChecked(True)
                    if p.get("codetype") == "C2/D2":
                        self.ui.c2d2Radio.setChecked(True)
                    if p.get("codetype") == "F2/F4":
                        self.ui.f2f4Radio.setChecked(True)

                if (p.get("qtstyle") in list(QtWidgets.QStyleFactory.keys()) or
                        p.get("qtstyle") == "Default"):
                    self.prefs["qtstyle"] = p.get("qtstyle")

                setCIndex = self.uiprefs.qtstyleSelect.setCurrentIndex

                if self.prefs.get("qtstyle") in (None, "Default"):
                    setCIndex(0)
                else:
                    setCIndex(self.uiprefs.qtstyleSelect.findText(
                        self.prefs.get("qtstyle"),
                        flags=QtCore.Qt.MatchFixedString))

                setCIndex = self.uiprefs.codetypeSelect.setCurrentIndex
                setCIndex(self.uiprefs.codetypeSelect.findText(
                    self.prefs.get("codetype"),
                    flags=QtCore.Qt.MatchFixedString))

                self.ui.set_close_event(self.prefs.get("confirm"))
                self.uiprefs.confirmation.setChecked(self.prefs.get("confirm"))
                self.uiprefs.loadLast.setChecked(self.prefs.get("loadlast"))
            finally:
                f.close()

    def save_prefs(self):
        self.prefs["confirm"] = self.uiprefs.confirmation.isChecked()
        self.prefs["loadlast"] = self.uiprefs.loadLast.isChecked()
        self.prefs["codetype"] = str(self.uiprefs.codetypeSelect.currentText())
        self.prefs["qtstyle"] = str(self.uiprefs.qtstyleSelect.currentText())
        self.ui.set_close_event(self.prefs.get("confirm"))

        try:
            f = open(".PyiiASMH.conf", "wb")
        except IOError as e:
            self.log.exception(e)
        else:
            cPickle.dump(self.prefs, f, 2)
            f.close()
        try:
            f = open(".last.psav", "wb")
        except IOError as e:
            self.log.exception(e)
        else:
            cPickle.dump(self.filename, f, 2)
            f.close()

    def load_qtstyle(self, style, first_style_load=False):
        if style != "Default":
            self.app.setStyle(style)
        else:
            self.app.setStyle(self.default_qtstyle)

        if first_style_load:
            setCIndex = self.uiprefs.qtstyleSelect.setCurrentIndex
            setCIndex(self.uiprefs.qtstyleSelect.findText(style,
                                                          flags=QtCore.Qt.MatchFixedString))

    def connect_signals(self):
        self.ui.asmButton.clicked.connect(lambda: self.convert("asm"))
        self.ui.dsmButton.clicked.connect(lambda: self.convert("dsm"))

        self.ui.actionQuit.triggered.connect(
            lambda: self.confirm_helper(self.ui.close))
        self.ui.actionPreferences.triggered.connect(self.show_dialog)
        self.ui.actionAbout_Qt.triggered.connect(
            lambda: self.show_dialog("aboutqt"))
        self.ui.actionAbout_PyiiASMH.triggered.connect(
            lambda: self.show_dialog("aboutpyiiasmh"))

        self.ui.actionNew.triggered.connect(
            lambda: self.confirm_helper(self.new_session))
        self.ui.actionOpen.triggered.connect(
            lambda: self.confirm_helper(self.open_session))
        self.ui.actionSave_As.triggered.connect(self.save_session)
        self.ui.actionReload.triggered.connect(
            lambda: self.confirm_helper(self.open_session, True))
        self.ui.actionSave.triggered.connect(
            lambda: self.save_session(False))

        self.uiprefs.buttonBox.accepted.connect(self.save_prefs)
        self.uiprefs.qtstyleSelect.currentIndexChanged.connect(lambda: self.load_qtstyle(
                                                                self.uiprefs.qtstyleSelect.currentText()))

    def run(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.default_qtstyle = self.app.style().objectName()
        self.ui = mainwindow_ui.MainWindowUi()  # uic.loadUi("mainwindow.ui")
        self.uiprefs = prefs_ui.PrefsUi()  # uic.loadUi("prefs.ui")

        self.uiprefs.qtstyleSelect.addItem("Default")
        for i in range(0, len(list(QtWidgets.QStyleFactory.keys()))):
            self.uiprefs.qtstyleSelect.addItem(
                list(QtWidgets.QStyleFactory.keys())[i])
        self.load_prefs()
        self.load_qtstyle(self.prefs.get("qtstyle"), True)
        self.ui.opcodesPTextEdit.setFocus()

        regex = QtCore.QRegExp("[0-9A-Fa-f]*")
        validator = QtGui.QRegExpValidator(regex)
        self.ui.bapoLineEdit.setValidator(validator)
        self.ui.xorLineEdit.setValidator(validator)
        self.ui.checksumLineEdit.setValidator(validator)

        if self.filename is not None and self.prefs.get("loadlast"):
            self.open_session(self.filename)

        self.connect_signals()
        self.ui.show()
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    app = PyiiAsmhGui()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run()
