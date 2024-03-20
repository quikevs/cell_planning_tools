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
from typing import List, Dict

from qgis.PyQt import uic
from qgis.PyQt.QtCore import (
    QModelIndex,
    QSettings,
    Qt,
    QVariant,
    pyqtSignal
    )

from qgis.PyQt.QtGui import (
    QColor,
    QShowEvent,
    QStandardItem,
    QStandardItemModel,
    )

from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QWidget,
    )

from qgis.core import (
    QgsProject,
    QgsMapLayer,
    Qgis,
    QgsFieldProxyModel,
    QgsVectorLayer,
    QgsRasterLayer,
    )

from qgis.gui import (
    QgisInterface,
    QgsFieldExpressionWidget,
    QgsFieldComboBox,
    )

from threading import Lock


class SettingsMeta(type):
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwds):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwds)
                cls._instances[cls] = instance
            return cls._instances[cls]


class Settings(metaclass=SettingsMeta):
    plugin_directory: str = os.path.dirname(__file__)
    plugin_name: str = "Cell Planning Tools"

    def __init__(self) -> None:
        self.read()
        return

    def read(self) -> None:
        qset: QSettings = QSettings("Rockmedia", "CellPlanningTools")
        sectorLayer: str = \
            qset.value("/CellPlanningTools/sectorLayer", "Cell-sector")
        layers: List[QgsMapLayer] = \
            QgsProject.instance().mapLayersByName(sectorLayer)
        self.sectorLayer: QgsVectorLayer = None
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.sectorLayer: QgsVectorLayer = layer
                break
        # RasterLists
        demList = qset.value("/CellPlanningTools/demList", "")
        self.demList: List[QgsRasterLayer] = None
        self.demList = self.getRasterLayers(demList)

        dsmList = qset.value("/CellPlanningTools/dsmList", "")
        self.dsmList: List[QgsRasterLayer] = None
        self.dsmList = self.getRasterLayers(dsmList)

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

        color: str = \
            qset.value("/CellPlanningTools/rubberBandColor2", "#efe57e")
        self.rubberBandColor2: QColor = QColor(color)

        alpha: int = qset.value("/CellPlanningTools/rubberBandOpacity2",
                                192)
        self.rubberBandColor2.setAlpha(alpha)

        # Layer Field Map

        self.mapName: str = \
            qset.value("/CellPlanningTools/mapName", "sector_name")
        self.mapAntennaHeight: str = \
            qset.value("/CellPlanningTools/mapAntennaHeight",
                       "antenna_height")
        self.mapAzimuth: str = \
            qset.value("/CellPlanningTools/mapAzimuth", "azimuth")
        self.mapShift: str = \
            qset.value("/CellPlanningTools/mapShift",
                       "h_beam_center_direction")
        self.mapMTilt: str = \
            qset.value("/CellPlanningTools/mapMTilt", "m_tilt")
        self.mapETilt: str = \
            qset.value("/CellPlanningTools/mapETilt", "e_tilt")
        self.mapHWidth: str = \
            qset.value("/CellPlanningTools/mapHWidth", "h_width")
        self.mapVWidth: str = \
            qset.value("/CellPlanningTools/mapVWidth", "v_width")
        self.mapMinETilt: str = \
            qset.value("/CellPlanningTools/mapMinETilt", "min_e_tilt")
        self.mapMaxETilt: str = \
            qset.value("/CellPlanningTools/mapMaxETilt", "max_e_tilt")
        self.mapLock: str = \
            qset.value("/CellPlanningTools/mapLock", "lock")
        return

    def getRasterLayers(self, names: str) -> List[QgsRasterLayer]:
        result: List[QgsRasterLayer] = []
        for name in names.split(","):
            if name == '':
                continue
            layers = QgsProject.instance().mapLayersByName(name)
            if len(layers) >= 1:
                layer = layers[0]
                if layer.type() != Qgis.LayerType.Raster:
                    continue
                else:
                    result.append(layer)
            else:
                continue
        return result

    def packRasterLayers(
            self,
            rasterList: List[QgsRasterLayer]
            ) -> List[QVariant]:
        result: List[QVariant] = []
        if len(rasterList) > 0:
            for raster in rasterList:
                result.append(QVariant({
                    "name": raster.name(),
                    "layer": raster,
                }))
        return result


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    Settings().plugin_directory, 'resources', 'ui', 'MultipleSelection.ui'))


