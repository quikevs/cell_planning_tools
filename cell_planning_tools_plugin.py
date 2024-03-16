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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar

from qgis.core import (
    QgsApplication, 
    QgsProcessingProvider
    )

from qgis import processing

from qgis.gui import QgisInterface

from typing import List

import os

from .cell_planning_tools_processing import CallPlanningToolsProcessing
from .settings import settings, SettingsDialog
from .alterSector import AlterSector


class CellPlanningTools():

    PLUGIN_NAME: str = 'Cell Planning Tools'
    def __init__(self, interface: QgisInterface) -> None:
        self.interface: QgisInterface = interface
        self.actions: List[QAction] = []
        self.toolbar: QToolBar = None
        self.called: bool = False

        self.settingsDialog: SettingsDialog = \
            SettingsDialog(interface, interface.mainWindow())
        
        self.alterSectorDialog: AlterSector = \
            AlterSector(interface, self, interface.mainWindow())

        self.provider: QgsProcessingProvider = CallPlanningToolsProcessing()
        return
    
    def registerAction(
            self, icon: QIcon, text: str, callback: callable,
            addToToolbar: bool = True, addToMenu: bool = True) -> QAction:
        
        action: QAction = QAction(icon, text)
        action.triggered.connect(callback)
        if addToToolbar:
            self.toolbar.addAction(action)
        if addToMenu:
            self.interface.addPluginToMenu(settings.plugin_name, action)
        self.actions.append(action)    
        return action

    def initGui(self) -> None:
        self.toolbar: QToolBar = self.interface.addToolBar(self.PLUGIN_NAME)
        self.toolbar.setToolTip(self.PLUGIN_NAME)
        
        self.registerAction(
            QIcon(os.path.join(settings.plugin_directory,
                               "resources","icons","draw_sectors.png")),
            "Draw Sectos", self.drawSectors)
        
        self.registerAction(
            QIcon(os.path.join(settings.plugin_directory,
                               "resources","icons","alter_sector.png")),
            "Alter Sector", self.alterSector)
        
        self.registerAction(
            QIcon(':/images/themes/default/mActionOptions.svg'),
            "Settings", self.showSettings)

        QgsApplication.processingRegistry().addProvider(self.provider)
        return
    
    def unload(self) -> None:
        QgsApplication.processingRegistry().removeProvider(self.provider)

        for action in self.actions:
            self.interface.removePluginMenu(self.PLUGIN_NAME, action)
            self.interface.removeToolBarIcon(action)
        del self.toolbar
        del self.alterSectorDialog
        return

    def drawSectors(self) -> None:
        processing.execAlgorithmDialog('cellplanningtools:drawsector', {})
        return
    
    def alterSector(self) -> None:
        self.interface.addDockWidget(
            Qt.RightDockWidgetArea, self.alterSectorDialog)
        self.alterSectorDialog.setFocusPolicy(Qt.StrongFocus)

        self.alterSectorDialog.tbSettings.clicked.connect(self.showSettings)
        pass
    
    def showSettings(self) -> None:
        self.settingsDialog.show()
        return