#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import sys, os, random
from PyQt4 import QtGui, QtCore
from PyKDE4.kdeui import *
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from numpy import arange, sin, pi
from matplotlib.figure import Figure
import BREWERY

progname = os.path.basename(sys.argv[0])
progversion = "0.1"


class BrewFigureCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent=None, width=5, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        # We want the axes cleared every time plot() is called
        self.axes.hold(False)

        self.compute_initial_figure()

        #
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        #FigureCanvas.setSizePolicy(self,
        #                           QtGui.QSizePolicy.Expanding,
        #                           QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self):
        pass

class BrewDynamicCanvas(BrewFigureCanvas):
    """A canvas that updates itself every second with a new plot."""
    def __init__(self, *args, **kwargs):
        BrewFigureCanvas.__init__(self, *args, **kwargs)

    def compute_initial_figure(self):
         self.axes.plot([0, 1, 2, 3], [1, 2, 0, 4], 'r')

    def update_figure(self, xdata="", ydata=""):
        self.axes.plot(xdata, ydata, 'r')
        maxtime = xdata[len(xdata)-1]
        mintime = maxtime-20.0
        if mintime < 0.0:
		   mintime = 0.0
        self.axes.set_xlim([mintime, maxtime]) #need to figure out x limit
        self.draw()

class dataLabel(QtGui.QWidget):
    def __init__(self, parent=None, labeltext="Label Text:", unittext="", manualable=0, increaseaction="", decreaseaction=""):
        QtGui.QWidget.__init__(self)
        self.content = QtGui.QHBoxLayout(self)

        labelfont = QtGui.QFont()
        labelfont.setPointSize(10)
        
        self.textlabel = QtGui.QLabel(labeltext)
        self.datalabel = QtGui.QLabel(str(0.0))
        self.unitlabel = QtGui.QLabel(unittext)

        self.textlabel.setFont(labelfont)
        self.datalabel.setFont(labelfont)
        self.unitlabel.setFont(labelfont)
        
        self.content.addWidget(self.textlabel)
        self.content.addWidget(self.datalabel)
        self.content.addWidget(self.unitlabel)

        if manualable==1:
            self.adjustor = QtGui.QVBoxLayout()
            self.upadjustor = QtGui.QPushButton("",self)
            if (increaseaction != ""):
                self.upadjustor.clicked.connect(increaseaction)
            self.dnadjustor = QtGui.QPushButton("",self)
            if (decreaseaction != ""):
                self.dnadjustor.clicked.connect(decreaseaction)
            self.upadjustor.setIcon(KIcon('go-up'))
            self.dnadjustor.setIcon(KIcon('go-down'))
            self.upadjustor.setIconSize(QtCore.QSize(15,15))
            self.dnadjustor.setIconSize(QtCore.QSize(15,15))
            self.adjustor.addWidget(self.upadjustor)
            self.adjustor.addWidget(self.dnadjustor)
            self.content.addLayout(self.adjustor)
            
    def updateData(self, newvalue):
        self.datalabel.setText('{:03.2f}'.format(newvalue))
            