class MultipleSelection(QDialog, FORM_CLASS):
    def __init__(
            self,
            avalableOptions: List[QVariant],
            selectedOptions: List[QVariant],
            parent: QWidget
            ) -> None:
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
        self.populateList(avalableOptions, selectedOptions)
        self.selectedItems: List[QVariant] = []
        return

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
            item.setCheckState(
                Qt.CheckState.Checked
                if item.checkState() == Qt.CheckState.Unchecked
                else Qt.CheckState.Unchecked)
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
            selectedOptions: List[QVariant]
            ) -> None:
        self.simModel = QStandardItemModel(self)
        remainingOptions = availableOptions
        for option in selectedOptions:
            self.addOption(option, True, True)
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
        return options

    def addOption(
            self,
            value: QVariant,
            selected: bool, updateExistingTilte: bool
            ) -> None:
        for i in range(self.simModel.rowCount()):
            if self.simModel.item(i).data(Qt.ItemDataRole.UserRole) == value:
                if updateExistingTilte:
                    self.simModel.item(i).setText(
                        f'{value.value()["name"]}')
                return
        item = QStandardItem(f'{value.value()["name"]}')
        item.setData(value, Qt.ItemDataRole.UserRole)
        item.setCheckState(
            Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
        item.setCheckable(True)
        item.setDropEnabled(False)
        self.simModel.appendRow(item)
        return


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    Settings().plugin_directory, "resources", "ui", "map_layer.ui"))


class MapLayerFields(QDialog, FORM_CLASS):
    def __init__(
            self,
            layer: QgsMapLayer,
            fieldMap: Dict[str, str],
            interface: QgisInterface,
            parent: QWidget
            ) -> None:
        super().__init__(parent)
        self.interface: QgisInterface = interface
        self.layer: QgsVectorLayer = None
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
            self.wMax_E_Tilt,
            ]
        self.fieldExpressionWidgets[0].setFilters(
            QgsFieldProxyModel.Filter.String)
        self.fieldExpressionWidgets[1].setFilters(
            QgsFieldProxyModel.Filter.String)
        [fieldWidget.setFilters(QgsFieldProxyModel.Filter.Numeric)
         for fieldWidget in self.fieldWidgets]
        [fieldWidget.setFilters(QgsFieldProxyModel.Filter.Numeric)
         for fieldWidget in self.fieldExpressionWidgets[2:]]
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

    def setFields(self, fieldMap: Dict[str, str]) -> None:
        fields: List[str] = self.layer.fields().names()
        if fieldMap['name'] in fields:
            # Name matching a field on the layer
            self.wName.setField(fieldMap['name'])
        else:
            self.wName.setExpression(fieldMap['name'])
            if not self.wName.isValidExpression:
                self.wName.setExpression(None)
            pass
        if fieldMap['shift'] in fields:
            self.wShift.setField(fieldMap['shift'])
        else:
            # no Matching, trying expresison
            self.wShift.setExpression(fieldMap['shift'])
            if not self.wShift.isValidExpression():
                self.wShift.setExpression(None)

        if fieldMap['minEDowntilt'] in fields:
            self.wMin_E_Tilt.setField(fieldMap['minEDowntilt'])
        else:
            self.wMin_E_Tilt.setExpression(fieldMap['minEDowntilt'])
            if not self.wMin_E_Tilt.isValidExpression():
                self.wMin_E_Tilt.setExpression(None)

        if fieldMap['maxEDowntilt'] in fields:
            self.wMax_E_Tilt.setField(fieldMap['maxEDowntilt'])
        else:
            self.wMax_E_Tilt.setExpression(fieldMap['maxEDowntilt'])
            if not self.wMax_E_Tilt.isValidExpression():
                self.wMax_E_Tilt.setExpression(None)

        if fieldMap['lock'] in fields:
            self.wLock.setField(fieldMap['lock'])
        else:
            self.wLock.setExpression(fieldMap['lock'])
            if not self.wLock.isValidExpression():
                self.wLock.setExpression(None)

        if fieldMap['antenaHeight'] in fields:
            self.wHeight.setField(fieldMap['antenaHeight'])
        if fieldMap['azimuth'] in fields:
            self.wAzimuth.setField(fieldMap['azimuth'])
        if fieldMap['mDowntilt'] in fields:
            self.wM_Tilt.setField(fieldMap['mDowntilt'])
        if fieldMap['eDowntilt'] in fields:
            self.wE_Tilt.setField(fieldMap['eDowntilt'])
        if fieldMap['hWidth'] in fields:
            self.wH_Width.setExpression(fieldMap['hWidth'])
        if fieldMap['vWidth'] in fields:
            self.wV_Width.setExpression(fieldMap['vWidth'])
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
            qset = QSettings("Rockmedia", "CellPlanningTools")
            qset.setValue(
                "/CellPlanningTools/mapName",
                self.wName.currentText())
            qset.setValue(
                "/CellPlanningTools/mapAntennaHeight",
                self.wHeight.currentText())
            qset.setValue(
                "/CellPlanningTools/mapAzimuth", self.wAzimuth.currentText())
            qset.setValue(
                "/CellPlanningTools/mapShift", self.wShift.currentText())
            qset.setValue(
                "/CellPlanningTools/mapMTilt", self.wM_Tilt.currentText())
            qset.setValue(
                "/CellPlanningTools/mapETilt", self.wE_Tilt.currentText())
            qset.setValue(
                "/CellPlanningTools/mapHWidth", self.wH_Width.currentText())
            qset.setValue(
                "/CellPlanningTools/mapVWidth", self.wV_Width.currentText())
            qset.setValue(
                "/CellPlanningTools/mapMinETilt",
                self.wMin_E_Tilt.currentText())
            qset.setValue(
                "/CellPlanningTools/mapMaxETilt",
                self.wMax_E_Tilt.currentText())
            qset.setValue(
                "/CellPlanningTools/mapLock", self.wLock.currentText())
            Settings().read()
            self.close()
            pass

        else:
            self.lbError.setText(
                "Error. Please check all Fields before continue")
        return


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    Settings().plugin_directory, 'resources', 'ui', 'Settings.ui'))


