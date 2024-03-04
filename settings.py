import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QShowEvent
from PyQt5.QtWidgets import QWidget

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDialog

from qgis.core import QgsProject, QgsMapLayer, Qgis

from qgis.gui import QgisInterface


class Settings():
    def __init__(self) -> None:
        self.plugin_directory: str = os.path.dirname(__file__)
        self.plugin_name: str = "Cell Planning Tools"
        

settings = Settings()


    
