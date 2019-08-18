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

import logging
found_jsonpickle = True
try:
    import jsonpickle
except ImportError:
    found_jsonpickle = False

from pyrateoptics.raytracer.optical_system import OpticalSystem


logging.basicConfig(level=logging.DEBUG)

# definition of optical system

s = OpticalSystem.p()

if found_jsonpickle:
    print("pickle dump")
    frozen = jsonpickle.encode(s)

    with open('optical_sys.jpkl', 'w') as output:
        output.write(frozen)

# WARNING: code is operational, but not tested
