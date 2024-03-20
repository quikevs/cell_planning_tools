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

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsMapLayer,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingFeedback,
    QgsProcessingFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameters,
    QgsProcessingParameterEnum,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProject,
    QgsProperty,
    QgsPropertyDefinition,
    QgsUnitTypes,
    QgsWkbTypes,
)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant

import os

from .settings import Settings
from .utils import EPSG4326, GeometryManager, Geometry
from .rf import CellSectorBuilder, CellSector
from .utils import logMessage

from typing import List, Dict, Any


class DrawSectors(QgsProcessingFeatureBasedAlgorithm):
    pNAME = "NAME"
    pDEM_LIST = "DEM_LIST"
    pDSM_LIST = "DSM_LIST"
    pSENSIBILITY = "SENSIBILITY"
    pAZIMUTH = "AZIMUTH"
    pSHIFT = "SHIFT"
    pANTENNA_HEIGHT = "ANTENNA_HEIGHT"
    pM_DOWNTILT = "M_DOWNTILT"
    pE_DOWNTILT = "E_DOWNTILT"
    pUNITS = "UNITS"
    pH_WIDTH = "H_WIDTH"
    pV_WIDTH = "V_WIDTH"
    pUS_LIMIT = "US_LIMIT"
    pDISTANCE_UNITS = "DISTANCE_UNITS"
    settings = Settings()

    def createInstance(self) -> QgsProcessingFeatureBasedAlgorithm:
        return DrawSectors()

    def icon(self) -> QIcon:
        return QIcon(
            os.path.join(
                self.settings.plugin_directory,
                "resources", "icons",
                "draw_sectors.png"
            )
        )

    def outputName(self) -> str:
        return "Cell-sector"

    def inputLayerTypes(self) -> List[int]:
        return [QgsProcessing.TypeVectorPoint]

    def outputWkbType(self, inputWkbType):
        return (QgsWkbTypes.Polygon)

    def outputFields(self, InputFields: QgsFields) -> QgsFields:
        InputFields.append(QgsField('distance', QVariant.Double))
        InputFields.append(QgsField('units', QVariant.String))
        InputFields.append(QgsField('lobe', QVariant.String))
        return (InputFields)

    def supportInPlaceEdit(self, Layer: QgsMapLayer) -> bool:
        return False

    def name(self) -> str:
        return 'drawsector'

    def displayName(self) -> str:
        return 'Draw Cell-sectors'

    def groupId(self) -> str:
        return 'geometrycalculator'

    def group(self) -> str:
        return 'Geometry Calculator'

    def initParameters(self, configuration: Dict[str, Any] = ...) -> None:

        # Cell Sector Name
        self.addParameter(
            QgsProcessingParameterField(
                self.pNAME,
                "Cell Sector name (Unique)",
                defaultValue=self.settings.mapName,
                allowMultiple=False,
                parentLayerParameterName='INPUT',
                optional=False,
            )
        )

        # Elevation Layer List
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.pDEM_LIST,
                "Digital Elevation Model (DEM) raster list",
                layerType=QgsProcessing.TypeRaster,
                defaultValue=self.settings.demList,
                optional=False,
            )
        )

        # Surface Layer List
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.pDSM_LIST,
                "Digital Surface Model (DSM) raster list (optional)",
                layerType=QgsProcessing.TypeRaster,
                defaultValue=self.settings.dsmList,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.pSENSIBILITY,
                "DEM/DSM Sensibility (in map units)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=self.settings.sensibility,
                optional=False,
                minValue=0.1,
            )
        )

        # Note: Azimuth

        self.addParameter(
            QgsProcessingParameterField(
                self.pAZIMUTH,
                "Azimuth",
                defaultValue=self.settings.mapAzimuth,
                parentLayerParameterName='INPUT',
                type=QgsProcessingParameterField.Numeric,
                allowMultiple=False,
                optional=False
                )
            )

        # Note: Azimuth Shift
        param = QgsProcessingParameterNumber(
            self.pSHIFT,
            'Azimuth Shift',
            QgsProcessingParameterNumber.Double,
            defaultValue=None,
            optional=False
        )
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(
            QgsPropertyDefinition(
                self.pSHIFT,
                'Azimuth Shift',
                QgsPropertyDefinition.Double
            )
        )
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterField(
                self.pANTENNA_HEIGHT,
                "Antenna Height",
                defaultValue=self.settings.mapAntennaHeight,
                parentLayerParameterName='INPUT',
                type=QgsProcessingParameterField.Numeric,
                allowMultiple=False,
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.pM_DOWNTILT,
                'Mechanical Downtilt',
                defaultValue=self.settings.mapMTilt,
                parentLayerParameterName='INPUT',
                type=QgsProcessingParameterField.Numeric,
                allowMultiple=False,
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.pE_DOWNTILT,
                'Electrical Downtilt',
                defaultValue=self.settings.mapETilt,
                parentLayerParameterName='INPUT',
                type=QgsProcessingParameterField.Numeric,
                allowMultiple=False,
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.pH_WIDTH,
                'Horizontal Beam Width',
                defaultValue=self.settings.mapHWidth,
                parentLayerParameterName='INPUT',
                type=QgsProcessingParameterField.Numeric,
                allowMultiple=False,
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.pV_WIDTH,
                'Vertical Beam Width',
                defaultValue=self.settings.mapHWidth,
                parentLayerParameterName='INPUT',
                type=QgsProcessingParameterField.Numeric,
                allowMultiple=False,
                optional=False
            )
        )

        # Upper sidelobe distance limit
        self.addParameter(
            QgsProcessingParameterNumber(
                self.pUS_LIMIT,
                "Upper sidelobe distance limit",
                QgsProcessingParameterNumber.Double,
                defaultValue=self.settings.upperSidelobeLimit,
                optional=False
            )
        )

        # Node: Resulting Distance Units
        self.addParameter(
            QgsProcessingParameterEnum(
                self.pUNITS,
                'Map units',
                options=["Meters", "Feet"],
                defaultValue=self.settings.units,
                optional=False)
        )
        return

    def prepareAlgorithm(self,
                         parameters: Dict[str, Any],
                         context: QgsProcessingContext,
                         feedback: QgsProcessingFeedback) -> bool:
        source: QgsProcessingFeatureSource = \
              self.parameterAsSource(
                  parameters, 'INPUT', context
                  )
        self.sourceCRS: QgsCoordinateReferenceSystem = \
            source.sourceCrs()

        self.transform: QgsCoordinateTransform = None

        if self.sourceCRS != EPSG4326:
            self.transform = QgsCoordinateTransform(
                self.sourceCRS,
                EPSG4326,
                QgsProject.instance()
                )

        self.featureCount = source.featureCount()

        DEMList: List[QgsMapLayer] = \
            self.parameterAsLayerList(
                parameters,
                self.pDEM_LIST,
                context
                )

        DSMList: List[QgsMapLayer] = \
            self.parameterAsLayerList(
                parameters,
                self.pDEM_LIST,
                context
                )
        # Dynamic Parameters
        self.name = self.parameterAsStrings(parameters, self.pNAME, context)[0]
        self.azimuth = self.parameterAsStrings(
            parameters, self.pAZIMUTH, context)[0]
        self.antennaHeight = self.parameterAsStrings(
            parameters, self.pANTENNA_HEIGHT, context)[0]
        self.mDowntilt: float = self.parameterAsStrings(
                parameters, self.pM_DOWNTILT, context)[0]
        self.eDowntilt = self.parameterAsStrings(
            parameters, self.pE_DOWNTILT, context)[0]
        self.hWidth = self.parameterAsStrings(
            parameters, self.pH_WIDTH, context)[0]
        self.vWidth = self.parameterAsStrings(
            parameters, self.pV_WIDTH, context)[0]

        # Azimuth Shift
        self.shift = self.parameterAsDouble(
            parameters, self.pSHIFT, context
            )
        self.shiftIsDynamic = QgsProcessingParameters.isDynamic(
            parameters, self.pSHIFT
            )
        if self.shiftIsDynamic:
            self.shiftProperty: QgsProperty = parameters[self.pSHIFT]

        # Units
        self.units = self.parameterAsInt(
            parameters, self.pUNITS, context
            )
        self.scaleFactor = 1 if self.units == 0 else \
            QgsUnitTypes.fromUnitToUnitFactor(
                QgsUnitTypes.DistanceFeet,
                QgsUnitTypes.DistanceMeters
                )

        sensibility = self.parameterAsDouble(
            parameters, self.pSENSIBILITY, context)

        sensibility = sensibility * self.scaleFactor
        # Upper sidelobe distance limit

        upperSidelobeLimit = self.parameterAsDouble(
            parameters, self.pUS_LIMIT, context
            )

        self.manager: GeometryManager = GeometryManager(EPSG4326)
        self.manager.setElevationRasterList(DEMList)
        self.manager.setSurfaceRasterList(DSMList)

        self.manager.setSensibility(sensibility)
        self.manager.setUpperSidelobeLimit(upperSidelobeLimit)

        if self.manager.isReady():
            feedback.pushInfo("Executing Algorithm sector by sector")
            return True
        else:
            feedback.reportError("Initialization Error")
            return False

    def processFeature(self,
                       feature: QgsFeature,
                       context: QgsProcessingContext,
                       feedback: QgsProcessingFeedback) -> List[QgsFeature]:
        features: List[QgsFeature] = []
        origin: QgsPointXY = feature.geometry().asPoint()

        if self.transform:
            origin = self.transform.transform(
                origin, direction=Qgis.TransformDirection.Forward)

        # Extract Dynamic Parameters

        name = str(feature[self.name])
        azimuth = float(feature[self.azimuth])
        if azimuth is None:
            feedback.pushDebugInfo(
                f"Azimuth.illegal error. Name:{name}"
                )
            return []
        azimuth %= 360

        # Shift
        if self.shiftIsDynamic:
            shift, success = self.shiftProperty.valueAsDouble(
                context.expressionContext(), self.shift
                )
            if not success:
                # Asume Zero
                shift = 0
        else:
            shift = self.shift

        shift %= 360

        antennaHeight = float(feature[self.antennaHeight])
        if antennaHeight <= 0 or antennaHeight is None:
            feedback.pushDebugInfo(
                f"AntennaHeight.illegal error. Name:{name}"
                )
            return []

        antennaHeight = antennaHeight * self.scaleFactor

        # M Downtilt
        mDowntilt = float(feature[self.mDowntilt])
        if mDowntilt is None:
            feedback.pushDebugInfo(
                f"MDowntiltProperty read error. Name:{name}"
                )
            return []

        eDowntilt = float(feature[self.eDowntilt])
        if eDowntilt is None:
            feedback.pushDebugInfo(
                f"EDowntiltProperty read error. Name:{name}"
                )
            return []

        # H Width
        hWidth = float(feature[self.hWidth])
        if hWidth is None:
            feedback.pushDebugInfo(
                f"HWidthProperty read error. Name:{name}"
                )
            return []
        if hWidth <= 0:
            feedback.pushDebugInfo(
                f"HWidth.illegal error. Name:{name}"
                )
            return []

        vWidth = float(feature[self.vWidth])
        if vWidth is None:
            feedback.pushDebugInfo(
                f"VWidthProperty read error. Name:{name}"
                )
            return []

        if vWidth <= 0:
            feedback.pushDebugInfo(
                f"VWidth.illegal error. Name:{name}"
                )
            return []

        builder: CellSectorBuilder = \
            (CellSectorBuilder(name, origin)
             .setAntennaHeigth(antennaHeight)
             .setAzimuth(azimuth, shift)
             .setMDowntilt(mDowntilt)
             .setEDowntilt(eDowntilt)
             .setHWidth(hWidth)
             .setVWidth(vWidth))

        mainLobe: CellSector = builder.mainlobe()
        if not mainLobe:
            feedback.pushDebugInfo(f"Mainlobe not Ready!. Name:{name}")
            return []

        mainLobeGeometry: Geometry = \
            self.manager.computeGeometry(mainLobe.copy())

        upperSidelobe: CellSector = builder.upperSidelobe()
        if not upperSidelobe:
            feedback.pushDebugInfo(f"Upper Sidelobe not Ready!. Name:{name}")
            return []

        upperSidelobeGeometry: Geometry =\
            self.manager.computeGeometry(upperSidelobe.copy())

        if not mainLobeGeometry or not upperSidelobeGeometry:
            feedback.pushDebugInfo(f"Null Geometry. Name:{name}")
            return []

        f = QgsFeature(feature)
        attributes = f.attributes()
        f.setAttributes(
            attributes + [
                mainLobeGeometry.distance,
                "Meters" if self.units == 0 else "Feet",
                "Mainlobe"
                ]
        )
        f.setGeometry(
            (
                mainLobeGeometry.geometry.transform(
                    self.transform, direction=Qgis.TransformDirection.Reverse)
                if self.transform else mainLobeGeometry.geometry
            )
        )
        features.append(f)

        f = QgsFeature(feature)
        attributes = f.attributes()
        f.setAttributes(
            attributes + [
                upperSidelobeGeometry.distance,
                "Meters" if self.units == 0 else "Feet",
                "Upper Sidelobe"
                ]
            )
        f.setGeometry(
            (
                upperSidelobeGeometry.geometry.transform(
                    self.transform, direction=Qgis.TransformDirection.Reverse)
                if self.transform else upperSidelobeGeometry.geometry
            )
        )
        features.append(f)

        return features

    def postProcessAlgorithm(self,
                             context: QgsProcessingContext,
                             feedback: QgsProcessingFeedback) -> dict:
        layer = context.getMapLayer(self.outputName())
        layer.loadNamedStyle(
            os.path.join(
                self.settings.plugin_directory,
                "resources", "styles",
                "cell_sector.qml"
            )
        )
        return {}
