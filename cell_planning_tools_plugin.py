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

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar

from qgis.core import QgsMessageLog, Qgis

from qgis.gui import QgisInterface

from typing import List

import os

class CellPlanningTools():

    PLUGIN_NAME: str = 'Cell Planning Tools'
    def __init__(self, interface: QgisInterface) -> None:
        self.interface: QgisInterface = interface
        self.plugin_directory: str = os.path.dirname(__file__)
        self.action: QAction = None
        self.toolbar: QToolBar = None
        self.called: bool = False
        return
    
    def initGui(self) -> None:
        self.toolbar: QToolBar = self.interface.addToolBar(self.PLUGIN_NAME)
        self.toolbar.setToolTip(self.PLUGIN_NAME)

        Icon = QIcon(os.path.join(self.plugin_directory,
                     "resources","icons","draw_sectors.png"))
        self.action = QAction(Icon, "Draw Sectors")
        self.action.triggered.connect(self.run)

        self.toolbar.addAction(self.action)
        self.interface.addPluginToMenu(self.PLUGIN_NAME, self.action)
        return
    
    def unload(self) -> None:
        self.interface.removePluginMenu(self.PLUGIN_NAME, self.action)
        self.interface.removeToolBarIcon(self.action)
        del self.action
        del self.toolbar
        return

    def run(self) -> None:
        if not self.called:
            QgsMessageLog.logMessage(
                "First time calling drawSectors()", 
                self.PLUGIN_NAME, 
                level=Qgis.Info)
            self.called = True
        
        QgsMessageLog.logMessage(
            "Calling drawSectors()",
            self.PLUGIN_NAME, 
            level=Qgis.Info) 
        
        return