#!/usr/bin/env/python
"""
Pyrate - Optical raytracing based on Python

Copyright (C) 2014-2018
               by     Moritz Esslinger moritz.esslinger@web.de
               and    Johannes Hartung j.hartung@gmx.net
               and    Uwe Lippmann  uwe.lippmann@web.de
               and    Thomas Heinze t.heinze@uni-jena.de
               and    others

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

import numpy as np
from ...core.log import BaseLogger
from ..globalconstants import numerical_tolerance


class RayBundleAnalysis(BaseLogger):
    """
    Class for analysis of raybundle.
    """
    def __init__(self, raybundle, name=""):
        super(RayBundleAnalysis, self).__init__(name=name)
        self.raybundle = raybundle

    def getCentroidPosition(self):
        """
        Returns the arithmetic average position of all rays at the end of the
        ray bundle.

        :return centr: centroid position (1d numpy array of 3 floats)
        """

        o = self.raybundle.x[-1]
        (_, num_points) = np.shape(o)
        centroid = 1.0/(num_points + numerical_tolerance) * np.sum(o, axis=1)

        return centroid

    def getRMSspotSize(self, referencePos):
        """
        Returns the root mean square (RMS) deviation of all ray positions
        with respect to a reference position at the end of the ray bundle.

        :referencePos: (1d numpy array of 3 floats)

        :return rms: RMS spot size (float)
        """

        o = self.raybundle.x[-1]
        (_, num_points) = np.shape(o)

        delta = o - referencePos.reshape((3, 1)) * np.ones((3, num_points))

        return np.sqrt(np.sum(np.sum(delta**2)) /
                       (num_points - 1 + numerical_tolerance))

    def getRMSspotSizeCentroid(self):
        """
        Returns the root mean square (RMS) deviation of all ray positions
        with respect to the centroid at the origin of the ray bundle.

        :return rms: RMS spot size (float)
        """
        centr = self.getCentroidPosition()
        return self.getRMSspotSize(centr)

    def getCentroidDirection(self):
        """
        Returns the arithmetic average direction of all rays at the origin of
        the ray bundle.

        :return centr: centroid unit direction vector
                        (1d numpy array of 3 floats)
        """

        directions = self.raybundle.returnKtoD()[-1]
        # (_, num_rays) = np.shape(directions)
        com_d = np.sum(directions, axis=1)
        length = np.sqrt(np.sum(com_d**2))

        return com_d / length

    def getRMSangluarSize(self, refDir):
        """
        Returns the root mean square (RMS) deviation of all ray directions
        with respect to a reference direction. The return value is approximated
        for small angluar deviations from refDir.

        :param refDir: reference direction vector (1d numpy array of 3 floats)
                       Must be normalized to unit length.

        :return rms: RMS angular size in rad (float)
        """
        # TODO: to be tested and corrected

        # sin(angle between rayDir and refDir)
        # = abs(rayDir crossproduct refDir)
        # sin(angle)**2 approx angle**2 for small
        # deviations from the reference,
        # but for large deviations the definition makes no sense, anyway

        directions = self.raybundle.returnKtoD()[-1]
        (_, num_rays) = np.shape(directions)

        cross_product = np.cross(directions, refDir, axisa=0).T

        return np.arcsin(np.sqrt(np.sum(cross_product**2) / num_rays))

    def getRMSangluarSizeCentroid(self):
        """
        Returns the root mean square (RMS) deviation of all ray directions
        with respect to the centroid direction.

        :return rms: RMS angular size in rad (float)
        """
        # TODO: to be tested
        return self.getRMSangluarSize(self.getCentroidDirection())

    def getArcLength(self):
        """
        Calculates arc length for all rays.

        :return Arc length (1d numpy array of float)
        """
        ds = np.sqrt(np.sum((self.raybundle.x[1:] - self.raybundle.x[:-1])**2,
                            axis=1))  # arc element lengths for every ray
        return np.sum(ds, axis=0)
