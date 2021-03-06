#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pyrate - Optical raytracing based on Python

Copyright (C) 2014-2020
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

import uuid
import json

from pprint import pformat

import yaml


from .log import BaseLogger
from .iterators import SerializationIterator
from .optimizable_variables_pool import OptimizableVariablesPool

from ..raytracer.localcoordinates import LocalCoordinates
from ..raytracer.surface import Surface
from ..raytracer.surface_shape import (Asphere,
                                       Biconic,
                                       Conic,
                                       Cylinder,
                                       GridSag,
                                       XYPolynomials,
                                       ZernikeFringe,
                                       ZernikeANSI)
from ..raytracer.aperture import (BaseAperture,
                                  CircularAperture,
                                  RectangularAperture)
from ..raytracer.optical_element import OpticalElement
from ..raytracer.optical_system import OpticalSystem
from ..raytracer.material.material_glasscat import CatalogMaterial
from ..raytracer.material.material_isotropic import ConstantIndexGlass


class Serializer(BaseLogger):
    """
    Class which is able to serialize a ClassWithOptimizableVariables
    in a recursive manner.
    """
    def __init__(self, class_instance, name=""):
        super(Serializer, self).__init__(name=name)
        self.class_instance = class_instance
        self.serialize()

    def setKind(self):
        self.kind = "serializer"

    def serialize(self):
        """
        Serialize class which was provided to constructor.
        """
        default_to_be_removed = ["annotations",
                                 "list_observers",
                                 "serializationfilter"]
        serialization = SerializationIterator(self.class_instance,
                                              remove=default_to_be_removed)
        serialization.collectStructure(remove=default_to_be_removed)
        optimizable_variables_pool = OptimizableVariablesPool(
            serialization.variables_dictionary)
        functionobjects_pool = optimizable_variables_pool.\
            generate_functionobjects_pool()

        self.serialization = [
            serialization.dictionary,
            dict([(k,
                   SerializationIterator(v,
                                         remove=default_to_be_removed
                                        ).dictionary
                  ) for (k, v) in serialization.classes_dictionary.items()]
                ),
            optimizable_variables_pool.to_dictionary(),
            functionobjects_pool.to_dictionary()
        ]

    def save_json(self, filename):
        """
        Save class in json.
        """
        mydump = self.serialization
        with open(filename, "wt") as filep:
            json.dump(mydump, filep, indent=4)

    def save_yaml(self, filename):
        """
        Save class in yaml
        """
        mydump = self.serialization
        with open(filename, "wt") as filep:
            yaml.dump(mydump, filep)