class SettingsDialog(QDialog, FORM_CLASS):
    settingsUpdated = pyqtSignal()

    def __init__(
            self,
            interface,
            parent: QWidget
            ) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.interface: QgisInterface = interface
        self.settings = Settings()
        self.settings.read()
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
        self.status.setText("Saving...")
        sectorLayer: QgsMapLayer = self.cbSectorLayer.currentLayer()
        if sectorLayer:
            qset.setValue(
                "/CellPlanningTools/sectorLayer", sectorLayer.name())
        demList: str = ','.join(
            [variant.value()['name'] for variant in self.demSelectedLayers])
        qset.setValue("/CellPlanningTools/demList", demList)

        dsmList: str = ",".join(
            [variant.value()['name'] for variant in self.dsmSelectedLayers])
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

        secondColor = self.secondColorButton.color().name()
        qset.setValue("/CellPlanningTools/rubberBandColor2", secondColor)
        secondAlpha = int(self.secondOpacityWidget.opacity() * 255)
        qset.setValue("/CellPlanningTools/rubberBandOpacity2", secondAlpha)

        self.settings.read()
        self.settingsUpdated.emit()
        self.close()
        self.status.setText('')
        return

    def showEvent(self, a0: QShowEvent) -> None:
        self.settings.read()
        self.cbSectorLayer.setLayer(self.settings.sectorLayer)
        if self.cbSectorLayer.currentLayer():
            self.tbMapLayerFields.setEnabled(True)
        self.sbSensibility.setValue(float(self.settings.sensibility))
        self.sbSidelobLimit.setValue(self.settings.upperSidelobeLimit)
        self.cbUnits.setCurrentIndex(int(self.settings.units))

        self.leDem.setText(
            f'{len(self.settings.demList)} inputs selected')
        self.leDsm.setText(
            f'{len(self.settings.dsmList)} inputs selected')

        self.colorButton.setColor(
            QColor(self.settings.rubberBandColor))

        self.opacityWidget.setOpacity(
            self.settings.rubberBandColor.alpha()/255)
        
        self.secondColorButton.setColor(
            QColor(self.settings.rubberBandColor2))

        self.secondOpacityWidget.setOpacity(
            self.settings.rubberBandColor2.alpha()/255)

        return

    def getAvailableLayers(self) -> List[QVariant]:
        rasterLayers: List[QVariant] = []
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == Qgis.LayerType.Raster:
                data = {
                    'name': layer.name(),
                    'layer': layer,
                    }
                variant = QVariant(data)
                rasterLayers.append(variant)
        return rasterLayers

    def selectDemLayers(self) -> None:
        if not self.selectDemLayersDialog:
            self.selectDemLayersDialog = \
                MultipleSelection(
                    self.getAvailableLayers(),
                    self.settings.packRasterLayers(self.settings.demList),
                    self)
            self.selectDemLayersDialog.buttonBox.accepted.connect(
                self.updateDemLayers)
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
        self.selectDemLayersDialog = None
        return

    def selectDsmLayers(self) -> None:
        if not self.selectDsmLayersDialog:
            self.selectDsmLayersDialog = \
                MultipleSelection(
                    self.getAvailableLayers(),
                    self.settings.packRasterLayers(self.settings.dsmList),
                    self)
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
        self.selectDsmLayersDialog = None
        return

    def readFields(self) -> Dict[str, str]:
        self.settings.read()
        fieldMap = {
            'name': self.settings.mapName,
            'antenaHeight': self.settings.mapAntennaHeight,
            'azimuth': self.settings.mapAzimuth,
            'shift': self.settings.mapShift,
            'mDowntilt': self.settings.mapMTilt,
            'eDowntilt': self.settings.mapETilt,
            'hWidth': self.settings.mapHWidth,
            'vWidth': self.settings.mapVWidth,
            'minEDowntilt': self.settings.mapMinETilt,
            'maxEDowntilt': self.settings.mapMaxETilt,
            'lock': self.settings.mapLock,
            }
        return fieldMap

    def mapLayers(self):
        layer = self.cbSectorLayer.currentLayer()
        fields = self.readFields()
        if self.mapLayersDialog is None:
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

    def close(self):
        super().close()
        self.mapLayersDialog = None
        self.selectDemLayersDialog = None
        self.selectDsmLayersDialog = None
