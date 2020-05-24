# -*- coding: utf-8 -*-
#
#  PyiiASMH (prefs_ui.py)
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


from PyQt5 import QtCore, QtWidgets

class PrefsUi(QtWidgets.QDialog):
    def __init__(self):
        super(PrefsUi, self).__init__()

        self.setupUi()

    def setupUi(self):
        self.setObjectName("Dialog")
        self.resize(300, 190)
        self.setMinimumSize(QtCore.QSize(300, 190))
        self.setBaseSize(QtCore.QSize(300, 190))
        self.setModal(True)
        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setGeometry(QtCore.QRect(10, 150, 281, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.formLayoutWidget = QtWidgets.QWidget(self)
        self.formLayoutWidget.setGeometry(QtCore.QRect(10, 10, 271, 61))
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.checkBoxLayout = QtWidgets.QGridLayout(self.formLayoutWidget)
        self.checkBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.checkBoxLayout.setVerticalSpacing(10)
        self.checkBoxLayout.setObjectName("checkBoxLayout")
        self.loadLast = QtWidgets.QCheckBox(self.formLayoutWidget)
        self.loadLast.setObjectName("loadLast")
        self.checkBoxLayout.addWidget(self.loadLast, 1, 0, 1, 1)
        self.confirmation = QtWidgets.QCheckBox(self.formLayoutWidget)
        self.confirmation.setChecked(True)
        self.confirmation.setObjectName("confirmation")
        self.checkBoxLayout.addWidget(self.confirmation, 0, 0, 1, 1)
        self.gridLayoutWidget = QtWidgets.QWidget(self)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 80, 271, 58))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.comboBoxLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.comboBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.comboBoxLayout.setVerticalSpacing(10)
        self.comboBoxLayout.setObjectName("comboBoxLayout")
        self.codetypeSelect = QtWidgets.QComboBox(self.gridLayoutWidget)
        self.codetypeSelect.setObjectName("codetypeSelect")
        self.codetypeSelect.addItem("")
        self.codetypeSelect.addItem("")
        self.codetypeSelect.addItem("")
        self.codetypeSelect.addItem("")
        self.comboBoxLayout.addWidget(self.codetypeSelect, 0, 1, 1, 1)
        self.codetypeLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.codetypeLabel.setObjectName("codetypeLabel")
        self.comboBoxLayout.addWidget(self.codetypeLabel, 0, 0, 1, 1)
        self.qtstyleSelect = QtWidgets.QComboBox(self.gridLayoutWidget)
        self.qtstyleSelect.setObjectName("qtstyleSelect")
        self.comboBoxLayout.addWidget(self.qtstyleSelect, 1, 1, 1, 1)
        self.qtstyleLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.qtstyleLabel.setObjectName("qtstyleLabel")
        self.comboBoxLayout.addWidget(self.qtstyleLabel, 1, 0, 1, 1)

        self.retranslateUi()
        self.codetypeSelect.setCurrentIndex(3)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateUi(self):
        self.setWindowTitle(QtWidgets.QApplication.translate("Dialog", "Preferences", None))
        self.loadLast.setText(QtWidgets.QApplication.translate("Dialog", "Load last session on startup", None))
        self.confirmation.setToolTip(QtWidgets.QApplication.translate("Dialog", "Show confirmation dialogs for starting a new session, saving, reloading, or exiting the application.", None))
        self.confirmation.setText(QtWidgets.QApplication.translate("Dialog", "Confirmation Dialogs", None))
        self.codetypeSelect.setItemText(0, QtWidgets.QApplication.translate("Dialog", "C0", None))
        self.codetypeSelect.setItemText(1, QtWidgets.QApplication.translate("Dialog", "C2/D2", None))
        self.codetypeSelect.setItemText(2, QtWidgets.QApplication.translate("Dialog", "F2/F4", None))
        self.codetypeSelect.setItemText(3, QtWidgets.QApplication.translate("Dialog", "RAW", None))
        self.codetypeLabel.setText(QtWidgets.QApplication.translate("Dialog", "Default Codetype:", None))
        self.qtstyleLabel.setText(QtWidgets.QApplication.translate("Dialog", "GUI Style:", None))

