# -*- coding: utf-8 -*-
#
#  PyiiASMH 3 (prefs_ui.py)
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


from PyQt5 import QtCore, QtWidgets, QtGui

class PrefsUi(QtWidgets.QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.setupUi()

    def setupUi(self):
        self.setObjectName("Dialog")
        self.resize(300, 234)
        self.setMinimumSize(QtCore.QSize(300, 234))
        self.setBaseSize(QtCore.QSize(300, 234))
        self.setMaximumSize(QtCore.QSize(300, 234))
        self.setModal(True)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("PyiiASMH.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setGeometry(QtCore.QRect(10, 194, 281, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.formLayoutWidget = QtWidgets.QWidget(self)
        self.formLayoutWidget.setGeometry(QtCore.QRect(10, 10, 271, 121))
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.checkBoxLayout = QtWidgets.QGridLayout(self.formLayoutWidget)
        self.checkBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.checkBoxLayout.setVerticalSpacing(0)
        self.checkBoxLayout.setObjectName("checkBoxLayout")

        #confirmation
        self.confirmation = QtWidgets.QCheckBox(self.formLayoutWidget)
        self.confirmation.setChecked(True)
        self.confirmation.setObjectName("confirmation")
        self.checkBoxLayout.addWidget(self.confirmation, 0, 0, 1, 1)

        #loadLast
        self.loadLast = QtWidgets.QCheckBox(self.formLayoutWidget)
        self.loadLast.setObjectName("loadLast")
        self.checkBoxLayout.addWidget(self.loadLast, 1, 0, 1, 1)

        #autodecorate
        self.autodecorate = QtWidgets.QCheckBox(self.formLayoutWidget)
        self.autodecorate.setChecked(True)
        self.autodecorate.setObjectName("autodecorate")
        self.checkBoxLayout.addWidget(self.autodecorate, 2, 0, 1, 1)

        #formalnaming
        self.formalnaming = QtWidgets.QCheckBox(self.formLayoutWidget)
        self.formalnaming.setObjectName("formalnaming")
        self.checkBoxLayout.addWidget(self.formalnaming, 3, 0, 1, 1)

        self.gridLayoutWidget = QtWidgets.QWidget(self)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 130, 271, 58))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.comboBoxLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.comboBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.comboBoxLayout.setVerticalSpacing(10)
        self.comboBoxLayout.setObjectName("comboBoxLayout")

        #codetype box
        self.codetypeSelect = QtWidgets.QComboBox(self.gridLayoutWidget)
        self.codetypeSelect.setObjectName("codetypeSelect")
        self.codetypeSelect.addItems(["", "", "", "", "", ""])
        self.comboBoxLayout.addWidget(self.codetypeSelect, 0, 1, 1, 1)

        #codetype label
        self.codetypeLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.codetypeLabel.setObjectName("codetypeLabel")
        self.comboBoxLayout.addWidget(self.codetypeLabel, 0, 0, 1, 1)

        #qtstyle box
        self.qtstyleSelect = QtWidgets.QComboBox(self.gridLayoutWidget)
        self.qtstyleSelect.setObjectName("qtstyleSelect")
        self.comboBoxLayout.addWidget(self.qtstyleSelect, 1, 1, 1, 1)

        #qtstyle label
        self.qtstyleLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.qtstyleLabel.setObjectName("qtstyleLabel")
        self.comboBoxLayout.addWidget(self.qtstyleLabel, 1, 0, 1, 1)

        self.retranslateUi()
        self.codetypeSelect.setCurrentIndex(5)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateUi(self):
        self.setWindowTitle(QtWidgets.QApplication.translate("Dialog", "Preferences", None))
        self.loadLast.setText(QtWidgets.QApplication.translate("Dialog", "Load last session on startup", None))
        self.confirmation.setToolTip(QtWidgets.QApplication.translate("Dialog", "Show confirmation dialogs for starting a new session, saving, reloading, or exiting the application.", None))
        self.confirmation.setText(QtWidgets.QApplication.translate("Dialog", "Confirmation Dialogs", None))
        self.autodecorate.setText(QtWidgets.QApplication.translate("Dialog", "Use C0 end block", None))
        self.formalnaming.setText(QtWidgets.QApplication.translate("Dialog", "Use \"sp\" and \"rtoc\"", None))
        self.codetypeSelect.setItemText(0, QtWidgets.QApplication.translate("Dialog", "C0", None))
        self.codetypeSelect.setItemText(1, QtWidgets.QApplication.translate("Dialog", "04/14", None))
        self.codetypeSelect.setItemText(2, QtWidgets.QApplication.translate("Dialog", "06/16", None))
        self.codetypeSelect.setItemText(3, QtWidgets.QApplication.translate("Dialog", "C2/D2", None))
        self.codetypeSelect.setItemText(4, QtWidgets.QApplication.translate("Dialog", "F2/F4", None))
        self.codetypeSelect.setItemText(5, QtWidgets.QApplication.translate("Dialog", "RAW", None))
        self.codetypeLabel.setText(QtWidgets.QApplication.translate("Dialog", "Default Codetype:", None))
        self.qtstyleLabel.setText(QtWidgets.QApplication.translate("Dialog", "GUI Style:", None))

