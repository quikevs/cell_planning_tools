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
    QPushButton,
    )

from typing import List, Dict, Union

from qgis.core import (
    QgsProject, 
    QgsMapLayer, 
    Qgis, 
    QgsFieldProxyModel, 
    QgsFields,
    QgsVectorLayer,
    QgsRasterLayer
    )

from qgis.gui import QgisInterface, QgsFieldExpressionWidget, QgsFieldComboBox


class Settings():
    plugin_directory: str = os.path.dirname(__file__)
    plugin_name: str = "Cell Planning Tools"
    def __init__(self) -> None:
        self.read()

    def read(self) -> None:
        qset = QSettings("Rockmedia", "CellPlanningTools")
        sectorLayer = \
            qset.value("/CellPlanningTools/sectorLayer", "Cell-sector")
        layers = QgsProject.instance().mapLayersByName(sectorLayer)
        self.sectorLayer = None
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.sectorLayer: QgsVectorLayer = layer
                break
        #RasterLists
        demList = qset.value("/CellPlanningTools/demList", "")
        self.demList = self.getRasterLayerList(demList)

        dsmList = qset.value("/CellPlanningTools/dsmList", "")
        self.dsmList = self.getRasterLayerList(dsmList)

        self.sensibility: float = \
            qset.value("/CellPlanningTools/sensibility", 1.5)
        self.upperSidelobeLimit: int = \
            qset.value("/CellPlanningTools/upperSidelobeLimit", 300_000)
        self.units: int = qset.value("/CellPlanningTools/units", 0)

        color: str = \
            qset.value("/CellPlanningTools/rubberBandColor", "#ffe57e")
        self.rubberBandColor: QColor = QColor(color)

        alpha: int = qset.value("/CellPlanningTools/rubberBandOpacity",
                                192)
        self.rubberBandColor.setAlpha(alpha)

        #Layer Field Map

        self.mapName: str = qset.value("/CellPlanningTools/mapName", "")
        self.mapAntennaHeight: str = \
            qset.value("/CellPlanningTools/mapAntennaHeight", "")
        self.mapAzimuth: str = qset.value("/CellPlanningTools/mapAzimuth", "")
        self.mapShift: str = qset.value("/CellPlanningTools/mapShift","")
        self.mapMTilt: str = qset.value("/CellPlanningTools/mapMTilt", "")
        self.mapETilt: str = qset.value("/CellPlanningTools/mapETilt", "")
        self.mapHWidth: str = qset.value("/CellPlanningTools/mapHWidth", "")
        self.mapVWidth: str = qset.value("/CellPlanningTools/mapVWidth", "")
        self.mapMinETilt: str = \
            qset.value("/CellPlanningTools/mapMinETilt", "")
        self.mapMaxETilt: str = \
            qset.value("/CellPlanningTools/mapMaxETilt", "")

        self.mapLock: str = \
            qset.value("/CellPlanningTools/mapLock", "")

        return
    
    def getRasterLayerList(self, nameList: str) -> List[QVariant]:
        result: List[QVariant] = []
        rasterList: List[QgsRasterLayer] = self.rasterListFromNames(nameList)
        for raster in rasterList:
            result.append(QVariant({
                "name": raster.name(),
                "layer": raster
            }))
        return result
    
    def rasterList(self, variantList: List[QVariant]) -> List[QgsRasterLayer]:
        result: List[QgsRasterLayer] = []
        for name in variantList:
            result.append(name.value()['layer'])
        return result
    
    def rasterListFromNames(self, nameList: str) -> List[QgsRasterLayer]:
        result: List[QgsRasterLayer] = []
        names: List[str] = nameList.split(",")
        for name in names:
            if name == '':
                continue
            layers = QgsProject.instance().mapLayersByName(name)
            if len(layers) >= 1:
                layer = layers[0]
                if layer.type() != Qgis.LayerType.Raster:
                    continue
                result.append(layer)
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
        #self.simModel.itemChanged.connect(self.selectionChanged)
        #self.simModel.rowsRemoved.connect(self.selectionChanged)
        self.selectedItems: List[QVariant] = []
        return
    
    #def selectionChanged():
    #    pass
    
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
                  selected: bool, updateExistingTilte: bool)-> None:
        
        for i in range(self.simModel.rowCount()):
            if self.simModel.item(i).data(Qt.ItemDataRole.UserRole) == value:
                if updateExistingTilte:
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
    settings.plugin_directory,"resources","ui","map_layer.ui"))

