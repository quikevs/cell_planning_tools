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

import dataclasses as dc
from typing import TypeVar, Dict

from qgis.core import QgsPointXY

from .errors import OutOfRangeError


TCellSectorBuilder = TypeVar("TCellSectorBuilder", bound="CellSectorBuilder")
TCellSector = TypeVar("TCellSector", bound="CellSector")


@dc.dataclass
class CellSector:
    name: str
    origin: QgsPointXY = dc.field(repr=False)
    antennaHeight: float = dc.field(repr=False)
    azimuth: float = dc.field(repr=False)
    shift: float = dc.field(repr=False)
    mDowntilt: float = dc.field(repr=False)
    eDowntilt: float = dc.field(repr=False)
    hWidth: float = dc.field(repr=False)
    vWidth: float = dc.field(repr=False)
    minEDowntilt: float = dc.field(default=0, repr=False)
    maxEDowntilt: float = dc.field(default=10, repr=False)
    floorHeight: float = dc.field(default=None, init=False, repr=False)

    @property
    def totalDowntilt(self) -> float:
        return self.mDowntilt + self.eDowntilt

    def asdict(self) -> Dict:
        return self.__dict__

    def copy(self) -> TCellSector:
        copy = dc.replace(self)
        for key, value in self.asdict().items():
            setattr(copy, key, value)
        return copy

    def setFloorElevation(floorHeight: float) -> None:
        floorHeight = floorHeight
        return


@dc.dataclass
class CellSectorBuilder:
    name: str
    origin: QgsPointXY = dc.field(repr=False)
    antennaHeight: float = dc.field(default=None, init=False, repr=False)
    azimuth: float = dc.field(default=None, init=False, repr=False)
    shift: float = dc.field(default=0.0, init=False, repr=False)
    mDowntilt: float = dc.field(default=0, init=False, repr=False)
    eDowntilt: float = dc.field(default=None, init=False, repr=False)
    hWidth: float = dc.field(default=None, init=False, repr=False)
    vWidth: float = dc.field(default=10, init=False, repr=False)
    minEDowntilt: float = dc.field(default=0, init=False, repr=False)
    maxEDowntilt: float = dc.field(default=10, init=False, repr=False)

    def setAntennaHeigth(self, antennaHeight: float) -> TCellSectorBuilder:
        if antennaHeight > 0:
            self.antennaHeight = antennaHeight
            return self
        else:
            raise OutOfRangeError(
                "Antenna Height Out of Range",
                {
                    "antennaHeight": antennaHeight,
                }
            )

    def setAzimuth(
            self,
            azimuth: float,
            shift: float = 0) -> TCellSectorBuilder:
        self.azimuth = azimuth % 360
        self.shift = shift % 360
        return self

    def setMDowntilt(self, mDowntilt: float) -> TCellSectorBuilder:
        self.mDowntilt = mDowntilt
        return self

    def setEDowntilt(
            self,
            eDowntilt: float,
            minRange: float = 0,
            maxRange: float = 10
            ) -> TCellSectorBuilder:
        self.minEDowntilt = minRange
        self.maxEDowntilt = maxRange
        if self.minEDowntilt <= eDowntilt <= self.maxEDowntilt:
            self.eDowntilt = eDowntilt
            return self
        else:
            raise OutOfRangeError(
                "Electrica tilt ot of Range",
                {
                    'minRange': minRange,
                    'maxRange': maxRange,
                    'value': eDowntilt,
                }
            )

    def setHWidth(self, hWidth: float) -> TCellSectorBuilder:
        if hWidth > 0:
            self.hWidth = hWidth
            return self
        else:
            raise OutOfRangeError(
                "Horizontal Beam Width Out of Range",
                {"hWidth": hWidth}
            )

    def setVWidth(self, vWidth: float) -> TCellSectorBuilder:
        if vWidth > 0:
            self.vWidth = vWidth
            return self
        else:
            raise OutOfRangeError(
                "Vertical Beam Width Out of Range",
                {"vWidth": vWidth}
            )

    def asdict(self) -> Dict:
        return self.__dict__

    def ready(self) -> bool:
        if self.antennaHeight is None or self.azimuth is None \
           or self.eDowntilt is None or self.hWidth is None:
            return False
        else:
            return True

    def mainlobe(self) -> CellSector:
        if not self.ready():
            return None
        return CellSector(
            self.name,
            self.origin,
            self.antennaHeight,
            self.azimuth,
            self.shift,
            self.mDowntilt,
            self.eDowntilt,
            self.hWidth,
            self.vWidth,
            self.minEDowntilt,
            self.maxEDowntilt,
        )

    def upperSidelobe(self) -> CellSector:
        if not self.ready():
            return None
        return CellSector(
            self.name,
            self.origin,
            self.antennaHeight,
            self.azimuth,
            self.shift,
            round(self.mDowntilt - self.vWidth / 2.0, 2),
            self.eDowntilt,
            self.hWidth,
            self.vWidth,
            self.minEDowntilt,
            self.maxEDowntilt,
        )
