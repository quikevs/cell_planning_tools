import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QShowEvent
from PyQt5.QtWidgets import QWidget

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings, Qt, QModelIndex, QVariant
from qgis.PyQt.QtGui import QColor, QStandardItem, QStandardItemModel
from qgis.PyQt.QtWidgets import (
    QAbstractItemView, 
    QDialog, 
    QDialogButtonBox,
    QListView,
    QPushButton,
    )

from typing import List

from qgis.core import QgsProject, QgsMapLayer, Qgis, QgsRasterLayer

from qgis.gui import QgisInterface

from .utils import logMessage

class Settings():
    plugin_directory: str = os.path.dirname(__file__)
    plugin_name: str = "Cell Planning Tools"
    def __init__(self) -> None:
        pass

    def read(self):
        qset = QSettings("Rockmedia", "CellPlanningTools")
        sectorLayer = \
            qset.value("/CellPlanningTools/sectorLayer", "Cell-sector")
        layers = QgsProject.instance().mapLayersByName(sectorLayer)
        self.sectorLayer = None
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.sectorLayer: QgsMapLayer = layer
                break
        #RasterLists
        demList = qset.value("/CellPlanningTools/demList", "")
        self.demList = self.layerListfromNames(demList)

        dsmList = qset.value("/CellPlanningTools/dsmList", "")
        self.dsmList = self.layerListfromNames(dsmList)

        self.sensibility: float = \
            qset.value("/CellPlanningTools/sensibility", 1.5)
        self.upperSidelobeLimit: int = \
            qset.value("/CellPlanningTools/upperSidelobeLimit", 300_000)
        self.units: int = qset.value("/CellPlanningTools/units", 0)




        return

    def layerListfromNames(self, nameList: str) -> List[QVariant]:
        result: List[QVariant] = []
        names: List[str] = nameList.split(",")
        for name in names:
            layers = QgsProject.instance().mapLayersByName(name)
            if len(layers) >= 1:
                layer = layers[0] #get first
                if layer.type() != Qgis.LayerType.Raster:
                    continue
                result.append(
                    QVariant({
                        "name": layer.name(),
                        "layer": layer}))
        return result


settings = Settings()

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    settings.plugin_directory, 'resources', 'ui', 'MultipleSelection.ui'))

class MultipleSelection(QDialog, FORM_CLASS):
    def __init__(self, 
                 avalableOptions: List[QVariant],
                 selectedOptions: List[QVariant],
                 parent: QWidget) -> None:
        super().__init__(parent)
        
        self.setupUi(self)

        self.simModel: QStandardItemModel = None
        
        self.lvSelection.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.lvSelection.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lvSelection.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove)
        
        self.pbSelectAll = QPushButton("Select All")
        self.buttonBox.addButton(
            self.pbSelectAll, 
            QDialogButtonBox.ButtonRole.ActionRole)
        self.pbSelectAll.clicked.connect(self.selectAll)
        
        self.pbClear = QPushButton("Clear Selection")
        self.buttonBox.addButton(
            self.pbClear, 
            QDialogButtonBox.ButtonRole.ActionRole)
        self.pbClear.clicked.connect(self.unselectAll)
        
        self.pbToogle = QPushButton("Toogle Selection")
        self.buttonBox.addButton(
            self.pbToogle, 
            QDialogButtonBox.ButtonRole.ActionRole)
        self.pbToogle.clicked.connect(self.toogleSelection)

#        self.buttonBox.accepted.connect(self.acceptClicked)

        self.populateList(avalableOptions, selectedOptions)
        self.simModel.itemChanged.connect(self.selectionChanged)
        self.simModel.rowsRemoved.connect(self.selectionChanged)
        self.selectedItems: List[QVariant] = []
    
    def selectAll(self) -> None:
        items: List[QStandardItem] = self.currentItems()
        for item in items:
            item.setCheckState(Qt.CheckState.Checked)
        return
    
    def unselectAll(self) -> None:
        items: List[QStandardItem] = self.currentItems()
        for item in items:
            item.setCheckState(Qt.CheckState.Unchecked)
        return
    
    def toogleSelection(self) -> None:
        items: List[QStandardItem] = self.currentItems()
        for item in items:
            item.setCheckState(Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked  else Qt.CheckState.Unchecked)
        return


    def currentItems(self) -> List[QStandardItem]:
        items: List[QStandardItem] = []
        selection: List[QModelIndex] = \
            self.lvSelection.selectionModel().selectedIndexes()
        if len(selection) > 1:
            for index in selection:
                items.append(self.simModel.itemFromIndex(index))
        else:
            for i in range(self.simModel.rowCount()):
                items.append(self.simModel.item(i))
        return items
    
    def populateList(
            self,
            availableOptions: List[QVariant],
            selectedOptions: List[QVariant]) -> None:
        self.simModel = QStandardItemModel(self)
        remainingOptions = availableOptions
        for option in selectedOptions:
            self.addOption(option,True,True)
            remainingOptions.remove(option)
        for option in remainingOptions:
            self.addOption(option, False, True)
        
        self.lvSelection.setModel(self.simModel)
        return
    
    def selectedOptions(self) -> List[QVariant]:
        options: List[QVariant] = []
        for i in range(self.simModel.rowCount()):
            item = self.simModel.item(i)
            if not item:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                options.append(
                    QVariant(item.data(Qt.ItemDataRole.UserRole)))
                #Note: something about hasModelSources in QGIS Source Code
                # QGIS/src/gui/processing/qgsprocessingmultipleselectiondialog.cpp
        return options
    
    def addOption(self, 
                  value: QVariant, 
                  selected: bool, updateExistingTitle: bool)-> None:
        for i in range(self.simModel.rowCount()):
            if self.simModel.item(i).data(Qt.ItemDataRole.UserRole) == value:
                if updateExistingTitle:
                    self.simModel.item(i).setText(
                        f'{value.value()["name"]}')
                return
        
        item = QStandardItem(
            f'{value.value()["name"]}')
        item.setData(value, Qt.ItemDataRole.UserRole)
        item.setCheckState(
            Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
        item.setCheckable(True)
        item.setDropEnabled(False)
        self.simModel.appendRow(item)
        return

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    settings.plugin_directory, 'resources', 'ui', 'Settings.ui'))

