# -*- coding: utf-8 -*-
"""
 Cell Planning Tools

 A set of Radio Access Network planning and optimization tools

                    (C) 2023 by quikevs
                  enriquevelazquez@gmail.com

                        MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

__author__ = 'Enrique Velazquez'
__date__ = '2023-04-21'
__copyright__ = '(C) 2023 by Rockmedia'


from qgis.PyQt.QtCore import (
    pyqtSignal,
    Qt,
    QCoreApplication,
)

from qgis.PyQt import uic

from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QCheckBox,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QMessageBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from qgis.PyQt.QtGui import(
    QColor,
    QIcon,
    QPixmap, 
    QCloseEvent, QKeyEvent
)

from qgis.gui import (
    QgisInterface,
    QgsMapLayerComboBox, 
    QgsMapCanvas,
    QgsMapMouseEvent,
    QgsMapTool,
    QgsMapToolEmitPoint,
    QgsMapToolIdentifyFeature,
    QgsRubberBand,
    )

from qgis.core import (
    QgsCoordinateTransform,
    QgsProject,
    QgsMapLayerProxyModel,
    QgsWkbTypes,
    QgsExpression,
    QgsExpressionContext,
    QgsFeature,
    QgsFields,
    QgsVectorLayer,
    QgsRasterLayer
)
import os
from math import radians, degrees
from typing import Union, Dict, List, Any
from enum import IntEnum

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


from .rf import CellSector, CellSectorBuilder, TCellSector
from .utils import Geometry, GeometryManager, EPSG4326, logMessage
from .settings import settings
from .errors import OutOfRangeError, NotInitialized

class Lobe(IntEnum):
    MAINLOBE = 0
    UPPERSIDELOBE = 1
    LOCKED_MAINLOBE = 2
    LOCKED_UPPERSIDELOBE = 3

class Attributes(IntEnum):
    HEIGHT = 0
    AZIMUTH = 1
    M_TILT = 2
    E_TILT = 3

class PlotCanvas(FigureCanvas):
    def __init__(self, parent = None, width=5, height=2, dpi = 100) -> None:
        figure = Figure()
        self.axes = figure.add_subplot(111)
        super().__init__(figure)
        return
    def clear(self) -> None:
        self.axes.clear()
        return

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    settings.plugin_directory, "resources", "ui", "lateral_view.ui"
))

class LateralView(QDockWidget, FORM_CLASS):
    closingPlugin_lv = pyqtSignal()
    def __init__(self, 
                 interface: QgisInterface, 
                 plugin = None, 
                 parent = None)->None:
        super().__init__(parent)
        self.setupUi(self)
        self.plugin = plugin
        self.interface = interface
        self.canvas = PlotCanvas(parent = self)
        self.canvas.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_canvas.addWidget(self.canvas)

    def clear(self) -> None:
        self.canvas.clear()
        return
    
    def closeEvent(self, event: QCloseEvent) -> None:
        self.closingPlugin_lv.emit()
        event.accept()
        return
    
    def show(self) -> None:
        self.interface.addDockWidget(Qt.BottomDockWidgetArea, self)
        return
    
    def plot(self, 
             sector: CellSector, 
             mainLobeGeometry: Geometry,
             upperSidelobeGeometry: Geometry)-> None:
        self.clear()
        if not mainLobeGeometry or not upperSidelobeGeometry:
            return
        if settings.units == 0:
            self.canvas.axes.set_xlabel("Distance (m)")
            self.canvas.axes.set_ylabel("Height (m)")
        else:
            self.canvas.axes.set_xlabel("Distance (ft)")
            self.canvas.axes.set_ylabel("Height (ft)")
        
        self.canvas.axes.spines["top"].set_color("None")
        self.canvas.axes.spines["right"].set_color("None")

        y = np.array(upperSidelobeGeometry.heightVector)
        x = np.arange(0, len(upperSidelobeGeometry.heightVector)*
                      upperSidelobeGeometry.stepSize,
                      upperSidelobeGeometry.stepSize)
        
        self.canvas.axes.step(x,y,color="black")

        height = sector.floorHeight + sector.antennaHeight

        upperSideLobe = -np.tan(
            radians(sector.totalDowntilt-(sector.vWidth/2)))*x + height
        
        self.canvas.axes.plot(x, upperSideLobe, color='blue')

        x2 = np.arange(0, len(mainLobeGeometry.heightVector)*
                       mainLobeGeometry.stepSize, mainLobeGeometry.stepSize)
        mainlobe = -np.tan(radians(sector.totalDowntilt))*x2 + height
        self.canvas.axes.plot(x2,mainlobe,color='green')

        self.canvas.figure.tight_layout()
        self.canvas.draw()
        return

class uiAlterSector(object):
    def setupUI(self, dockWidget: QDockWidget):

        # dockWidget
        dockWidget.setObjectName("dockWidget")
        dockWidget.setFocusPolicy(Qt.StrongFocus)
        dockWidget.setWindowTitle("Cell Planning Tools - Alter Cell-sector")
        
        self.dock = QWidget()
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.dock.sizePolicy().hasHeightForWidth())
        self.dock.setSizePolicy(sizePolicy)
        self.dock.setObjectName("dockWidgetContents")

        self.vlDockWidget = QVBoxLayout(self.dock)
        self.vlDockWidget.setObjectName("vlDockWidget")

        #Sector Selector

        self.hlSectorSelector = QHBoxLayout()
        self.hlSectorSelector.setObjectName("hlSectorSelector")

        self.lbSectorName = QLabel(self.dock)
        self.lbSectorName.setText("Cell-sector")
        self.lbSectorName.setObjectName("lbSectorName")
        self.hlSectorSelector.addWidget(self.lbSectorName)

        self.leSectorName = QLineEdit(self.dock)
        self.leSectorName.setText("")
        self.leSectorName.setObjectName("leSectorName")
        self.leSectorName.setEnabled(False)
        self.hlSectorSelector.addWidget(self.leSectorName)

        self.tbCapture = QToolButton(self.dock)
        self.tbCapture.setText("+")
        icon = QIcon()
        icon.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","select.svg")), 
                QIcon.Normal, QIcon.Off)
        self.tbCapture.setIcon(icon)
        self.tbCapture.setObjectName("tbCapture")
        self.tbCapture.setToolTip("Capture Cell-sector from Map")
        self.hlSectorSelector.addWidget(self.tbCapture)

        self.tbShowLateralView = QToolButton(self.dock)
        self.tbShowLateralView.setText("view")
        icon = QIcon()
        icon.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","inspect.svg")), 
                QIcon.Normal, QIcon.Off)
        self.tbShowLateralView.setIcon(icon)
        self.tbShowLateralView.setObjectName("tbShowLateralView")
        self.tbShowLateralView.setEnabled(False)
        self.hlSectorSelector.addWidget(self.tbShowLateralView)

        self.vlDockWidget.addLayout(self.hlSectorSelector)

        #Attribute Table
        self.hlAttributes = QHBoxLayout()
        self.hlAttributes.setObjectName("hlAttributes")
        self.tAttributes = QTableWidget(self.dock)
        self.tAttributes.setEnabled(False)
        self.tAttributes.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tAttributes.setSelectionMode(QAbstractItemView.NoSelection)
        self.tAttributes.setGridStyle(Qt.DotLine)
        self.tAttributes.setRowCount(4)
        self.tAttributes.setColumnCount(2)
        self.tAttributes.setObjectName("tAttributes")

        item = QTableWidgetItem()
        item.setText("Height")
        self.tAttributes.setVerticalHeaderItem(0, item)
        item = QTableWidgetItem()
        item.setText("Azimuth")
        self.tAttributes.setVerticalHeaderItem(1, item)
        item = QTableWidgetItem()
        item.setText("mDowntilt")
        self.tAttributes.setVerticalHeaderItem(2, item)
        item = QTableWidgetItem()
        item.setText("eDowntilt")
        self.tAttributes.setVerticalHeaderItem(3, item)
        item = QTableWidgetItem()
        item.setText("Value")
        self.tAttributes.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        item.setText("Initial")
        self.tAttributes.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem()
        self.tAttributes.setItem(0, 0, item)
        item = QTableWidgetItem()
        self.tAttributes.setItem(0, 1, item)
        item = QTableWidgetItem()
        self.tAttributes.setItem(1, 0, item)
        item = QTableWidgetItem()
        self.tAttributes.setItem(1, 1, item)
        item = QTableWidgetItem()
        self.tAttributes.setItem(2, 0, item)
        item = QTableWidgetItem()
        self.tAttributes.setItem(2, 1, item)
        item = QTableWidgetItem()
        self.tAttributes.setItem(3, 0, item)
        item = QTableWidgetItem()
        self.tAttributes.setItem(3, 1, item)
        self.hlAttributes.addWidget(self.tAttributes)

        self.vlEdit = QVBoxLayout()
        self.vlEdit.setObjectName("vlEdit")
        self.tbEdit = QToolButton(self.dock)
        self.tbEdit.setEnabled(False)
        self.tbEdit.setText("e")
        icon2 = QIcon()
        icon2.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","edit.svg")), 
                QIcon.Normal, QIcon.Off)
        self.tbEdit.setIcon(icon2)
        self.tbEdit.setObjectName("tbEdit")
        self.vlEdit.addWidget(self.tbEdit)
        self.tbSettings = QToolButton(self.dock)
        self.tbSettings.setText('s')
        icon = QIcon()
        icon.addPixmap(QPixmap(
            ':/images/themes/default/mActionOptions.svg'),
            QIcon.Normal, QIcon.Off)
        self.tbSettings.setIcon(icon)
        self.tbSettings.setObjectName("tbSettings")
        self.vlEdit.addWidget(self.tbSettings)
        spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.vlEdit.addItem(spacerItem)
        self.hlAttributes.addLayout(self.vlEdit)
        self.vlDockWidget.addLayout(self.hlAttributes)

        #Geometry Section

        self.hlGeometry = QHBoxLayout()
        self.hlGeometry.setObjectName("hlGeometry")
        self.lbGeometry = QLabel(self.dock)
        self.lbGeometry.setText("Geometry")
        self.lbGeometry.setObjectName("lbGeometry")
        self.hlGeometry.addWidget(self.lbGeometry)
        self.tbFreeHand = QToolButton(self.dock)
        self.tbFreeHand.setEnabled(False)
        self.tbFreeHand.setText("c")
        icon3 = QIcon()
        icon3.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","free_hand.svg")), 
                QIcon.Normal, QIcon.Off)
        self.tbFreeHand.setIcon(icon3)
        self.tbFreeHand.setObjectName("tbFreeHand")
        self.hlGeometry.addWidget(self.tbFreeHand)

        self.pbRestore = QPushButton(self.dock)
        self.pbRestore.setEnabled(False)
        self.pbRestore.setText("Restore")
        self.pbRestore.setObjectName("pbRestore")
        self.hlGeometry.addWidget(self.pbRestore)

        self.pbClear = QPushButton(self.dock)
        self.pbClear.setEnabled(False)
        self.pbClear.setText("Clear")
        self.pbClear.setObjectName("pbClear")
        self.hlGeometry.addWidget(self.pbClear)
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.hlGeometry.addItem(spacerItem1)
        self.vlDockWidget.addLayout(self.hlGeometry)

        #Line

        self.line = QFrame(self.dock)
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setObjectName("line")
        self.vlDockWidget.addWidget(self.line)

        #Controls

        self.lbControls = QLabel(self.dock)
        self.lbControls.setText("Controls")
        self.lbControls.setObjectName("lbControls")
        self.vlDockWidget.addWidget(self.lbControls)
        self.hlControls = QHBoxLayout()
        self.hlControls.setObjectName("hlControls")
        spacerItem2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.hlControls.addItem(spacerItem2)

        self.vlLockControls = QVBoxLayout()
        self.vlLockControls.setObjectName("vlLockControls")
        self.lockAzimuth = QCheckBox(self.dock)
        self.lockAzimuth.setEnabled(False)
        self.lockAzimuth.setText("Lock Azimuth")
        self.lockAzimuth.setChecked(True)
        self.lockAzimuth.setObjectName("lockAzimuth")
        self.vlLockControls.addWidget(self.lockAzimuth)

        self.lockMDownTilt = QCheckBox(self.dock)
        self.lockMDownTilt.setEnabled(False)
        self.lockMDownTilt.setText("Lock Mechanical Downtilt")
        self.lockMDownTilt.setChecked(True)
        self.lockMDownTilt.setObjectName("lockMDownTilt")
        self.vlLockControls.addWidget(self.lockMDownTilt)

        self.lockHeight = QCheckBox(self.dock)
        self.lockHeight.setEnabled(False)
        self.lockHeight.setText("Lock Antenna Height")
        self.lockHeight.setChecked(True)
        self.lockHeight.setObjectName("lockHeight")
        self.vlLockControls.addWidget(self.lockHeight)

        self.hlControls.addLayout(self.vlLockControls)

        self.vlHeightControls = QVBoxLayout()
        self.vlHeightControls.setObjectName("vlHeightControls")
        self.lbHeight = QLabel(self.dock)
        self.lbHeight.setText("Height")
        self.lbHeight.setAlignment(Qt.AlignCenter)
        self.lbHeight.setObjectName("lbHeight")
        self.vlHeightControls.addWidget(self.lbHeight)
        self.hlUpControls = QHBoxLayout()
        self.hlUpControls.setObjectName("hlUpControls")
        self.tbUp = QToolButton(self.dock)
        self.tbUp.setText("+")
        icon4 = QIcon()
        icon4.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","up.svg"))
                , QIcon.Normal, QIcon.Off)
        self.tbUp.setIcon(icon4)
        self.tbUp.setObjectName("tbUp")
        self.tbUp.setEnabled(False)
        self.hlUpControls.addWidget(self.tbUp)
        self.vlHeightControls.addLayout(self.hlUpControls)

        self.valueHeight = QLabel(self.dock)
        self.valueHeight.setText("15 m")
        self.valueHeight.setAlignment(Qt.AlignCenter)
        self.valueHeight.setObjectName("valueHeight")
        self.vlHeightControls.addWidget(self.valueHeight)
        self.hlDownControls = QHBoxLayout()
        self.hlDownControls.setObjectName("hlDownControls")
        self.tbDown = QToolButton(self.dock)
        self.tbDown.setText("-")
        icon5 = QIcon()
        icon5.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","down.svg"))
                , QIcon.Normal, QIcon.Off)
        self.tbDown.setIcon(icon5)
        self.tbDown.setObjectName("tbDown")
        self.tbDown.setEnabled(False)
        self.hlDownControls.addWidget(self.tbDown)
        self.vlHeightControls.addLayout(self.hlDownControls)

        self.hlControls.addLayout(self.vlHeightControls)
        self.vlAzimuthTiltControls = QVBoxLayout()
        self.vlAzimuthTiltControls.setObjectName("vlAzimuthTiltControls")
        self.lbAzimuth = QLabel(self.dock)
        self.lbAzimuth.setText("Azimuth")
        self.lbAzimuth.setAlignment(Qt.AlignCenter)
        self.lbAzimuth.setObjectName("lbAzimuth")
        self.vlAzimuthTiltControls.addWidget(self.lbAzimuth)
        self.hlAzimuthControl = QHBoxLayout()
        self.hlAzimuthControl.setObjectName("hlAzimuthControl")
        self.tbCCW = QToolButton(self.dock)
        self.tbCCW.setText("-")
        icon6 = QIcon()
        icon6.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","ccw.svg"))
                , QIcon.Normal, QIcon.Off)
        self.tbCCW.setIcon(icon6)
        self.tbCCW.setObjectName("tbCCW")
        self.tbCCW.setEnabled(False)
        self.hlAzimuthControl.addWidget(self.tbCCW)

        self.valueAzimuth = QLabel(self.dock)
        self.valueAzimuth.setText("0°")
        self.valueAzimuth.setAlignment(Qt.AlignCenter)
        self.valueAzimuth.setObjectName("valueAzimuth")
        self.hlAzimuthControl.addWidget(self.valueAzimuth)
        self.tbCW = QToolButton(self.dock)
        self.tbCW.setText("+")
        icon7 = QIcon()
        icon7.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","cw.svg"))
                , QIcon.Normal, QIcon.Off)
        self.tbCW.setIcon(icon7)
        self.tbCW.setObjectName("tbCW")
        self.tbCW.setEnabled(False)
        self.hlAzimuthControl.addWidget(self.tbCW)
        self.vlAzimuthTiltControls.addLayout(self.hlAzimuthControl)

        self.hlTiltControl = QHBoxLayout()
        self.hlTiltControl.setObjectName("hlTiltControl")
        self.tbUpTilt = QToolButton(self.dock)
        self.tbUpTilt.setText("-")
        icon8 = QIcon()
        icon8.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","ut.svg"))
                , QIcon.Normal, QIcon.Off)
        self.tbUpTilt.setIcon(icon8)
        self.tbUpTilt.setObjectName("tbUpTilt")
        self.tbUpTilt.setEnabled(False)
        self.hlTiltControl.addWidget(self.tbUpTilt)

        self.valueDowntilt = QLabel(self.dock)
        self.valueDowntilt.setText("2°")
        self.valueDowntilt.setAlignment(Qt.AlignCenter)
        self.valueDowntilt.setObjectName("valueDowntilt")
        self.hlTiltControl.addWidget(self.valueDowntilt)
        self.tbDownTilt = QToolButton(self.dock)
        self.tbDownTilt.setText("+")
        icon9 = QIcon()
        icon9.addPixmap(QPixmap(
            os.path.join(
                settings.plugin_directory,
                "resources","icons","dt.svg"))
                , QIcon.Normal, QIcon.Off)

        self.tbDownTilt.setIcon(icon9)
        self.tbDownTilt.setObjectName("tbDownTilt")
        self.hlTiltControl.addWidget(self.tbDownTilt)
        self.vlAzimuthTiltControls.addLayout(self.hlTiltControl)
        self.lbDonwtilt = QLabel(self.dock)
        self.lbDonwtilt.setText("Downtilt")
        self.lbDonwtilt.setAlignment(Qt.AlignCenter)
        self.lbDonwtilt.setObjectName("lbDonwtilt")
        self.tbDownTilt.setEnabled(False)
        self.vlAzimuthTiltControls.addWidget(self.lbDonwtilt)
        self.hlControls.addLayout(self.vlAzimuthTiltControls)
        self.vlDockWidget.addLayout(self.hlControls)

        dockWidget.setWidget(self.dock)

    def retranslateUi(self, DockWidget):
        _translate = QCoreApplication.translate
        __sortingEnabled = self.tAttributes.isSortingEnabled()
        self.tAttributes.setSortingEnabled(False)
        self.tAttributes.setSortingEnabled(__sortingEnabled)



class AlterSector(QDockWidget, uiAlterSector):
    keyPressed = pyqtSignal()
    #closingPLugin = pyqtSignal()
    def __init__(self,
                 interface: QgisInterface,
                 plugin= None,
                 parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setupUI(self) 
        self.plugin = plugin
        self.interface: QgisInterface = interface
        self.canvas: QgsMapCanvas = interface.mapCanvas()

        self.controls: List[QWidget] = [
            self.tbCapture,
            self.tbShowLateralView,
            self.tbEdit,
            self.tbFreeHand,
            self.pbRestore,
            self.pbClear,
            self.lockAzimuth,
            self.lockHeight,
            self.lockMDownTilt,
            self.tbUp,
            self.tbDown,
            self.tbCCW,
            self.tbCW,
            self.tbUpTilt,
            self.tbDownTilt
        ]

        self.mapTool: QgsMapTool = None

        

        self.rubberBand: QgsRubberBand = \
            QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.rubberBand.setWidth(3)

        self.setFocusPolicy(Qt.StrongFocus)

        #Signals

        self.tbCapture.clicked.connect(self.selectSector)
        self.pbClear.clicked.connect(self.clear)
        self.keyPressed.connect(self.keyPressEvent)
        self.tbUp.clicked.connect(self.moveUp)
        self.tbDown.clicked.connect(self.moveDown)
        self.tbCCW.clicked.connect(self.rotateCcw)
        self.tbCW.clicked.connect(self.rotateCw)
        self.tbUpTilt.clicked.connect(self.upTilt)
        self.tbDownTilt.clicked.connect(self.downTilt)

        self.lateralView = LateralView(interface, plugin, parent)
        self.tbShowLateralView.clicked.connect(self.lateralView.show)
        
        self.manager: GeometryManager = GeometryManager(EPSG4326)
        demlist = [layer.value()['layer'] for layer in settings.demList]
        self.manager.setElevationRasterList(demlist)
        dsmlist = [layer.value()['layer'] for layer in settings.dsmList]
        self.manager.setSurfaceRasterList(dsmlist)
        self.manager.setSensibility(float(settings.sensibility))
        self.manager.setUpperSidelobeLimit(settings.upperSidelobeLimit)
        
        self.selectedSector: CellSector = None
        self.workingLayer = None
        self.activeListen = False
        self.layerIndexes = {}
        self.sectorSet: List[CellSector]= [None]*4
        self.initialState: List[float] = []
        self.selectedGeometry: Geometry = None
        self.layerIds: List[int] = [None]*4
        return
    
    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key_Escape:
            if self.activeListen:
                self.cancelMeasurement()
        if e.key() == Qt.Key_I:
            if self.activeListen:
                self.cancelMeasurement()
            self.selectSector()
        if e.key() == Qt.Key_C:
            if self.activeListen:
                self.cancelMeasurement()
            logMessage("Free hand Transform Not Implemented")
        return
    
    def cancelMeasurement(self):
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        self.activeListen = False
        self.canvas.unsetMapTool(self.mapTool)
        return
    
    def closeEvent(self, event: QCloseEvent) -> None:
        self.cancelMeasurement()
        #self.lateral_view.close()
        #self.closeingPlugin.emit()
        event.accept()
        return
    
    def enableControls(self, state: bool = True) -> None:
        for control in self.controls:
            control.setEnabled(state)
        return
    
    def clear(self):
        self.activeListen = False

        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        self.rubberBand.setColor(settings.rubberBandColor)
        #self.rubberBand.setFillColor(settings.rubberBandFillColor)

        self.leSectorName.setText("")
        self.writeTable("","","","",0)
        self.writeTable("","","","",1)
        self.enableControls(False)
        self.tbCapture.setEnabled(True)


        self.selectedSector: CellSector = None
        self.workingLayer = None
        self.activeListen = False
        self.layerIndexes = {}
        self.sectorSet: List[CellSector]= [None]*4
        self.initialState: List[float] = [None]*4
        self.selectedGeometry: Geometry = None
        self.layerIds: List[int] = [None]*4

        self.lateralView.clear()
        self.lateralView.canvas.clear()
        return
    
    def writeTable(self, 
              height: Union[float,str],
              azimuth: Union[float,str],
              mDowntilt: Union[float,str],
              eDowntilt: Union[float,str],
              column: int = 1) -> None:
        if height:
            height = round(height,2)
        if azimuth:
            azimuth = round(azimuth,2)
        if mDowntilt:
            mDowntilt = round(mDowntilt, 2)
        if eDowntilt:
            eDowntilt = round(eDowntilt, 2)

        self.tAttributes.setItem(0, column, QTableWidgetItem(str(height)))
        self.tAttributes.setItem(1, column, QTableWidgetItem(str(azimuth)))
        self.tAttributes.setItem(2, column, QTableWidgetItem(str(mDowntilt)))
        self.tAttributes.setItem(3, column, QTableWidgetItem(str(eDowntilt)))
        return
        
    def selectSector(self) -> None:
        self.clear()
        
        self.workingLayer: QgsVectorLayer = settings.sectorLayer
        if not self.manager.isReady() or not self.workingLayer:
            QMessageBox.information(self.interface.mainWindow(),
                                    "Settings Error",
                                    "Geometry Manager not initialized."\
                                    " Please verify the Cell Planning Tool"\
                                    " settings.")
            return
        else:
            fields: QgsFields = self.workingLayer.fields()
            self.layerIndexes = {
                'height': fields.indexOf(settings.mapAntennaHeight),
                'azimuth': fields.indexOf(settings.mapAzimuth),
                'm_tilt': fields.indexOf(settings.mapMTilt),
                'e_tilt': fields.indexOf(settings.mapETilt),
            }
            for index in self.layerIndexes:
                
                if self.layerIndexes[index] == -1:
                    QMessageBox.information(self.interface.mainWindow(),
                                    "Layer Field Map Error",
                                    "Incomplete or incorrect Layer Field Map."\
                                    " Please verify the Cell Planning Tool"\
                                    " Layer Field Map settings.")
                    return
            
            self.mapTool = QgsMapToolIdentifyFeature(self.canvas)
            self.mapTool.setLayer(self.workingLayer)
            self.canvas.setMapTool(self.mapTool)
            self.mapTool.featureIdentified.connect(self.identify)

        return
    
    def identify(self, feature: QgsFeature) -> None:
        self.canvas.unsetMapTool(self.mapTool)
        self.layerIds: List[int] = [None]*4
        lockedFeature: QgsFeature = None
        if feature['lobe'] == "Upper Sidelobe":
            self.layerIds[Lobe.UPPERSIDELOBE] = feature.id()
            try:
                index = next(
                    self.workingLayer.getFeatures(
                        f'"{settings.mapName}"=\'{feature[settings.mapName]}\' and "lobe"=\'Mainlobe\'')).id()
                self.layerIds[Lobe.MAINLOBE] = index
            except StopIteration:
                self.layerIds[Lobe.MAINLOBE] = None
        
        else:
            self.layerIds[Lobe.MAINLOBE] = feature.id()
            try:
                
                self.layerIds[Lobe.UPPERSIDELOBE] = next(
                    self.workingLayer.getFeatures(
                        f'"{settings.mapName}"=\'{feature[settings.mapName]}\' and "lobe"=\'Upper Sidelobe\'')).id()
            except StopIteration:
                self.layerIds[Lobe.UPPERSIDELOBE] = None
        
        expression: QgsExpression = QgsExpression(settings.mapLock)
        context: QgsExpressionContext = QgsExpressionContext()
        context.setFeature(feature)
        context.setFields(self.workingLayer.fields())
        lockName = expression.evaluate(context)
        #Try to identify the locked sector
        if not lockName == "":
            try:
                
                lockedFeature = next(
                    self.workingLayer.getFeatures(
                        f'"{settings.mapName}"=\'{lockName}\' and "lobe"=\'Mainlobe\''))
                self.layerIds[Lobe.LOCKED_MAINLOBE] =  lockedFeature.id()

            except StopIteration:
                self.layerIds[Lobe.LOCKED_MAINLOBE] = None

            try:
                self.layerIds[Lobe.LOCKED_UPPERSIDELOBE] = next(
                    self.workingLayer.getFeatures(
                        f'"{settings.mapName}"=\'{lockName}\' and "lobe"=\'Upper Sidelobe\'')).id()
            except StopIteration:
                self.layerIds[Lobe.LOCKED_UPPERSIDELOBE] = None

        if not self.layerIds[Lobe.MAINLOBE]:
            return
        
        name = QgsExpression(settings.mapName).evaluate(context)
        shift = QgsExpression(settings.mapShift).evaluate(context)
        hWidth = QgsExpression(settings.mapHWidth).evaluate(context)
        vWidth = QgsExpression(settings.mapVWidth).evaluate(context)

        sectorBuilder = CellSectorBuilder(
            name,
            feature.geometry().asPolygon()[0][0])
        sectorBuilder.setAntennaHeigth(feature[settings.mapAntennaHeight])
        sectorBuilder.setAzimuth(feature[settings.mapAzimuth],float(shift))
        sectorBuilder.setMDowntilt(feature[settings.mapMTilt])
        sectorBuilder.setEDowntilt(feature[settings.mapETilt])
        sectorBuilder.setHWidth(float(hWidth))
        sectorBuilder.setVWidth(float(vWidth))

        ## missing e_tilt range
        mainlobe = sectorBuilder.mainlobe()
        floorHeight= self.manager.sampleElevation(mainlobe.origin)
        mainlobe.floorHeight = floorHeight
        self.sectorSet[Lobe.MAINLOBE] = mainlobe
        uppersidelobe = sectorBuilder.upperSidelobe()
        uppersidelobe.floorHeight = floorHeight
        self.sectorSet[Lobe.UPPERSIDELOBE] = uppersidelobe

        if lockedFeature:
            context.setFeature(lockedFeature)
            name = QgsExpression(settings.mapName).evaluate(context)
            shift = QgsExpression(settings.mapShift).evaluate(context)
            hWidth = QgsExpression(settings.mapHWidth).evaluate(context)
            vWidth = QgsExpression(settings.mapVWidth).evaluate(context)

            sectorBuilder = CellSectorBuilder(
                name,
                lockedFeature.geometry().asPolygon()[0][0])
            sectorBuilder.setAntennaHeigth(lockedFeature[settings.mapAntennaHeight])
            sectorBuilder.setAzimuth(lockedFeature[settings.mapAzimuth],float(shift))
            sectorBuilder.setMDowntilt(lockedFeature[settings.mapMTilt])
            sectorBuilder.setEDowntilt(lockedFeature[settings.mapETilt])
            sectorBuilder.setHWidth(float(hWidth))
            sectorBuilder.setVWidth(float(vWidth))

            locked_mainlobe = sectorBuilder.mainlobe()
            locked_mainlobe.floorHeight=floorHeight
            self.sectorSet[Lobe.LOCKED_MAINLOBE] = \
                locked_mainlobe
            locked_uppersidelobe = sectorBuilder.upperSidelobe()
            locked_uppersidelobe.floorHeight = floorHeight
            self.sectorSet[Lobe.LOCKED_UPPERSIDELOBE] = \
                locked_uppersidelobe

        else:
            self.sectorSet[Lobe.LOCKED_MAINLOBE] = None
            self.sectorSet[Lobe.LOCKED_UPPERSIDELOBE] = None
        
        self.initialState = [
            feature[settings.mapAntennaHeight], 
            feature[settings.mapAzimuth],
            feature[settings.mapMTilt],
            feature[settings.mapETilt],
        ]
        self.updateLabels(self.sectorSet[Lobe.MAINLOBE].copy())
        self.lateralView.plot(
            mainlobe,
            self.manager.computeGeometry(mainlobe),
            self.manager.computeGeometry(uppersidelobe)
        )
        return
    
    def updateLabels(self, sector: CellSector) -> None:
        self.leSectorName.setText(sector.name)
        self.writeTable(
            sector.antennaHeight,
            sector.azimuth,
            sector.mDowntilt,
            sector.eDowntilt,0
        )
        self.writeTable(
            self.initialState[Attributes.HEIGHT],
            self.initialState[Attributes.AZIMUTH],
            self.initialState[Attributes.M_TILT],
            self.initialState[Attributes.E_TILT],
            1
        )
        self.valueHeight.setText(str(round(sector.antennaHeight,0)))
        self.valueAzimuth.setText(str(round(sector.azimuth,1))+"°")
        self.valueDowntilt.setText(str(round(sector.totalDowntilt,1))+"°")

        self.enableControls(True)
        return
    
    def moveUp(self):
        if not self.workingLayer.isEditable():
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Not editable layer", 
                "Enable edit mode in sector layer before making changes.")
            return
        if self.lockHeight.isChecked():
            return
        self.enableControls(False)
        sector: CellSector = self.sectorSet[Lobe.MAINLOBE].copy()
        #TODO: move this parameter to settings
        step = 1.0
        sector.antennaHeight += step
        selectedGeometry: Geometry = self.manager.computeGeometry(sector)
        if selectedGeometry:
            self.postChangeUpdate(sector, selectedGeometry)
        else:
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Error Computing Geometry", 
                "The raster List may not be initializade properly.")
        self.enableControls(True)
        return
    
    def moveDown(self):
        if not self.workingLayer.isEditable():
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Not editable layer", 
                "Enable edit mode in sector layer before making changes.")
            return
        if self.lockHeight.isChecked():
            return
        self.enableControls(False)
        sector: CellSector = self.sectorSet[Lobe.MAINLOBE].copy()
        #TODO: move this parameter to settings
        step = -1
        if sector.antennaHeight + step <= 0:
            sector.antennaHeight = 0.5
        else:
            sector.antennaHeight+=step
        selectedGeometry: Geometry = self.manager.computeGeometry(sector)
        if selectedGeometry:
            self.postChangeUpdate(sector, selectedGeometry)
        else:
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Error Computing Geometry", 
                "The raster List may not be initializade properly.")
        self.enableControls(True)
        return
    
    def rotateCcw(self):
        if not self.workingLayer.isEditable():
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Not editable layer", 
                "Enable edit mode in sector layer before making changes.")
            return
        if self.lockAzimuth.isChecked():
            return
        self.enableControls(False)
        sector = self.sectorSet[Lobe.MAINLOBE].copy()

        #TODO: move this parameter to settings
        step = -1
        sector.azimuth = (sector.azimuth + step) % 360
        selectedGeometry: Geometry = self.manager.computeGeometry(sector)
        if selectedGeometry:
            self.postChangeUpdate(sector, selectedGeometry)
        else:
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Error Computing Geometry", 
                "The raster List may not be initializade properly.")
        self.enableControls(True)
        return
    
    def rotateCw(self):
        if not self.workingLayer.isEditable():
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Not editable layer", 
                "Enable edit mode in sector layer before making changes.")
            return
        if self.lockAzimuth.isChecked():
            return
        self.enableControls(False)
        sector = self.sectorSet[Lobe.MAINLOBE].copy()

        #TODO: move this parameter to settings
        step = 1
        sector.azimuth = (sector.azimuth + step) % 360
        selectedGeometry: Geometry = self.manager.computeGeometry(sector)
        if selectedGeometry:
            self.postChangeUpdate(sector, selectedGeometry)
        else:
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Error Computing Geometry", 
                "The raster List may not be initializade properly.")
        self.enableControls(True)
        return
        
    def upTilt(self):
        if not self.workingLayer.isEditable():
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Not editable layer", 
                "Enable edit mode in sector layer before making changes.")
            return
        self.enableControls(False)
        sector = self.sectorSet[Lobe.MAINLOBE].copy()
        step = -0.5
        if 0 <= sector.eDowntilt+step <= 10:
            sector.eDowntilt += step
        elif not self.lockMDownTilt.isChecked():
            sector.mDowntilt += 2*step
            sector.eDowntilt -= step
        else:
            self.enableControls(True)
            return
        selectedGeometry: Geometry = self.manager.computeGeometry(sector)
        self.postChangeUpdate(sector, selectedGeometry)
        self.enableControls(True)
        return
    def downTilt(self):
        if not self.workingLayer.isEditable():
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Not editable layer", 
                "Enable edit mode in sector layer before making changes.")
            return
        self.enableControls(False)
        sector = self.sectorSet[Lobe.MAINLOBE].copy()
        step = 0.5
        if 0 <= sector.eDowntilt+step <= 10:
            sector.eDowntilt += step
        elif not self.lockMDownTilt.isChecked():
            sector.mDowntilt += 2*step
            sector.eDowntilt -= step
        else:
            self.enableControls(True)
            return
        selectedGeometry: Geometry = self.manager.computeGeometry(sector)
        if selectedGeometry:
            self.postChangeUpdate(sector, selectedGeometry)
        else:
            QMessageBox.information(
                self.interface.mainWindow(), 
                "Error Computing Geometry", 
                "The raster List may not be initializade properly.")
        self.enableControls(True)
        return
    
    def postChangeUpdate(self, sector: CellSector, geometry: Geometry):
        self.sectorSet[Lobe.MAINLOBE] = sector
        self.updateLayer(self.layerIds[Lobe.MAINLOBE], sector, geometry)
        self.writeTable(sector.antennaHeight, sector.azimuth, sector.mDowntilt, sector.eDowntilt,0)

        upperSidelobe = sector.copy()
        self.sectorSet[Lobe.UPPERSIDELOBE] = upperSidelobe
        upperSidelobe.mDowntilt -= upperSidelobe.vWidth / 2
        upperSidelobeGeometry = self.manager.computeGeometry(upperSidelobe)
        self.updateLayer(self.layerIds[Lobe.UPPERSIDELOBE], upperSidelobe, upperSidelobeGeometry)

        if self.layerIds[Lobe.LOCKED_MAINLOBE]:
            feature = self.workingLayer.getFeature(self.layerIds[Lobe.LOCKED_MAINLOBE])
            context: QgsExpressionContext = QgsExpressionContext()
            context.setFeature(feature)
            context.setFields(self.workingLayer.fields())

            name = QgsExpression(settings.mapName).evaluate(context)
            shift = QgsExpression(settings.mapShift).evaluate(context)
            hwidth = QgsExpression(settings.mapHWidth).evaluate(context)
            vwidth = QgsExpression(settings.mapVWidth).evaluate(context)

            builder = CellSectorBuilder(name, feature.geometry().asPolygon()[0][0])
            builder.setAntennaHeigth(sector.antennaHeight)
            builder.setAzimuth(sector.azimuth, float(shift))
            builder.setMDowntilt(sector.mDowntilt)
            builder.setEDowntilt(feature[settings.mapETilt])
            builder.setHWidth(hwidth)
            builder.setVWidth(vwidth)
            lockedMainlobe = builder.mainlobe()
            self.sectorSet[Lobe.LOCKED_MAINLOBE] = lockedMainlobe
            lockedMainLobeGeometry = self.manager.computeGeometry(lockedMainlobe)
            self.updateLayer(self.layerIds[Lobe.LOCKED_MAINLOBE], lockedMainlobe, lockedMainLobeGeometry)
            lockedUpperSidelobe = builder.upperSidelobe()
            self.sectorSet[Lobe.LOCKED_UPPERSIDELOBE] = lockedUpperSidelobe
            lockedUpperSidelobeGeometry = self.manager.computeGeometry(lockedUpperSidelobe)
            self.updateLayer(self.layerIds[Lobe.LOCKED_UPPERSIDELOBE], lockedUpperSidelobe, lockedUpperSidelobeGeometry)

        if self.canvas.isCachingEnabled():
            self.workingLayer.triggerRepaint()
        else:
            self.canvas.refresh()
        
        self.updateLabels(sector.copy())
        self.lateralView.plot(sector.copy(), geometry,upperSidelobeGeometry )

    
    def updateLayer(self, layerId: int, sector: CellSector, geometry: Geometry)-> None:
        self.workingLayer.changeAttributeValue(layerId, self.layerIndexes['height'], sector.antennaHeight)
        self.workingLayer.changeAttributeValue(layerId, self.layerIndexes['azimuth'], sector.azimuth)
        self.workingLayer.changeAttributeValue(layerId, self.layerIndexes['m_tilt'], sector.mDowntilt)
        self.workingLayer.changeAttributeValue(layerId, self.layerIndexes['e_tilt'], sector.eDowntilt)
        self.workingLayer.changeGeometry(layerId, geometry.geometry)
        return
   

    
