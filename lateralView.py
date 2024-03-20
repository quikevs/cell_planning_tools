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

from PyQt5.QtGui import QMouseEvent
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    )
from matplotlib.figure import Figure
from matplotlib.backend_bases import MouseEvent
from matplotlib.lines import Line2D
from matplotlib.text import Text


import numpy as np
import os
from math import radians, degrees

from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import QDockWidget, QSizePolicy
from qgis.PyQt.QtGui import QCloseEvent

from qgis.gui import QgisInterface, QgsDockWidget
from qgis.core import QgsPointXY

from .settings import Settings
from .rf import CellSector
from .utils import Geometry, logMessage


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, dpi=100) -> None:
        figure = Figure(dpi=dpi, facecolor='gainsboro')
        self.axes = figure.add_subplot(111)
        figure.subplots_adjust(left=0.03, right=0.99, top=0.9, bottom=0.1)
        super().__init__(figure)

        self.mpl_connect("motion_notify_event", self.on_motion)
        self.clear()
        return
    def setCrossHairVisible(self, visible: bool) -> bool:
        needRedraw = self.hLine.get_visible() != visible
        self.hLine.set_visible(visible)
        self.vLine.set_visible(visible)
        self.text.set_visible(visible)
        return needRedraw

    def on_motion(self, event: MouseEvent):
        if self.hLine:
            if not event.inaxes:
                needRedraw = self.setCrossHairVisible(False)
                if needRedraw:
                    self.draw()
            else:
                self.setCrossHairVisible(True)
                # print(f'{x}, {y}')
                self.hLine.set_ydata([event.ydata])
                self.vLine.set_xdata([event.xdata])
                self.text.set_text(
                    f'distance: {event.xdata:,.2f} {self.units}\n' +
                    f'height: {event.ydata:,.2f} {self.units}')
                self.draw()
        return

    def clear(self) -> None:
        self.axes.clear()
        self.hLine: Line2D = None
        self.vLine: Line2D = None
        self.text: Text = None
        self.units: str = ''
        self.figure.tight_layout()
        self.draw()
        return


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    Settings().plugin_directory, "resources", "ui", "lateral_view.ui"
))


class LateralView(QgsDockWidget, FORM_CLASS):
    settings = Settings()

    def __init__(
            self,
            interface: QgisInterface,
            parent=None,
            ) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.interface: QgisInterface = interface
        self.canvas = PlotCanvas(parent=self)
        self.canvas.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_canvas.addWidget(self.canvas)

    def clear(self) -> None:
        self.canvas.clear()
        return

    def plot(
            self,
            sector: CellSector,
            mainLobeGeometry: Geometry,
            upperSidelobeGeometry: Geometry,
            ) -> None:
        self.clear()
        if not mainLobeGeometry or not upperSidelobeGeometry:
            return
        
        if self.settings.units == 0:
            # self.canvas.axes.set_xlabel("Distance (m)")
            self.canvas.axes.xaxis.set_units('m')
            # self.canvas.axes.set_ylabel("Height (m)")
            self.canvas.axes.yaxis.set_units('m')
            self.canvas.units = 'm'
        else:
            # self.canvas.axes.set_xlabel("Distance (ft)")
            self.canvas.axes.xaxis.set_units('ft')
            # self.canvas.axes.set_ylabel("Height (ft)")
            self.canvas.axes.yaxis.set_units('ft')
            self.canvas.units = 'ft'

        #self.canvas.axes.spines["top"].set_color("None")
        #self.canvas.axes.spines["right"].set_color("None")

        y = np.array(upperSidelobeGeometry.heightVector)
        x = np.arange(0, len(upperSidelobeGeometry.heightVector) *
                      upperSidelobeGeometry.stepSize,
                      upperSidelobeGeometry.stepSize)
        
        height = sector.floorHeight + sector.antennaHeight

        self.canvas.hLine = self.canvas.axes.axhline(
            color='k', lw=0.8, ls='--', y=height)
        self.canvas.vLine = self.canvas.axes.axvline(
            color='k', lw=0.8, ls='--')
        self.canvas.text = \
            self.canvas.axes.text(0.85, 0.72, '',
                                  transform=self.canvas.axes.transAxes)
        
        self.canvas.axes.set_xlim(left=0, right=x.max())
        self.canvas.axes.step(x, y, color="black")

        

        upperSideLobe = -np.tan(
            radians(sector.totalDowntilt-(sector.vWidth/2)))*x + height

        self.canvas.axes.plot(x, upperSideLobe, color='blue')
        
        x2 = np.arange(0, len(mainLobeGeometry.heightVector) *
                       mainLobeGeometry.stepSize, mainLobeGeometry.stepSize)
        mainlobe = -np.tan(radians(sector.totalDowntilt))*x2 + height
        self.canvas.axes.plot(x2, mainlobe, color='green')

        self.canvas.figure.tight_layout()
        self.canvas.axes.grid(True,'major','both',
                              color='gray', linestyle='--', linewidth=0.4)
        self.canvas.draw()
        return