class Deserializer(BaseLogger):
    """
    Class which is able to reconstruct a ClassWithOptimizableVariables
    from a yaml or json file.
    """
    def __init__(self, serialization_list,
                 source_checked, variables_checked, name="",
                 register_classes=None):
        super(Deserializer, self).__init__(name=name)
        self.serialization_list = serialization_list
        self.classes_dictionary = {
            "shape_Conic": Conic,
            "shape_Cylinder": Cylinder,
            "shape_Asphere": Asphere,
            "shape_Biconic": Biconic,
            "shape_XYPolynomials": XYPolynomials,
            "shape_GridSag": GridSag,
            "shape_ZernikeFringe": ZernikeFringe,
            "shape_ZernikeANSI": ZernikeANSI,
            "localcoordinates": LocalCoordinates,
            "constantindexglass": ConstantIndexGlass,
            "opticalelement": OpticalElement,
            "opticalsystem": OpticalSystem,
            "surface": Surface,
            "material_from_catalog": CatalogMaterial,
            "aperture": BaseAperture,
            "aperture_Circular": CircularAperture,
            "aperture_Rectangular": RectangularAperture
            }
        if register_classes is not None:
            for (kind_name, class_name) in register_classes:
                self.classes_dictionary[kind_name] = class_name

        self.deserialize(source_checked, variables_checked)

    def is_uuid(self, uuidstr):
        """
        Check whether a variable is a valid uuid. This could be improved,
        once in the classes appear regular uuids which have nothing to do
        with the serialization process.
        """
        if isinstance(uuidstr, str):
            try:
                uuid.UUID(uuidstr)
            except ValueError:
                return False
            else:
                return True
        else:
            return False

    def deserialize(self, source_checked, variables_checked):
        """
        Convert the list obtained from a file or another source back
        into a class with optimizable variables, via a recursive
        reconstruction of subclasses. Source checked and variables checked
        are to be set to True by the user.
        """

        def is_structure_free_of_uuids(structure_dict):
            """
            Checks whether structure dict is free of uuids
            If this is the case the reconstruction process is finished.
            Else there are either unreconstructed variables or classes
            in this structure dict.
            """

            def free_of_uuid(var):
                """
                This function is called recursively to verify that a
                given nested structure is free of UUIDs as checked by
                is_uuid.
                """
                if self.is_uuid(var):
                    return False
                elif isinstance(var, list):
                    return all([free_of_uuid(v) for v in var])
                elif isinstance(var, dict):
                    return all([free_of_uuid(v) for v in var.values()])
                else:
                    return True
            return free_of_uuid(structure_dict)

        def reconstruct_variables(structure_dict,
                                  reconstructed_variables_dict):
            """
            This function is called to reconstruct variables from a pool
            with in a necessary sub class of a class which is to be
            reconstructed. It uses structure_dict of the class to be
            reconstructed and returns a modified version where the
            variables UUIDs are substituted by the appropriate objects.
            """

            def reconstruct_recursively(variable,
                                        reconstructed_variables_dict):
                """
                Traverse variables and reconstruct them if necessary.
                """
                if self.is_uuid(variable):
                    if variable in reconstructed_variables_dict:
                        return reconstructed_variables_dict[variable]
                    else:
                        return variable
                elif isinstance(variable, list):
                    return [
                        reconstruct_recursively(
                            part,
                            reconstructed_variables_dict)
                        for part in variable]
                elif isinstance(variable, dict):
                    return dict(
                        [
                            (key, reconstruct_recursively(
                                part,
                                reconstructed_variables_dict))
                            for (key, part) in variable.items()])
                else:
                    return variable

            new_structure_dict = reconstruct_recursively(
                structure_dict,
                reconstructed_variables_dict)

            return new_structure_dict

        def reconstruct_class(class_to_be_reconstructed, subclasses_dict,
                              reconstructed_variables_dict):
            """
            Main reconstruction function. Is to be called recursively in
            the tree. Reconstructs first in-class variables by accessing
            the reconstructed_variables_dict. In a second step, it
            reconstructs the whole class by setting attributes from the
            structure dictionary, sets the annotations from the annotations
            dictionary and finally constructs the ClassWithOptimizableVariables
            object.
            """

            def reconstruct_subclasses(structure_dict, subclasses_dict,
                                       reconstructed_variables_dict):
                """
                This function reconstructs necessary subclasses of a given
                class to be reconstructed. This is done by first reconstructing
                their variables via the function reconstruct_variables and
                afterwards parsing the structure for other classes which are
                also reconstructed by using the sub function
                reconstruct_recursively. Modified structure dict, annotations
                and all other things are to be used to construct a
                ClassWithOptimizableVariables.
                """

                def reconstruct_recursively(variable, subclasses_dict,
                                            reconstructed_variables_dict):
                    """
                    Reconstruct class recursively from subclasses_dict and
                    reconstructed_variables.
                    """
                    if self.is_uuid(variable) and variable in subclasses_dict:
                        return reconstruct_class(
                            subclasses_dict[variable],
                            subclasses_dict,
                            reconstructed_variables_dict)
                    elif isinstance(variable, list):
                        return [reconstruct_recursively(part,
                                                        subclasses_dict,
                                                        reconstructed_variables_dict)
                                for part in variable]
                    elif isinstance(variable, dict):
                        return dict([(key,
                                      reconstruct_recursively(part,
                                                              subclasses_dict,
                                                              reconstructed_variables_dict))
                                     for (key, part) in variable.items()])
                    else:
                        return variable

                new_structure_dict = reconstruct_recursively(
                    structure_dict,
                    subclasses_dict,
                    reconstructed_variables_dict)
                return new_structure_dict

            def show_dict(mydict):
                """
                Show dictionary in a beautiful fashion.
                """
                strlimit = 10
                return "\n".join([str(key) + ": " +
                                  (str(val)[:strlimit] if len(str(val)) > strlimit else str(val))
                                  for key, val in mydict.items()])

            if not isinstance(class_to_be_reconstructed, dict):
                self.debug("Class was already modified or reconstructed:")
                self.debug("Is not of type dict, leaving unchanged.")
                return class_to_be_reconstructed
            self.debug("RECONSTRUCT SUB CLASSES ENTER:")
            self.debug("Reconstructing structure dictionary")
            structure_dict = class_to_be_reconstructed["structure"]
            # TODO: check whether class_to_be_reconstructed["unique_id"]
            # is in structure_dict. Remove this and append
            # it after reconstruction
            self.debug(str(class_to_be_reconstructed))
            self.debug("Class reconstructed name: " + class_to_be_reconstructed["name"])
            self.debug("Class reconstructed structure dict:\n" + pformat(structure_dict))
            self.debug("Reconstructing optimizable variables")
            structure_dict = reconstruct_variables(
                structure_dict,
                reconstructed_variables_dict)
            self.debug("keys reconstructed_variables_dict: " +
                       show_dict(reconstructed_variables_dict))
            self.debug("Reconstructing sub classes")

            self.debug("keys structure_dict: " + show_dict(structure_dict))
            self.debug("keys subclasses_dict: " + show_dict(subclasses_dict))
            # TODO: this does not work as intended
            # TODO: the main problem are parent variables in subclasses
            # their reconstruction has to be postponed
            if class_to_be_reconstructed["unique_id"] in subclasses_dict:
                self.debug("Found class to be reconstructed id in subclasses!")
                self.debug("Removed the following item from subclass dictionary:")
                self.debug(str(subclasses_dict.pop(
                    class_to_be_reconstructed["unique_id"])
                              )
                          )
                # TODO: what if the class is still needed?
            structure_dict = reconstruct_subclasses(structure_dict,
                                                    subclasses_dict,
                                                    reconstructed_variables_dict)
            found_no_uuids = is_structure_free_of_uuids(structure_dict)
            self.debug("No UUIDs in structure dict left? " +
                       "(Shouldn\'t be after reconstruction!) " +
                       str(found_no_uuids))
            if not found_no_uuids:
                self.info("Found some uuids anyway.")
                self.debug("Second attempt to reconstruct them.")
                structure_dict = reconstruct_subclasses(
                    structure_dict,
                    subclasses_dict,
                    reconstructed_variables_dict)
                self.debug(pformat(subclasses_dict))
                found_no_uuids_now = is_structure_free_of_uuids(
                    structure_dict)
                if not found_no_uuids_now:
                    self.debug("Found uuids still after second attempt " +
                               "of reconstruction.")
                    self.debug("GIVING UP!")
                else:
                    self.debug("No UUIDs left after second attempt. Pheew!")
            else:
                self.info("Structure properly reconstructed.")

            self.debug("Generating final object (constructor)")
            kind = class_to_be_reconstructed["kind"]
            name = class_to_be_reconstructed["name"]
            anno = class_to_be_reconstructed["annotations"]

            self.debug("Name: " + name)
            self.debug("Kind: " + kind)

            self.debug("Annotations")

            self.debug(pformat(anno))

            self.debug("Creating attributes")

            self.debug(pformat(structure_dict))

            myclass = self.classes_dictionary[kind](
                anno,
                structure_dict, name=name)
            self.info("Reconstructed " + kind + " " + name)
            # subclasses_dict[class_to_be_reconstructed["unique_id"]] = myclass
            self.debug("RECONSTRUCT SUB CLASSES LEAVE:")
            return myclass

        # ===================================
        # STARTING ACTUAL DESERIALIALIZATION CODE
        # ===================================

        (class_to_be_deserialized, subclasses_dict,
         optimizable_variables_pool_dict, functionobjects_pool_dict) =\
            self.serialization_list

        self.debug("Deserializing class")
        self.debug(pformat(class_to_be_deserialized))
        self.debug(pformat(subclasses_dict))

        # Reconstruct the variables pool by its own reconstruction functions.
        # Then reconstruct the class to be reconstructed by calling
        # reconstruct_class in a recursive manner. Return the final object.

        self.info("Deserializing variables")
        optimizable_variables_pool = OptimizableVariablesPool.from_dictionary(
            optimizable_variables_pool_dict,
            functionobjects_pool_dict, source_checked, variables_checked)

        self.info("Inserting variables into subclasses_dict")
        new_subclasses_dict = {}
        for (key, value) in subclasses_dict.items():
            newvalue = value.copy()
            newvalue["structure"] = reconstruct_variables(
                newvalue["structure"],
                optimizable_variables_pool.variables_pool)
            new_subclasses_dict[key] = newvalue
        self.debug(pformat(new_subclasses_dict))
        self.info("Reconstructing classes with no recursive structure")
        for (key, value) in new_subclasses_dict.items():
            if is_structure_free_of_uuids(value["structure"]):
                new_subclasses_dict[key] = reconstruct_class(
                    new_subclasses_dict[key], {},
                    optimizable_variables_pool.variables_pool)
        self.debug(pformat(new_subclasses_dict))

        self.debug("Reconstructing class")
        mynewobject = reconstruct_class(class_to_be_deserialized,
                                        new_subclasses_dict,
                                        optimizable_variables_pool.variables_pool)
        self.info("Returning Class")
        self.class_instance = mynewobject

    @staticmethod
    def load_json(filename, source_checked, variables_checked,
                  name="", register_classes=None):
        """
        Load class from json file.
        """
        mylist = None
        with open(filename, "rt") as filep:
            mylist = json.load(filep)
        return Deserializer(mylist,
                            source_checked,
                            variables_checked, name=name,
                            register_classes=register_classes).class_instance

    @staticmethod
    def load_yaml(filename, source_checked, variables_checked,
                  name="", register_classes=None):
        """
        Load class from yaml file.
        """
        mylist = None
        with open(filename, "rt") as filep:
            mylist = yaml.load(filep)
        return Deserializer(mylist,
                            source_checked,
                            variables_checked, name=name,
                            register_classes=register_classes).class_instance