class SettingsDialog(QDialog, FORM_CLASS):
    def __init__(self, interface, 
                 parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.interface: QgisInterface = interface
        settings.read()
        self.cbSectorLayer.setFilters(
            Qgis.LayerFilters(Qgis.LayerFilter.PolygonLayer))
        self.sbSensibility.setMinimum(0.5)
        self.sbSensibility.setSingleStep(0.5)

        self.sbSidelobLimit.setMinimum(0)
        self.sbSidelobLimit.setSingleStep(100)

        self.tbDem.clicked.connect(self.selectDemLayers)
        self.tbDsm.clicked.connect(self.selectDsmLayers)

        self.selectDemLayersDialog: MultipleSelection = None
        self.selectDsmLayersDialog: MultipleSelection = None

        self.demSelectedLayers: List[QVariant] = []
        self.dsmSelectedLayers: List[QVariant] = []
        return
    
    def accept(self) -> None:
        qset = QSettings("Rockmedia", "CellPlanningTools")
        sectorLayer: QgsMapLayer = self.cbSectorLayer.currentLayer()
        if sectorLayer:
            qset.setValue(
                "/CellPlanningTools/sectorLayer", sectorLayer.name())
            
        
        demList: str = ','.join(
            [variant.value()['name'] for variant in self.demSelectedLayers]
        )
        qset.setValue("/CellPlanningTools/demList", demList)

        dsmList: str = ",".join(
            [variant.value()['name'] for variant in self.dsmSelectedLayers]
        )
        qset.setValue("/CellPlanningTools/dsmList", dsmList)
            
        sensibility = self.sbSensibility.value()
        qset.setValue("/CellPlanningTools/sensibility", sensibility)

        upperSidelobeLimit = self.sbSidelobLimit.value()
        qset.setValue("/CellPlanningTools/upperSidelobeLimit", 
                      upperSidelobeLimit)
        
        units = self.cbUnits.currentIndex()
        qset.setValue("/CellPlanningTools/units", units)

        

        settings.read()
        self.close()
        return

    def showEvent(self, a0: QShowEvent) -> None:
        settings.read()
        self.cbSectorLayer.setLayer(settings.sectorLayer)

        
        return
    
    def getAvailableLayers(self) -> List[QVariant]:
        rasterLayers: List[QVariant] = []
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == Qgis.LayerType.Raster:
                data = {
                    'name': layer.name(),
                    'layer': layer
                }
                variant = QVariant(data)
                rasterLayers.append(variant)
        return rasterLayers
    
    def selectDemLayers(self) -> None:
        
        self.selectDemLayersDialog = MultipleSelection(
            self.getAvailableLayers(), self.demSelectedLayers, self)
        self.selectDemLayersDialog.buttonBox.accepted.connect(self.updateDemLayers)
        self.selectDemLayersDialog.show()
        return
    
    def updateDemLayers(self) -> None:
        self.selectDemLayersDialog.selectedItems = \
            self.selectDemLayersDialog.selectedOptions()
        self.demSelectedLayers = self.selectDemLayersDialog.selectedItems
        self.leDem.setText(
            f'{len(self.demSelectedLayers)} inputs selected'
        )
        self.selectDemLayersDialog.close()
        
        return

    def selectDsmLayers(self) -> None:
        self.selectDsmLayersDialog = MultipleSelection(
            self.getAvailableLayers(), self.dsmSelectedLayers, self)
        self.selectDsmLayersDialog.buttonBox.accepted.connect(
            self.updateDsmLayers)
        self.selectDsmLayersDialog.show()
        return
    
    def updateDsmLayers(self) -> None:
        self.selectDsmLayersDialog.selectedItems = \
            self.selectDsmLayersDialog.selectedOptions()
        self.dsmSelectedLayers = self.selectDsmLayersDialog.selectedItems
        self.leDsm.setText(
            f'{len(self.dsmSelectedLayers)} inputs selected'
        )
        self.selectDsmLayersDialog.close()
        
        return
    