class BuiltinsDocUI(QtWidgets.QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.init_docs()
        self.setupUi()

    def setupUi(self):
        self.setObjectName("Dialog")
        self.resize(700, 400)
        self.setMinimumSize(QtCore.QSize(700, 400))
        self.setBaseSize(QtCore.QSize(700, 400))
        self.setMaximumSize(QtCore.QSize(700, 400))
        self.setModal(True)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("PyiiASMH.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)

        self.objtypebar = QtWidgets.QPlainTextEdit(self)
        self.objtypebar.setMinimumSize(QtCore.QSize(400, 32))
        self.objtypebar.setMaximumSize(QtCore.QSize(16777215, 32))
        font = QtGui.QFont()
        font.setFamily("Consolas")
        font.setPointSize(13)
        font.setWeight(34)
        fontMetrics = QtGui.QFontMetricsF(font)
        spaceWidth = fontMetrics.width(' ')
        self.objtypebar.setFont(font)
        self.objtypebar.setTabStopDistance(spaceWidth * 4)
        self.objtypebar.setReadOnly(True)
        self.objtypebar.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.objtypebar.setBackgroundVisible(False)
        self.objtypebar.setObjectName("docuTextBox")

        self.objtypebar.setPlainText("")

        self.gridLayoutWidget = QtWidgets.QGridLayout(self)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 60, 400, 70))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")

        self.funcSelect = QtWidgets.QListWidget(self)
        self.funcSelect.setMinimumSize(QtCore.QSize(200, 200))
        self.funcSelect.setMaximumSize(QtCore.QSize(200, 16777215))
        self.funcSelect.setObjectName("funcSelect")

        for item in self.docs:
            self.funcSelect.addItem(item[0])

        self.docuTextBox = QtWidgets.QPlainTextEdit(self)
        self.docuTextBox.setMinimumSize(QtCore.QSize(400, 300))
        self.docuTextBox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setFamily("Consolas")
        font.setPointSize(10)
        font.setWeight(34)
        fontMetrics = QtGui.QFontMetricsF(font)
        spaceWidth = fontMetrics.width(' ')
        self.docuTextBox.setFont(font)
        self.docuTextBox.setTabStopDistance(spaceWidth * 4)
        self.docuTextBox.setReadOnly(True)
        self.docuTextBox.setBackgroundVisible(False)
        self.docuTextBox.setObjectName("docuTextBox")

        self.docuTextBox.setPlainText("")

        self.gridLayoutWidget.addWidget(self.funcSelect, 0, 0, 2, 1)
        self.gridLayoutWidget.addWidget(self.objtypebar, 0, 1, 1, 1)
        self.gridLayoutWidget.addWidget(self.docuTextBox, 1, 1, 1, 1)

        self.setWindowTitle(QtWidgets.QApplication.translate("Dialog", "Builtins Documentation", None))

        QtCore.QMetaObject.connectSlotsByName(self)

    def init_docs(self):
        self.docs = []
        _names = []
        _docs = []
        _types = []

        with open("__includes.a", "r") as builtins:
            commentready = False
            _documentation = ""
            for line in builtins.readlines():
                line.strip()
                if line == "":
                    continue
                elif line.startswith("#") and commentready:
                    _documentation += line[1:].strip() + "\n"
                    continue
                elif commentready:
                    _docs.append(_documentation)
                    commentready = False
                    _documentation = ""
                    continue

                segments = line.split(" ")
                if segments[0] == ".set":
                    _types.append("const")
                elif segments[0] == ".macro":
                    _types.append("macro")
                else:
                    commentready = False
                    continue
                
                commentready = True
                _names.append(segments[1].strip().rstrip(","))

        for i in range(len(_names)):
            self.docs.append((_names[i], _docs[i], _types[i]))

    def update_info(self):
        self.objtypebar.setPlainText(self.docs[self.funcSelect.currentRow()][2].center(51, " ").upper())
        self.docuTextBox.setPlainText(self.docs[self.funcSelect.currentRow()][1])


        