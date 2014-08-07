#!/usr/bin/env/python
"""
Pyrate - Optical raytracing based on Python

Copyright (C) 2014 Moritz Esslinger moritz.esslinger@web.de
               and    Uwe Lippmann  uwe.lippmann@web.de

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import inspector
import pupil
import field
import raster
from ray import RayBundle
from numpy import *

class aimFiniteByMakingASurfaceTheStop(object):
    def __init__(self, opticalSystem, 
    pupilType="EntrancePupilDiameter", pupilSizeParameter = 0,
    fieldType="ObjectHeight", 
    rasterType="rasterRectGrid", nray = 10, 
    wavelength = 0.55, stopPosition = 1):
        """
        This class provides functionality to create an initial ray bundle 
        that can be traced through an optical system.
        It is intended for finite object distances and assumes one surface 
        of the optical system to be the stop surface.
        The aiming is non-iterative, which means there is no chcek whether 
        the ray actually hits the pupil position it was
        aimed for.
        """

        self.stopDiameter = 0

        self.listOfPupilTypeNames, self.listOfPupilTypeClasses = inspector.getListOfClasses(pupil, "<class \'pupil.", "")
        self.listOfFieldTypeNames, self.listOfFieldTypeClasses = inspector.getListOfClasses(field, "<class \'field.", "")
        self.listOfRasterTypeNames, self.listOfRasterTypeClasses = inspector.getListOfClasses(raster, "<class \'raster.", "")

        self.setPupilType( pupilType )
        self.setStopSize(opticalSystem, pupilSizeParameter,stopPosition, wavelength)
        self.setFieldType( fieldType )
        self.setPupilRaster(rasterType, nray)

    def setPupilType(self, pupilType ):
        """
        Sets up the private data of this class required to aim rays through the pupil.

        :param pupilType: name of the class in pupil.py that defines the type of pupil (F#, NA, stop dia, ...) (str)
        """

        if pupilType in self.listOfPupilTypeNames:
            i = self.listOfPupilTypeNames.index(pupilType)
        
            self.pupilSizeCalculatorObject = self.listOfPupilTypeClasses[i]()
        else:
            print 'Warning: pupil type \'', pupilType, '\' not found. setPupilType() aborted.'      


    def setStopSize(self, opticalSystem, pupilSizeParameter, stopPosition, wavelength):
        """
        Calculates the stop size required for an optical system and a given pupil size.
        Requires setPupilType() to set up basic pupil data first.

        :param opticalSystem: OpticalSystem object
        :param pupilSizeParameter: size parameter of the pupil. Unit depends on pupilType. (float)
        :param stopPosition: surface number of the stop (int)
        :param wavelength: wavelength for pupil size calculation in um (float)
        """
        self.stopPosition = stopPosition
        dummyRay = RayBundle(zeros((3,3)), ones((3,3)), wavelength)
        temp_ms, self.stopDiameter = self.pupilSizeCalculatorObject.get_marginalSlope(opticalSystem, self.stopPosition, dummyRay, pupilSizeParameter)

    def getMarginalSlope(self, opticalSystem, ray):
        """
        Returns the marginal ray slope required for ray aiming.
        Once the pupil type and stop size are set up at the primary wavelength, this method 
        is intended to quickly return the marginal ray slope at different wavelengths for the pre-set stop diameter.

        :param opticalSystem: OpticalSystem object

        :return marginalSlope: slope (dy/dz) of the marginal ray (float)
        """
        CalculatorObject2 = pupil.StopDiameter()
        marginalslope, temp_stopDia = CalculatorObject2.get_marginalSlope(opticalSystem, self.stopPosition, ray, self.stopDiameter)
        return marginalslope

    def setFieldType(self, fieldType ):
        """
        Sets up the private data of this class required to aim rays through the pupil.

        :param fieldType: name of the function in field.py that defines the type of field (height, angle, ...) (str)
        """

        if fieldType in self.listOfFieldTypeNames:
            i = self.listOfFieldTypeNames.index(fieldType)
        
            self.chiefSlopeCalculatorObject = self.listOfFieldTypeClasses[i]()
        else:
            print 'Warning: field type \'', fieldType, '\' not found. setFieldType() aborted.'      

    def setPupilRaster(self, rasterType, nray):
        """
        Sets up the private data of this class required to aim rays through the pupil.

        :param rasterType: name of the function in raster.py that defines the type of pupil raster (grid, fan, random, ...) (str)
        :param nray: desired number of rays for the raster (int)
        """

        if rasterType in self.listOfRasterTypeNames:
            i = self.listOfRasterTypeNames.index(rasterType)
        
            temp_obj = self.listOfRasterTypeClasses[i]()
            self.xpup, self.ypup = temp_obj.getGrid(nray)
        else:
            print 'Warning: raster type \'', rasterType, '\' not found. setPupilRaster() aborted.'      

    def getInitialRayBundle(self, opticalSystem, fieldXY, wavelength):
        """
        Creates and returns a RayBundle object that aims at the optical system pupil.
        Pupil position is estimated paraxially.
        Aiming into the pupil is non-iterative, which means there is no check 
        whether the real ray actually hits the stop at the paraxially calculated position.
        
        TO DO: At the moment, this function fails to produce correct values for immersion
        """
        # dummy ray that carries the wavelength information
        ray = RayBundle(zeros((3,3)), ones((3,3)), wavelength) 

        marginalslope = self.getMarginalSlope(opticalSystem, wavelength)
        chiefslopeXY  = self.chiefSlopeCalculatorObject.getChiefSlope(opticalSystem, self.stopPosition, ray, fieldXY)

        nray = len(self.xpup)
        slopeX = chiefslopeXY[0] + marginalslope * self.xpup # dx/dz
        slopeY = chiefslopeXY[1] + marginalslope * self.ypup # dy/dz
        k = ones((3,nray), dtype=float )
        k[0,:] = slopeX
        k[1,:] = slopeY
        #k[2,:] = 1

        absk = sqrt( sum(k**2, axis=0) )
        k[0] = k[0] / absk
        k[1] = k[1] / absk
        k[2] = k[2] / absk

        originXY = self.chiefSlopeCalculatorObject.getObjectHeight(opticalSystem, ray, self.stopPosition, fieldXY)
        nray = len( self.xpup )
        o = zeros((3,nray), dtype=float )
        o[0,:] = originXY[0]
        o[1,:] = originXY[1]

        raybundle = RayBundle( o, k, wavelength, pol=[])
        return raybundle