class BrewConnect_Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        #===MAIN PROPERTIES======================================================
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("BrewConnect")

        #===TOOL BAR=============================================================
        self.toolbar = self.addToolBar('Tools')

        exitAction = QtGui.QAction(KIcon('application-exit'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.fileQuit)        
        self.toolbar.addAction(exitAction)
        self.toolbar.setIconSize(QtCore.QSize(50,50))

        startAction = QtGui.QAction(KIcon('media-playback-start'), 'Start', self)
        startAction.triggered.connect(self.startControls)
        self.toolbar.addAction(startAction)
        self.toolbar.setIconSize(QtCore.QSize(50,50))

        stopAction = QtGui.QAction(KIcon('media-playback-stop'), 'Stop', self)
        stopAction.triggered.connect(self.stopControls)
        self.toolbar.addAction(stopAction)
        self.toolbar.setIconSize(QtCore.QSize(50,50))

        saveAction = QtGui.QAction(KIcon('document-save'), 'Save', self)
        saveAction.triggered.connect(self.fileQuit)
        self.toolbar.addAction(saveAction)
        self.toolbar.setIconSize(QtCore.QSize(50,50))

        settingsAction = QtGui.QAction(KIcon('preferences-system'), 'Settings', self)
        settingsAction.triggered.connect(self.fileQuit)
        self.toolbar.addAction(settingsAction)
        self.toolbar.setIconSize(QtCore.QSize(50,50))
        
        self.permissionAction = QtGui.QAction(KIcon('go-next'), 'Continue', self)
        self.permissionAction.triggered.connect(self.grantPermission)
        self.permissionAction.setDisabled(True)
        self.toolbar.addAction(self.permissionAction)
        self.toolbar.setIconSize(QtCore.QSize(50,50))



        #===MAIN LAYOUT==========================================================
        self.main_widget = QtGui.QWidget(self)

        self.precontent = QtGui.QVBoxLayout(self.main_widget)
        
        self.status  = QtGui.QHBoxLayout()
        self.content = QtGui.QHBoxLayout()

        self.graphs   = QtGui.QVBoxLayout()
        self.datavals = QtGui.QVBoxLayout()
        
        self.initstatustexts()
        statustext = self.statustexts[0]
        statusfont = QtGui.QFont()
        statusfont.setPointSize(10)
        self.statuslabel = QtGui.QLabel(statustext)
        self.statuslabel.setFont(statusfont)
        self.status.addWidget(self.statuslabel)
        
        self.boiltempchart = BrewDynamicCanvas(self.main_widget, width=5, height=2, dpi=100)
        self.mashtempchart = BrewDynamicCanvas(self.main_widget, width=5, height=2, dpi=100)
        self.graphs.addWidget(self.boiltempchart)
        self.graphs.addWidget(self.mashtempchart)

        self.boiltemp_act = dataLabel(labeltext="Boil Temp:", unittext="degF", manualable=0)
        self.boiltemp_set = dataLabel(labeltext="Boil SetPt:", unittext="degF", manualable=1, increaseaction=self.increase_B_TempSet, decreaseaction=self.decrease_B_TempSet)
        self.mashtemp_act = dataLabel(labeltext="Mash Temp:", unittext="degF", manualable=0)
        self.mashtemp_set = dataLabel(labeltext="Mash SetPt:", unittext="degF", manualable=1, increaseaction=self.increase_M_TempSet, decreaseaction=self.decrease_M_TempSet)
        self.controlstate = dataLabel(labeltext="CTRL State:", unittext="", manualable=1, increaseaction=self.increase_C_State, decreaseaction=self.decrease_C_State)
        self.timeleft_lab = dataLabel(labeltext="Time Left:",  unittext="min", manualable=0)
        self.datavals.addWidget(self.boiltemp_act)
        self.datavals.addWidget(self.boiltemp_set)
        self.datavals.addWidget(self.mashtemp_act)
        self.datavals.addWidget(self.mashtemp_set)
        self.datavals.addWidget(self.controlstate)
        self.datavals.addWidget(self.timeleft_lab)
        self.datavals.addStretch(1)

        self.content.addLayout(self.graphs)
        self.content.addLayout(self.datavals)

        self.precontent.addLayout(self.status)
        self.precontent.addLayout(self.content)
        
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self.statusBar().showMessage("Ready", 2000)

    def initstatustexts(self):
        self.statustexts = []
        self.statustexts.append("Stage 0: Waiting for HLT to be full of water.")
        self.statustexts.append("Stage 1: Heating water up for strike.")
        self.statustexts.append("Stage 2: Adding strike water to mash tun.")
        self.statustexts.append("Stage 3: Waiting for strike water temperature to recover.")
        self.statustexts.append("Stage 4: Mash recirculation process.")
        self.statustexts.append("Stage 5: Stepping up mash temperature to 170 for sparge.")
        self.statustexts.append("Stage 6: Circulating mash at high temp for mashout.")
        self.statustexts.append("Stage 7: Waiting for configuration for sparging.")
        self.statustexts.append("Stage 8: Sparging process.")
        self.statustexts.append("Stage 9: Waiting for reconfiguration for boil.")
        self.statustexts.append("Stage 10: Moving wort to boil kettle.")
        self.statustexts.append("Stage 11: Preboil. Heating wort to boil temp.")
        self.statustexts.append("Stage 12: Boil process.")
        self.statustexts.append("Stage 13: Cooling wort down to pitching temperature.")
        self.statustexts.append("Stage 14: Pumping wort out to fermentation bucket.")
        
    
    def startControls(self):
        #starting up controls sequencing
        BREWERY.setup()
        BREWERY.loop()
        self.CTRLtimer = QtCore.QTimer(self)
        QtCore.QObject.connect(self.CTRLtimer, QtCore.SIGNAL("timeout()"), self.CTRLloop)
        self.CTRLtimer.start(50)
        
        #start plot updating sequencing
        self.Plottimer = QtCore.QTimer(self)
        QtCore.QObject.connect(self.Plottimer, QtCore.SIGNAL("timeout()"), self.plotUpdate)
        self.Plottimer.start(30000)
        
        self.Datatimer = QtCore.QTimer(self)
        QtCore.QObject.connect(self.Datatimer, QtCore.SIGNAL("timeout()"), self.dataUpdate)
        self.Datatimer.start(1000)
        
        self.start_time = BREWERY.get_Tm1_BREWING_1_wtime()
        
        self.time_array = [0.0]
        self.B_TempFil_array = [BREWERY.get_Tm1_BREWING_1_B_TempFil()]
        self.M_TempFil_array = [BREWERY.get_Tm1_BREWING_1_M_TempFil()]
        
        self.requestpermission = 0
        
        reply = QtGui.QMessageBox.question(self, 'Message',
            "Starting up Brewing Operation.", QtGui.QMessageBox.Ok)

    def stopControls(self):
        #stopping controls
        BREWERY.stopControls()        
        self.CTRLtimer.stop()
        self.Plottimer.stop()
        self.Datatimer.stop()
        reply = QtGui.QMessageBox.question(self, 'Message',
            "Stopping Brewing Operation.", QtGui.QMessageBox.Ok)
        

    def saveData(self):
        #save measured data + log to log file
        reply = QtGui.QMessageBox.question(self, 'Message',
            "Save Data.", QtGui.QMessageBox.Ok)

    def changeSettings(self):
        #change control parameters
        reply = QtGui.QMessageBox.question(self, 'Message',
            "Change Parameters.", QtGui.QMessageBox.Ok)

    def fileQuit(self):
        self.close()

    def dataUpdate(self):
	   self.time_array.append((BREWERY.get_Tm1_BREWING_1_wtime() - self.start_time)/(1000.0*60.0))
	   self.B_TempFil_array.append(BREWERY.get_Tm1_BREWING_1_B_TempFil())
	   self.M_TempFil_array.append(BREWERY.get_Tm1_BREWING_1_M_TempFil())
	   
	   B_TempFil = BREWERY.get_Tm1_BREWING_1_B_TempFil()
	   B_TempSet = BREWERY.get_Tm1_BREWING_1_B_TempSet()
	   M_TempFil = BREWERY.get_Tm1_BREWING_1_M_TempFil()
	   M_TempSet = BREWERY.get_Tm1_BREWING_1_M_TempSet()
	   C_State   = BREWERY.get_Tm1_BREWING_1_C_State()
	   timeleft  = BREWERY.get_Tm1_BREWING_1_timeleft()
	   self.boiltemp_act.updateData(B_TempFil)
	   self.boiltemp_set.updateData(B_TempSet)
	   self.mashtemp_act.updateData(M_TempFil)
	   self.mashtemp_set.updateData(M_TempSet)
	   self.controlstate.updateData(C_State)
	   self.timeleft_lab.updateData(timeleft)
	   self.statuslabel.setText(self.statustexts[C_State])
	   
	   requestpermission_z1 = self.requestpermission
	   self.requestpermission = BREWERY.get_Tm1_BREWING_1_requestpermission()
	   if ((requestpermission_z1==0)and(self.requestpermission==1)):
		   self.askuserforpermission()
    
    def askuserforpermission(self):
        self.permissionAction.setEnabled(True)    
        #reply = QtGui.QMessageBox.question(self, 'Message',"Advance to next stage?", QtGui.QMessageBox.Ok)
        
      
    def grantPermission(self):
        BREWERY.set_Tm1_BREWING_1_grantpermission(1)
        self.permissionAction.setDisabled(True)
    
    def plotUpdate(self):
        self.boiltempchart.update_figure(xdata=self.time_array,ydata=self.B_TempFil_array)
        self.mashtempchart.update_figure(xdata=self.time_array,ydata=self.M_TempFil_array)
        
    def CTRLloop(self):
	   BREWERY.loop()
        
    def increase_B_TempSet(self):
	   BREWERY.set_Tm1_BREWING_1_B_TempSet(BREWERY.get_Tm1_BREWING_1_B_TempSet() + 1.0)
	   
    def decrease_B_TempSet(self):
	   BREWERY.set_Tm1_BREWING_1_B_TempSet(BREWERY.get_Tm1_BREWING_1_B_TempSet() - 1.0)
	   
    def increase_M_TempSet(self):
	   BREWERY.set_Tm1_BREWING_1_M_TempSet(BREWERY.get_Tm1_BREWING_1_M_TempSet() + 1.0)
	   
    def decrease_M_TempSet(self):
	   BREWERY.set_Tm1_BREWING_1_M_TempSet(BREWERY.get_Tm1_BREWING_1_M_TempSet() - 1.0)	   
	   
    def increase_C_State(self):
	   BREWERY.set_Tm1_BREWING_1_C_State(BREWERY.get_Tm1_BREWING_1_C_State() + 1)
	   
    def decrease_C_State(self):
	   BREWERY.set_Tm1_BREWING_1_C_State(BREWERY.get_Tm1_BREWING_1_C_State() - 1)

    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self, 'Message',
            "Are you sure to quit?", QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            event.accept()
            self.fileQuit()
        else:
            event.ignore()        

        
def main():
    qApp = QtGui.QApplication(sys.argv)

    aw = BrewConnect_Window()
    aw.setWindowTitle("%s" % progname)
    aw.showMaximized()
    aw.show()

    sys.exit(qApp.exec_()) 


if __name__ == '__main__':
    main() 
