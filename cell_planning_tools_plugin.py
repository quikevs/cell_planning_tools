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

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QToolBar

from qgis.gui import QgisInterface

from typing import List

import os

from .utils import log

class cell_planning_tools(object):

    PLUGIN_NAME: str = '&Cell Planning Tools'
    
    def __init__(self, Interface: QgisInterface) -> None:
        
        self.Interface: QgisInterface = Interface 
        self.PluginDirectory: str = os.path.dirname(__file__)
        self.ResourcesDirectory: str = os.path.join(
            self.PluginDirectory,"resources")

        self.Actions: List[QAction] = []
        
        self.Toolbar: QToolBar = self.Interface.addToolBar(self.PLUGIN_NAME)
        self.Toolbar.setObjectName(self.PLUGIN_NAME)

        self.FirstStart: bool = None
        return

    def initGui(self) -> None:
        IconPath: str = os.path.join(self.ResourcesDirectory, 
                                "icons", "sectors.png")

        Action: QAction = QAction(QIcon(IconPath), 
                         self.PLUGIN_NAME, self.Interface.mainWindow())
        Action.triggered.connect(self.run)
        Action.setEnabled(True)

        self.Toolbar.addAction(Action)
        self.Interface.addPluginToMenu(self.PLUGIN_NAME, Action)
        self.Actions.append(Action)
        
        self.FirstStart: bool = True
        return

    def unload(self) -> None:
        """Removes the plugin menu item and icon from QGIS GUI."""
        log.Critical("Dying")
        for Action in self.Actions:
            self.Interface.removePluginMenu(self.PLUGIN_NAME,Action)
            self.Interface.removeToolBarIcon(Action)
        log.Message("Died peacefully...")
        return

    def run(self) -> None:
        if self.FirstStart == True:
            self.FirstStart = False
            log.Success("First time calling run()")
        log.Information("call to run()")
        return