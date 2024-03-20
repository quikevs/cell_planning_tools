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

from typing import Tuple, List, Union, Generator
from math import atan, radians, isnan
from threading import Lock

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsRasterDataProvider,
    QgsDistanceArea,
    )

from qgis.core import QgsMessageLog, Qgis

from .rf import CellSector
from .errors import NotInitialized, OutOfRangeError


EPSG4326 = QgsCoordinateReferenceSystem("EPSG:4326")


def logMessage(message: str, level: Qgis.MessageLevel = Qgis.Info) -> None:
    QgsMessageLog.logMessage(
                message,
                "Cell Planning Tools",
                level=level
                )
    return

class Geometry:
    def __init__(
            self,
            CellSector: CellSector,
            Geometry: QgsGeometry,
            stepSize: float,
            heightVector: List[float],
            ) -> None:
        self.cellSector: CellSector = CellSector
        self.geometry: QgsGeometry = Geometry
        self.stepSize: float = stepSize
        self.heightVector: List[float] = heightVector
        return

    @property
    def distance(self) -> float:
        return self.stepSize*(len(self.heightVector)-1)


class GeometryManagerMeta(type):
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwds):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwds)
                cls._instances[cls] = instance
            return cls._instances[cls]


class GeometryManager(metaclass=GeometryManagerMeta):
    def __init__(self, crs: QgsCoordinateReferenceSystem) -> None:
        self.crs: QgsCoordinateReferenceSystem = crs
        self.distanceArea: QgsDistanceArea = QgsDistanceArea()
        self.distanceArea.setEllipsoid("WGS84")
        self.sensibility: float = None
        self.upperSidelobeLimit: float = 30_000

        self.demRasterList: List[QgsRasterLayer] = []
        self.demProviderList: List[QgsRasterDataProvider] = []
        self.demTransformList: List[QgsCoordinateTransform] = []

        self.dsmRasterList: List[QgsRasterLayer] = []
        self.dsmProviderList: List[QgsRasterDataProvider] = []
        self.dsmTransformList: List[QgsCoordinateTransform] = []
        return

    def setSurfaceRasterList(self, layerList: List[QgsRasterLayer]) -> None:
        self.dsmRasterList: List[QgsRasterLayer] = []
        self.dsmProviderList: List[QgsRasterDataProvider] = []
        self.dsmTransformList: List[QgsCoordinateTransform] = []
        for layer in layerList:
            self.dsmRasterList.append(layer)
            provider = layer.dataProvider()
            self.dsmProviderList.append(provider)
            if layer.crs() != EPSG4326:
                self.dsmTransformList.append(QgsCoordinateTransform(
                    self.crs,
                    layer.crs(),
                    QgsProject()))
            else:
                self.dsmTransformList.append(None)
        return

    def getDSMLayerNames(self):
        return (',').join([layer.name() for layer in self.dsmRasterList])

    def setElevationRasterList(self, layerList: List[QgsRasterLayer]) -> None:
        self.demRasterList: List[QgsRasterLayer] = []
        self.demProviderList: List[QgsRasterDataProvider] = []
        self.demTransformList: List[QgsCoordinateTransform] = []
        for layer in layerList:
            self.demRasterList.append(layer)
            provider = layer.dataProvider()
            self.demProviderList.append(provider)
            if layer.crs() != EPSG4326:
                self.demTransformList.append(QgsCoordinateTransform(
                    self.crs,
                    layer.crs(),
                    QgsProject()))
            else:
                self.demTransformList.append(None)
        return

    def setSensibility(self, sensibility: float) -> None:
        if sensibility <= 0:
            raise OutOfRangeError(
                "Sensibility Out of Range",
                {
                    'sensibility': sensibility,
                }
            )
        self.sensibility = sensibility
        return

    def setUpperSidelobeLimit(self, upperSidelobeLimit: float) -> None:
        self.upperSidelobeLimit = upperSidelobeLimit
        return

    def isReady(self) -> bool:
        if (self.crs is not None and
            len(self.demRasterList) > 0,
            all([provider for provider in self.demProviderList]) and
            len(self.demProviderList) ==
            len(self.demTransformList) and
                self.sensibility is not None):
            return True
        else:
            return False

    def isSurfaceReady(self) -> bool:

        if (len(self.dsmRasterList) > 0 and
            all([provider for provider in self.dsmProviderList]) and
            len(self.dsmProviderList) == len(self.dsmTransformList) and
                self.sensibility is not None):
            return True
        else:
            return False

    def sampleElevation(self, point: QgsPointXY) -> Tuple[float, bool]:
        if self.isReady():
            for i, raster in enumerate(self.demRasterList):
                if self.demTransformList[i]:
                    point_x = self.demTransformList[i].transform(point)
                result, _ = raster.dataProvider().sample(point_x, 1)
                if not isnan(result):
                    # There are Readings within this provider
                    return result, True
                else:
                    # No reading within this provider
                    continue
            return None, False
        else:
            raise NotInitialized(
                'DEM Manager Not Initialized',
                {
                    'demRasterList': self.demRasterList,
                    'sensibility': self.sensibility,
                    'crs': self.crs
                }
            )

    def sampleSurface(self, point: QgsPointXY) -> Tuple[float, bool]:
        if self.isReady():
            if self.isSurfaceReady():
                for i, raster in enumerate(self.dsmRasterList):
                    if self.dsmTransformList[i]:
                        point_x = self.dsmTransformList[i].transform(point)
                    result, _ = raster.dataProvider().sample(point_x, 1)
                    if not isnan(result):
                        # There are Readings within this provider
                        return result, True
                    else:
                        # No reading within this provider
                        continue
                return None, False
            else:
                raise NotInitialized(
                    'DSM Manager Not Initialized',
                    {
                        'dsmRasterList': self.dsmRasterList,
                        'sensibility': self.sensibility,
                        'crs': self.crs
                    }
                )
        else:
            raise NotInitialized(
                'DEM Manager Not Initialized',
                {
                    'demRasterList': self.demRasterList,
                    'sensibility': self.sensibility,
                    'crs': self.crs
                }
            )

    def get_walker(self, cellSector: CellSector):
        def walk():
            crossed: bool = False
            step: int = 0
            while not crossed:
                distance: float = step * self.sensibility
                point: QgsPointXY = None
                _, point = self.distanceArea.measureLineProjected(
                    cellSector.origin, distance, radians(cellSector.azimuth)
                    )
                sample, success = Sample(point)
                if not success:
                    # Value not found in any DEM/DSM Provider
                    # StopIteration
                    return
                else:
                    beam_height: float = (
                        -atan(radians(cellSector.totalDowntilt)) * distance +
                        cellSector.antennaHeight + cellSector.floorHeight)
                    clearance: float = beam_height - sample
                    if clearance <= 0 or distance >= self.upperSidelobeLimit:
                        crossed = True
                    step += 1
                    yield sample, clearance

        if self.isReady():
            floorHeight, success = self.sampleElevation(cellSector.origin)
            if not success:
                return None
            else:
                cellSector.floorHeight = floorHeight
                Sample: callable = self.sampleSurface \
                    if self.isSurfaceReady() else self.sampleElevation
                return walk
        else:
            raise NotInitialized(
                'DEM Manager Not Initialized',
                {
                    'DEMRasterList': self.demRasterList,
                    'sensibility': self.sensibility,
                    'crs': self.crs
                }
            )

    def pointsCrossingDateLine(self, points: List[QgsPointXY]) -> bool:
        length: int = len(points)
        if length == 0:
            return False
        lastLongitude: float = points[0].x()
        for i in range(1, length):
            longitude: float = points[i].x()
            if lastLongitude < 0 and longitude >= 0:
                if longitude-lastLongitude > 180:
                    return True
            elif lastLongitude >= 0 and longitude < 0:
                if lastLongitude - longitude > 180:
                    return True
        return False

    def crossingDateLineMakesPositive(self, points: List[QgsPointXY]) -> None:
        if self.pointsCrossingDateLine(points):
            length: int = len(points)
            for i in range(length):
                longitude: float = points[i].x()
                if longitude < 0:
                    points[i].setX(longitude + 360)
        return

    def draw(self, cellSector: CellSector, distance: float) -> QgsGeometry:
        points: List[QgsPointXY] = []
        points.append(cellSector.origin)
        HalfWidth: float = cellSector.hWidth / 2.0

        initBearing = (
            (cellSector.azimuth + cellSector.shift -
             HalfWidth) % 360)

        lastBearing = (
            (cellSector.azimuth + cellSector.shift +
             HalfWidth) % 360)
        initBearing -= 360 if initBearing > lastBearing else 0

        point: QgsPointXY = None
        while initBearing < lastBearing:
            _, point = self.distanceArea.measureLineProjected(
                cellSector.origin, distance, radians(initBearing))
            points.append(point)
            initBearing += 10  # Arbitrary

        _, point = self.distanceArea.measureLineProjected(
            cellSector.origin, distance, radians(lastBearing))

        points.append(point)
        points.append(cellSector.origin)  # Close the Polygon

        self.crossingDateLineMakesPositive(points)

        return QgsGeometry.fromPolygonXY([points])

    def computeGeometry(self, cellSector: CellSector) -> Geometry:
        if self.isReady():
            heightVector: List[float] = []
            clearanceVector: List[float] = []
            walker = self.get_walker(cellSector)
            if not walker:
                return None
            for height, clearance in walker():
                heightVector.append(height)
                clearanceVector.append(clearance)
            distance = self.sensibility*(len(heightVector)-1)
            return Geometry(
                cellSector,
                self.draw(cellSector, distance),
                self.sensibility,
                heightVector)
        else:
            raise NotInitialized(
                "Geometry Manager not Initialized",
                {
                    'DEMRasterList': self.demRasterList,
                    'sensibility': self.sensibility,
                    'crs': self.crs
                }
            )

    def computeLOS(self, cellSector: CellSector) -> List[Geometry]:
        if self.isReady():
            azimuth = cellSector.azimuth + cellSector.shift
            step = cellSector.hWidth / 20

            initialBearing = (azimuth - 10 * step) % 360
            lastBearing = (azimuth + 10 * step) % 360
            lines: list[QgsGeometry] = []

            initialBearing -= 360 if initialBearing > lastBearing else 0
            while initialBearing < lastBearing:
                heightVector: List[float] = []
                bearingAsSector: CellSector = cellSector.copy()
                bearingAsSector.azimuth = initialBearing
                walker = self.get_walker(bearingAsSector)
                if not walker:
                    return None
                for height, _ in walker():
                    heightVector.append(height)
                distance = self.sensibility * (len(heightVector) - 1)
                _, point = self.distanceArea.measureLineProjected(
                    cellSector.origin, distance, radians(initialBearing))
                points = [cellSector.origin, point]
                self.crossingDateLineMakesPositive(points)
                lines.append(QgsGeometry.fromPolylineXY(points))
                initialBearing += step
            heightVector: List[float] = []
            bearingAsSector: CellSector = cellSector.copy()
            bearingAsSector.azimuth = lastBearing
            walker = self.get_walker(bearingAsSector)
            if not walker:
                return None
            for height, _ in walker():
                heightVector.append(height)
            distance = self.sensibility * (len(heightVector) - 1)
            _, point = self.distanceArea.measureLineProjected(
                cellSector.origin, distance, radians(lastBearing))
            points = [cellSector.origin, point]
            self.crossingDateLineMakesPositive(points)
            lines.append(QgsGeometry.fromPolylineXY(points))
            return lines

        else:
            raise NotInitialized(
                "Geometry Manager not Initialized",
                {
                    'DEMRasterList': self.demRasterList,
                    'sensibility': self.sensibility,
                    'crs': self.crs
                }
            )