class MapLayerFields(QDialog, FORM_CLASS):
    def __init__(self, layer: QgsMapLayer, fieldMap: Dict[str, str], 
                 interface:QgisInterface, parent: QWidget)->None:
        super().__init__(parent)
        self.interface: QgisInterface = interface
        self.layer :QgsVectorLayer = None
        self.setupUi(self)
        self.fieldWidgets: List[QgsFieldComboBox] = [
            self.wAzimuth,
            self.wHeight,
            self.wM_Tilt,
            self.wE_Tilt,
            
        ]
        self.fieldExpressionWidgets: List[QgsFieldExpressionWidget] = [
            self.wName,
            self.wLock,
            self.wShift,
            self.wH_Width,
            self.wV_Width,
            self.wMin_E_Tilt,
            self.wMax_E_Tilt
        ]
        self.fieldExpressionWidgets[0].setFilters(QgsFieldProxyModel.Filter.String)
        self.fieldExpressionWidgets[1].setFilters(QgsFieldProxyModel.Filter.String)
        [fieldWidget.setFilters(QgsFieldProxyModel.Filter.Numeric) for fieldWidget in self.fieldWidgets]
        [fieldWidget.setFilters(QgsFieldProxyModel.Filter.Numeric) for fieldWidget in self.fieldExpressionWidgets[2:]]
        self.lbError.setText("")
        self.setLayer(layer)
        self.setFields(fieldMap)
        return
    
    def setLayer(self, layer: QgsVectorLayer) -> None:
        self.layer = layer
        for fieldExpression in self.fieldExpressionWidgets:
            fieldExpression.setLayer(self.layer if self.layer else None)
        for fieldExpression in self.fieldWidgets:
            fieldExpression.setLayer(self.layer if self.layer else None)    
        return
    
    def setFields(self, fieldMap: Dict[str,str]) -> None:
        #name
        fields: List[str] = self.layer.fields().names()
        if fieldMap['name'] in fields:
            # name previoulsy stored in Memory
            self.wName.setExpression(fieldMap['name'])      
        if fieldMap['antenaHeight'] in fields:
            # name previoulsy stored in Memory
            self.wHeight.setField(fieldMap['antenaHeight'])
        if fieldMap['azimuth'] in fields:
            # name previoulsy stored in Memory
            self.wAzimuth.setField(fieldMap['azimuth'])
        if fieldMap['shift'] in fields:
            # name previoulsy stored in Memory
            self.wShift.setExpression(fieldMap['shift'])
        if fieldMap['mDowntilt'] in fields:
            # name previoulsy stored in Memory
            self.wM_Tilt.setField(fieldMap['mDowntilt'])
        if fieldMap['eDowntilt'] in fields:
            # name previoulsy stored in Memory
            self.wE_Tilt.setField(fieldMap['eDowntilt'])            
        if fieldMap['hWidth'] in fields:
            # name previoulsy stored in Memory
            self.wH_Width.setExpression(fieldMap['hWidth'])
        if fieldMap['vWidth'] in fields:
            # name previoulsy stored in Memory
            self.wV_Width.setExpression(fieldMap['vWidth'])
        if fieldMap['minEDowntilt'] in fields:
            # name previoulsy stored in Memory
            self.wMin_E_Tilt.setExpression(fieldMap['minEDowntilt'])
        if fieldMap['maxEDowntilt'] in fields:
            # name previoulsy stored in Memory
            self.wMax_E_Tilt.setExpression(fieldMap['maxEDowntilt'])
        if fieldMap['lock'] in fields:
            self.wLock.setExpression(fieldMap['lock'])
       
        return
    
    def accept(self) -> None:
        self.lbError.setText("")
        isValid = True
        for field in self.fieldExpressionWidgets:
            if field.isValidExpression():
                continue
            else:
                isValid = False

        for field in self.fieldWidgets:
            if field.currentField() != "":
                continue
            else:
                isValid = False
        
        if isValid:
            #save and commit changes
            qset = QSettings("Rockmedia", "CellPlanningTools")
            qset.setValue(
                "/CellPlanningTools/mapName", self.wName.currentText())
            qset.setValue(
                "/CellPlanningTools/mapAntennaHeight", self.wHeight.currentText())
            qset.setValue(
                "/CellPlanningTools/mapAzimuth", self.wAzimuth.currentText())
            qset.setValue(
                "/CellPlanningTools/mapShift",self.wShift.currentText())
            qset.setValue(
                "/CellPlanningTools/mapMTilt", self.wM_Tilt.currentText())
            qset.setValue(
                "/CellPlanningTools/mapETilt", self.wE_Tilt.currentText())
            qset.setValue(
                "/CellPlanningTools/mapHWidth", self.wH_Width.currentText())
            qset.setValue(
                "/CellPlanningTools/mapVWidth", self.wV_Width.currentText())
            qset.setValue(
                "/CellPlanningTools/mapMinETilt", self.wMin_E_Tilt.currentText())
            qset.setValue(
                "/CellPlanningTools/mapMaxETilt", self.wMax_E_Tilt.currentText())
            qset.setValue(
                "/CellPlanningTools/mapLock", self.wLock.currentText())
            
            settings.read()
            self.close()
            pass
        
        else:
            self.lbError.setText("Error. Please check all Fields before continue")

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

        self.mapLayersDialog: MapLayerFields = None
        
        self.tbMapLayerFields.setEnabled(False)
        self.tbMapLayerFields.clicked.connect(self.mapLayers)
        self.cbSectorLayer.layerChanged.connect(self.layerChanged)
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

        color = self.colorButton.color().name()
        qset.setValue("/CellPlanningTools/rubberBandColor", color)

        alpha = int(self.opacityWidget.opacity() * 255)
        qset.setValue("/CellPlanningTools/rubberBandOpacity", alpha)

        settings.read()
        self.close()
        return

    def showEvent(self, a0: QShowEvent) -> None:
        settings.read()
        self.cbSectorLayer.setLayer(settings.sectorLayer)
        self.sbSensibility.setValue(float(settings.sensibility))
        self.sbSidelobLimit.setValue(float(settings.upperSidelobeLimit))
        self.cbUnits.setCurrentIndex(int(settings.units))

        self.leDem.setText(
            f'{len(settings.demList)} inputs selected'
        )
        self.leDsm.setText(
            f'{len(settings.dsmList)} inputs selected'
        )

        self.colorButton.setColor(
            QColor(settings.rubberBandColor))

        self.opacityWidget.setOpacity(
            settings.rubberBandColor.alpha()/255)

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
            self.getAvailableLayers(), settings.demList, self)
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
            self.getAvailableLayers(), settings.dsmList, self)
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
    
    def readFields(self) -> Dict[str, str]:
        settings.read()
        fieldMap = {
            'name': settings.mapName,
            'antenaHeight': settings.mapAntennaHeight,
            'azimuth':settings.mapAzimuth,
            'shift': settings.mapShift,
            'mDowntilt': settings.mapMTilt,
            'eDowntilt': settings.mapETilt,
            'hWidth': settings.mapHWidth,
            'vWidth': settings.mapVWidth,
            'minEDowntilt': settings.mapMinETilt,
            'maxEDowntilt': settings.mapMaxETilt,
            'lock': settings.mapLock,
        }
        return fieldMap
    
    def mapLayers(self):
        layer = self.cbSectorLayer.currentLayer()
        fields = self.readFields()
        if self.mapLayersDialog == None:
        
            self.mapLayersDialog = MapLayerFields(
                layer,                                              
                fields,
                self.interface, self)
        else:
            self.mapLayersDialog.setLayer(layer)
            self.mapLayersDialog.setFields(fields)
        self.mapLayersDialog.show()
        return
    
    def layerChanged(self, layer: QgsMapLayer):
        if self.cbSectorLayer.currentLayer():
            self.tbMapLayerFields.setEnabled(True)
        else:
            self.tbMapLayerFields.setEnabled(False)
        return