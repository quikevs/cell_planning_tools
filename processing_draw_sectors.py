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

from .settings import settings
from .utils import EPSG4326, GeometryManager, Geometry
from .rf import CellSectorBuilder, CellSector

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

    def createInstance(self) -> QgsProcessingFeatureBasedAlgorithm:
        return DrawSectors()
    
    def icon(self) -> QIcon:
        return QIcon(
            os.path.join(
                settings.plugin_directory, 
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
        param = QgsProcessingParameterString(
            self.pNAME,
            "Cell Sector Name (Unique)",
            defaultValue=None,
            multiLine=False,
            optional=False
        )
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(
            QgsPropertyDefinition(
                self.pNAME,
                'Cell-sector Name (Unique)',
                QgsPropertyDefinition.String
            )
        )
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        # Elevation Layer List
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.pDEM_LIST,
                "Digital Elevation Model (DEM) raster list",
                layerType=QgsProcessing.TypeRaster,
                defaultValue=None,
                optional=False,
            )
        )

        # Surface Layer List
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.pDSM_LIST,
                "Digital Surface Model (DSM) raster list (optional)",
                layerType=QgsProcessing.TypeRaster,
                defaultValue=None,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.pSENSIBILITY,
                "DEM/DSM Sensibility (in map units)",
                defaultValue=0.0,
                optional=False,
                minValue=0.1,
            )
        )

        # Note: Azimuth
        param = QgsProcessingParameterNumber(
            self.pAZIMUTH,
            'Azimuth',
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False
        )
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(
            QgsPropertyDefinition(
                self.pAZIMUTH,
                'Azimuth',
                QgsPropertyDefinition.Double
            )
        )
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        # Note: Azimuth Shift
        param = QgsProcessingParameterNumber(
            self.pSHIFT,
            'Azimuth Shift',
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
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

        # Note: Antenna Height
        param = QgsProcessingParameterNumber(
            self.pANTENNA_HEIGHT,
            'Antenna Height',
            QgsProcessingParameterNumber.Double,
            defaultValue=1,
            optional=False,
        )
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(
            QgsPropertyDefinition(
                self.pANTENNA_HEIGHT,
                'Antenna Height',
                QgsPropertyDefinition.Double
            )
        )
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        
        # Note: Mechanical Downtilt 
        param = QgsProcessingParameterNumber(
            self.pM_DOWNTILT,
            'Mechanical Downtilt',
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False
        )
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(
            QgsPropertyDefinition(
                self.pM_DOWNTILT,
                'Mechanical Downtilt',
                QgsPropertyDefinition.Double
            )
        )
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        # Note: Electrical Downtilt 
        param = QgsProcessingParameterNumber(
            self.pE_DOWNTILT,
            'Electrical Downtilt',
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False
        )
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(
            QgsPropertyDefinition(
                self.pE_DOWNTILT,
                'Electrical Downtilt',
                QgsPropertyDefinition.Double
            )
        )
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        # Note: H_WIDTH
        param = QgsProcessingParameterNumber(
            self.pH_WIDTH,
            'Horizontal Beam Width',
            QgsProcessingParameterNumber.Double,
            defaultValue=65.0,
            optional=False
            )
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(
            QgsPropertyDefinition(
                self.pH_WIDTH,
                'Horizontal Beam Width',
                QgsPropertyDefinition.Double
                ))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        # Node: V_WIDTH
        param = QgsProcessingParameterNumber(
            self.pV_WIDTH,
            'Vertical Beam Width',
            QgsProcessingParameterNumber.Double,
            defaultValue=10.0,
            optional=False
            )
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(
            QgsPropertyDefinition(
                self.pV_WIDTH,
                'Vertical Beam Width',
                QgsPropertyDefinition.Double
                ))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        # Upper sidelobe distance limit
        self.addParameter(
            QgsProcessingParameterNumber(
                self.pUS_LIMIT,
                "Upper sidelobe distance limit",
                QgsProcessingParameterNumber.Double,
                defaultValue=30000,
                optional = False
            )
        )
        
        # Node: Resulting Distance Units
        self.addParameter(
            QgsProcessingParameterEnum(
                self.pUNITS,
                'Map units',
                options= ["Meters", "Feet"],
                defaultValue=0,
                optional=False)
        )
        return
    
    def prepareAlgorithm(self, 
                         parameters: Dict[str, Any], 
                         context: QgsProcessingContext, 
                         feedback: QgsProcessingFeedback) -> bool:
        
        source:QgsProcessingFeatureSource = \
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

        self.name = self.parameterAsString(
            parameters, self.pNAME, context
        )
        self.nameIsDynamic = QgsProcessingParameters.isDynamic(
            parameters, self.pNAME
        )
        if self.nameIsDynamic:
            self.NameProperty: QgsProperty = parameters[self.pNAME]

        # Azimuth

        self.azimuth = self.parameterAsDouble(
            parameters, self.pAZIMUTH, context
            )
        self.azimuthIsDynamic = QgsProcessingParameters.isDynamic(
            parameters, self.pAZIMUTH
            )
        if self.azimuthIsDynamic:
            self.azimuthProperty: QgsProperty = parameters[self.pAZIMUTH]

        # Azimuth Shift
        self.shift = self.parameterAsDouble(
            parameters, self.pSHIFT, context
            )
        self.shiftIsDynamic = QgsProcessingParameters.isDynamic(
            parameters, self.pSHIFT
            )
        if self.shiftIsDynamic:
            self.shiftProperty: QgsProperty = parameters[self.pSHIFT]

        
        # Antenna Heigth
        self.antennaHeight = self.parameterAsDouble(
            parameters, self.pANTENNA_HEIGHT, context
            )
        self.antennaHeightIsDynamic = QgsProcessingParameters.isDynamic(
            parameters, self.pANTENNA_HEIGHT
            )
        if self.antennaHeightIsDynamic:
            self.antennaHeightProperty: QgsProperty = \
                parameters[self.pANTENNA_HEIGHT]
        
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
            parameters, self.pSENSIBILITY,context)
        
        sensibility = sensibility * self.scaleFactor
        
        # Mechanical Downtilt

        self.mDowntilt: float = self.parameterAsDouble(
                parameters, self.pM_DOWNTILT, context
                )
        self.mDowntiltIsDynamic: bool = QgsProcessingParameters.isDynamic(
            parameters, self.pM_DOWNTILT
            )
        if self.mDowntiltIsDynamic:
            self.mDowntiltProperty: QgsProperty = parameters[self.pM_DOWNTILT]

        # Electrical Downtilt
        self.eDowntilt = self.parameterAsDouble(
            parameters, self.pE_DOWNTILT, context
            )
        self.eDowntiltIsDynamic = QgsProcessingParameters.isDynamic( 
            parameters, self.pE_DOWNTILT
            )
        if self.eDowntiltIsDynamic:
            self.eDowntiltProperty: QgsProperty = parameters[self.pE_DOWNTILT]

        # H width
        self.hWidth = self.parameterAsDouble(
            parameters, self.pH_WIDTH, context
            )
        self.hWidthIsDynamic = QgsProcessingParameters.isDynamic( 
            parameters, self.pH_WIDTH
            )
        if self.hWidthIsDynamic:
            self.hWidthProperty: QgsProperty = parameters[self.pH_WIDTH]


        # VWith
        self.vWidth = self.parameterAsDouble(
            parameters, self.pV_WIDTH, context
            )
        self.vWidthIsDynamic = QgsProcessingParameters.isDynamic( 
            parameters, self.pV_WIDTH
            )
        if self.vWidthIsDynamic:
            self.vWidthProperty: QgsProperty = parameters[self.pV_WIDTH]

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
        
        #Extract Dynamic Parameters
        
        if self.nameIsDynamic:
            name, success = self.NameProperty.valueAsString(
                context.expressionContext(), self.name
            )
            if not success:
                feedback.pushDebugInfo(
                    f"NameProperty read error on Feature: {feature.id}"
                )
                return []
        else:
            name = self.name

        #Azimuth
            
        if self.azimuthIsDynamic:
            azimuth, success = self.azimuthProperty.valueAsDouble(
                context.expressionContext(), self.azimuth
                )
            if not success:
                feedback.pushDebugInfo(
                    f"AzimuthProperty read error. Name:{name}"
                    )
                return []
        else:
            azimuth = self.azimuth

        azimuth %= 360
        
        #Shift
        if self.shiftIsDynamic:
            shift, success = self.shiftProperty.valueAsDouble(
                context.expressionContext(), self.shift
                )
            if not success:
                #Asume Zero
                shift = 0
        else:
            shift = self.shift

        shift %= 360

        #Antenna Height
        if self.antennaHeightIsDynamic:
            antennaHeight, success = self.antennaHeightProperty.valueAsDouble(
                context.expressionContext(), self.antennaHeight
                )
            if not success:
                feedback.pushDebugInfo(
                    f"AntennaHeightProperty read error. Name:{name}"
                    )
                return []
        else:
            antennaHeight = self.antennaHeight

        if antennaHeight <= 0:
            feedback.pushDebugInfo(
                f"AntennaHeight.illegal error. Name:{name}"
                )
            return []
        
        antennaHeight = antennaHeight * self.scaleFactor

        #M Downtilt
        if self.mDowntiltIsDynamic:
            mDowntilt, success = self.mDowntiltProperty.valueAsDouble(
                context.expressionContext(), self.mDowntilt
                )
            if not success:
                feedback.pushDebugInfo(
                    f"MDowntiltProperty read error. Name:{name}"
                    )
                return []
        else:
            mDowntilt = self.mDowntilt

        mDowntilt %= 360

        #E Downtilt
        if self.eDowntiltIsDynamic:
            eDowntilt, success = self.eDowntiltProperty.valueAsDouble(
                context.expressionContext(), self.eDowntilt
                )
            if not success:
                feedback.pushDebugInfo(
                    f"EDowntiltProperty read error. Name:{name}"
                    )
                return []
        else:
            eDowntilt = self.eDowntilt

        eDowntilt %= 360

        #H Width
        if self.hWidthIsDynamic:
            hWidth, success = self.hWidthProperty.valueAsDouble(
                context.expressionContext(), self.hWidth
                )
            if not success:
                feedback.pushDebugInfo(
                    f"HWidthProperty read error. Name:{name}"
                    )
                return []
        else:
            hWidth = self.hWidth

        if hWidth <=0:
            feedback.pushDebugInfo(
                f"HWidth.illegal error. Name:{name}"
                )
            return []

        # V Width
        if self.vWidthIsDynamic:
            vWidth, success = self.vWidthProperty.valueAsDouble(
                context.expressionContext(), self.vWidth
                )
            if not success:
                feedback.pushDebugInfo(
                    f"VWidthProperty read error. Name:{name}"
                    )
                return []
        else:
            vWidth = self.vWidth
        
        if vWidth <= 0:
            feedback.pushDebugInfo(
                f"HWidth.illegal error. Name:{name}"
                )
            return []
        
            
        builder: CellSectorBuilder = (CellSectorBuilder(name, origin)
                   .setAntennaHeigth(antennaHeight)
                   .setAzimuth(azimuth, shift)
                   .setMDowntilt(mDowntilt)
                   .setEDowntilt(eDowntilt)
                   .setHWidth(hWidth)
                   .setVWidth(vWidth)
                   )
        
        mainLobe: CellSector = builder.mainlobe()
        if not mainLobe:
            feedback.pushDebugInfo(f"Mainlobe not Ready!. Name:{name}")
            return []   
        mainLobeGeometry: Geometry = \
            self.manager.computeGeometry(mainLobe)
        
        upperSidelobe: CellSector = builder.upperSidelobe()
        if not upperSidelobe:
            feedback.pushDebugInfo(f"Uper Sidelobe not Ready!. Name:{name}")
            return []
        
        upperSidelobeGeometry: Geometry =\
            self.manager.computeGeometry(upperSidelobe)
        
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
                settings.plugin_directory,
                "resources","styles",
                "cell_sector.qml"
            )
        )
        return {} 
