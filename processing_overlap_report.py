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
from typing import Dict, List, Any

from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    Qgis,
    QgsDistanceArea,
    QgsExpression,
    QgsFeature,
    QgsFeatureIterator,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFileDestination,
    QgsUnitTypes,
)

from .settings import settings

class OverlapReport(QgsProcessingAlgorithm):
    pCELL_SECTORS = "CELL_SECTORS"
    pPOLYGONS = "POLYGONS"
    pUNITS = "UNITS"
    pREPORT = "REPORT"
    pCELL_SECTOR_NAME = "CELL_SECTOR_NAME"
    pCELL_SECTOR_LOBE = "CELL_SECTOR_LOBE"
    pPOLYGON_NAME = "POLYGON_NAME"
    def createInstance(self) -> QgsProcessingAlgorithm:
        return OverlapReport()
    def shortHelpString(self) -> str:
        return """
        <h1> Overlap Report </h1>
        TODO
        """
    def groupId(self) -> str:
        return 'geometrycalculator'
    
    def group(self) -> str:
        return 'Geometry Calculator'
    
    def name(self) -> str:
        return 'overlap_report'
    
    def displayName(self) -> str:
        return 'Overlap Report'
    
    def icon(self) -> QIcon:
        return QIcon(
            os.path.join(
                settings.plugin_directory,
                "resources", "icons",
                "overlap_report.png"
            )
        )
    def initAlgorithm(self,
                      configuration: Dict[str, Any]) -> None:
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.pCELL_SECTORS,
                "Cell-sector Layer",
                types=[QgsProcessing.TypeVectorPolygon],
                defaultValue=None,
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.pCELL_SECTOR_NAME,
                "Cell-sector Name Field",
                defaultValue="sector_name",
                parentLayerParameterName=self.pCELL_SECTORS,
                allowMultiple=False,
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.pPOLYGONS,
                "Polygons",
                types=[QgsProcessing.TypeVectorPolygon],
                defaultValue=None,
                optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.pPOLYGON_NAME,
                "Polygon name field",
                defaultValue="name",
                parentLayerParameterName=self.pPOLYGONS,
                allowMultiple=False,
                optional=False
            )
        )
        
        self.addParameter(
            QgsProcessingParameterEnum(
                self.pUNITS,
                'Map units',
                options= ["Kilometers", "Miles"],
                defaultValue=0,
                optional=False)
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.pREPORT,
                "Overlap Report destination",
                fileFilter='Text files (*txt)',
                defaultValue=None,
                optional=False,
                createByDefault=True
            )
        )
        return
    
    def processAlgorithm(self,
                         parameters: Dict[str, Any],
                         context: QgsProcessingContext,
                         feedback: QgsProcessingFeedback) -> Dict[str, Any]:
        
        path = self.parameterAsFileOutput(
            parameters, self.pREPORT, context)
        name = self.parameterAsFields(
            parameters, self.pCELL_SECTOR_NAME, context)
        polygons = self.parameterAsSource(
            parameters, self.pPOLYGONS, context)
        polygonNames = self.parameterAsFields(
            parameters, self.pPOLYGON_NAME, context)
        self.units = self.parameterAsInt(
            parameters, self.pUNITS, context
            )
        
        # TODO: Review
        self.toSquareKilometers = QgsUnitTypes.fromUnitToUnitFactor(
                QgsUnitTypes.AreaSquareMeters,
                QgsUnitTypes.AreaSquareKilometers
                )
        
        self.areaScaleFactor = 1 if self.units == 0 else \
            QgsUnitTypes.fromUnitToUnitFactor(
                QgsUnitTypes.AreaSquareKilometers,
                QgsUnitTypes.AreaSquareMiles
            )
        
        sectors = self.parameterAsSource(
            parameters, self.pCELL_SECTORS, context)
        
        if polygons is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.pPOLYGONS)
            )
        if sectors is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.pCELL_SECTORS)
            )
               
        if len(name) == 0:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.pCELL_SECTOR_NAME)
            )
        lobe: str = "lobe"
        name: str = name[0]
        
        distArea = QgsDistanceArea()
        distArea.setEllipsoid('WGS84')

        mainlobes_request = \
            QgsFeatureRequest().setFilterExpression(
                QgsExpression().createFieldEqualityExpression(
                    lobe, "Mainlobe"
                )
            )
        upper_sidelobes_request = \
            QgsFeatureRequest().setFilterExpression(
                QgsExpression().createFieldEqualityExpression(
                    lobe, "Upper Sidelobe"
                )
            )
        
        mainlobeList: List[QgsFeature] = []
        mainLobes: QgsFeatureIterator = sectors.getFeatures(mainlobes_request)
        mainlobeList.append(next(mainLobes))
        mainlobeCombined: QgsGeometry = mainlobeList[0].geometry()

        for feature in mainLobes:
            if feedback.isCanceled():
                return {}
            mainlobeCombined =mainlobeCombined.combine(feature.geometry())
            mainlobeList.append(feature)
        
        upperSidelobeList: List[QgsFeature] = []
        upperSidelobes: QgsFeatureIterator = \
            sectors.getFeatures(upper_sidelobes_request)
        upperSidelobeList.append(next(upperSidelobes))
        upperSidelobeCombined: QgsGeometry = upperSidelobeList[0].geometry()

        for feature in upperSidelobes:
            if feedback.isCanceled():
                return {}
            upperSidelobeCombined = \
                upperSidelobeCombined.combine(feature.geometry())
            upperSidelobeList.append(feature)
        
        polygonName: str = None
        if self.units == 0:
            units = 'km^2'
        else:
            units = 'mi^2'
        with open(path, "w") as file:
            file.write("Overlap and Coverage report\n")
            for polygon in polygons.getFeatures():
                if feedback.isCanceled():
                    return {}
                if len(polygonNames) == 0:
                    polygonName = polygon.id()
                else:
                    polygonName = polygonNames[0]
                
                polygonArea = \
                    distArea.measureArea(polygon.geometry()) * \
                    self.toSquareKilometers * \
                    self.areaScaleFactor

                file.write(f'Polygon: {polygonName}\n')
                feedback.pushInfo(f'Polygon: {polygonName}')
                
                file.write(f'Area: {polygonArea} {units}\n')
                feedback.pushInfo(f'Area: {polygonArea} {units}')

                mainlobeCoverage = distArea.measureArea(
                    polygon.geometry().intersection(mainlobeCombined)) *\
                    self.toSquareKilometers *\
                    self.areaScaleFactor
                upperSidelobeCoverage = distArea.measureArea(
                    polygon.geometry().intersection(upperSidelobeCombined)) *\
                    self.toSquareKilometers *\
                    self.areaScaleFactor
                
                file.write(
                    f'Mainlobes coverage: {mainlobeCoverage} {units} <=> {round(100.0*mainlobeCoverage / polygonArea,2)} %\n')
                feedback.pushInfo(
                    f'Mainlobes coverage: {mainlobeCoverage} {units} <=> {round(100.0*mainlobeCoverage / polygonArea,2)} %')

                file.write(
                    f'Mainlobes coverage: {upperSidelobeCoverage} {units} <=> {round(100*upperSidelobeCoverage / polygonArea,2)} %\n')
                feedback.pushInfo(
                    f'Mainlobes coverage: {upperSidelobeCoverage} {units} <=> {round(100*upperSidelobeCoverage / polygonArea,2)} %')
                
                statusIndex = 0
                total = len(mainlobeList) + len(upperSidelobeList)
                mainlobeIntersections: dict[str,float]= {}
                upperSidelobeIntersections: dict[str,float]= {}

                for i, sector in enumerate(mainlobeList):
                    if feedback.isCanceled():
                        return {}
                    statusIndex += 1
                    for shifted in mainlobeList[i+1:]:
                        if sector.geometry().intersects(shifted.geometry()):
                            overlapName = sector[name]+'x'+shifted[name]
                            if overlapName not in mainlobeIntersections:
                                mainlobeIntersections[overlapName] = \
                                    distArea.measureArea(
                                        sector.geometry().intersection(
                                            shifted.geometry()))*\
                                        self.toSquareKilometers*\
                                        self.areaScaleFactor
                    feedback.setProgress(int(statusIndex*100 / total))

                for i, sector in enumerate(upperSidelobeList):
                    if feedback.isCanceled():
                        return {}
                    statusIndex += 1
                    for shifted in upperSidelobeList[i+1:]:
                        if sector.geometry().intersects(shifted.geometry()):
                            overlapName = sector[name]+'x'+shifted[name]
                            if overlapName not in upperSidelobeIntersections:
                                upperSidelobeIntersections[overlapName] = \
                                    distArea.measureArea(
                                        sector.geometry().intersection(
                                            shifted.geometry()))*\
                                        self.toSquareKilometers*\
                                        self.areaScaleFactor
                    feedback.setProgress(int(statusIndex*100 / total))

                mainlobeTotalInterference = \
                    sum(mainlobeIntersections.values())
                upperSidelobeTotalInterference = \
                    sum(upperSidelobeIntersections.values())       
                
                file.write(
                    f"Total Mainlobes overlap: {round(mainlobeTotalInterference,2)} {units}\n\n")
                feedback.pushInfo(
                    f"Total Mainlobes overlap: {round(mainlobeTotalInterference,2)} {units}"
                )
                sortedMainlobeTotalInterference = \
                    dict(
                        sorted(
                            mainlobeIntersections.items(), 
                            key=lambda x:x[1], 
                            reverse=True
                            )
                        )
                
                file.write("Sector\tOverlap\n")
                for key, value in sortedMainlobeTotalInterference.items():
                    if round(value,2):
                        file.write(f'{key}:\t{round(value,2)} {units}\n')
                
                file.write(
                    f"\nUper Sidelobe Overlap: {round(upperSidelobeTotalInterference)} {units} \n\n")
                feedback.pushInfo(
                    f"\nUper Sidelobe Overlap: {round(upperSidelobeTotalInterference)} {units}"
                )
                
                sortedUpperSidelobeTotalInterference = \
                    dict(
                        sorted(
                            upperSidelobeIntersections.items(), 
                            key=lambda x:x[1], 
                            reverse=True
                            )
                        )
                
                file.write("Sector\tOverlap\n")
                for key, value in sortedUpperSidelobeTotalInterference.items():
                    if round(value,2):
                        file.write(f'{key}:\t{round(value,2)} {units}\n')
            
            return { 'OUTPUT': file}
        