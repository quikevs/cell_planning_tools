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

import os

from qgis.PyQt.QtGui import QIcon

from qgis.core import QgsProcessingProvider

from .settings import Settings
from .processing_draw_sectors import DrawSectors
from .processing_overlap_report import OverlapReport


class CallPlanningToolsProcessing(QgsProcessingProvider):
    settings = Settings()
    
    def __init__(self) -> None:
        QgsProcessingProvider.__init__(self)
        return

    def loadAlgorithms(self) -> None:
        self.addAlgorithm(DrawSectors())
        self.addAlgorithm(OverlapReport())
        return

    def unload(self) -> None:
        QgsProcessingProvider.unload(self)
        return

    def id(self) -> str:
        return "cellplanningtools"

    def name(Self) -> str:
        return "Cell Planning Tools"

    def longName(self) -> str:
        return self.name()

    def icon(self) -> QIcon:
        return QIcon(
            os.path.join(
                self.settings.plugin_directory,
                "resources", "icons", "cellplanningtools.png"
            )
        )
