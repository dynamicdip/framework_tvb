# -*- coding: utf-8 -*-
#
#
# TheVirtualBrain-Framework Package. This package holds all Data Management, and 
# Web-UI helpful to run brain-simulations. To use it, you also need do download
# TheVirtualBrain-Scientific Package (for simulators). See content of the
# documentation-folder for more details. See also http://www.thevirtualbrain.org
#
# (c) 2012-2013, Baycrest Centre for Geriatric Care ("Baycrest")
#
# This program is free software; you can redistribute it and/or modify it under 
# the terms of the GNU General Public License version 2 as published by the Free
# Software Foundation. This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
# License for more details. You should have received a copy of the GNU General 
# Public License along with this program; if not, you can download it here
# http://www.gnu.org/licenses/old-licenses/gpl-2.0
#
#
#   CITATION:
# When using The Virtual Brain for scientific publications, please cite it as follows:
#
#   Paula Sanz Leon, Stuart A. Knock, M. Marmaduke Woodman, Lia Domide,
#   Jochen Mersmann, Anthony R. McIntosh, Viktor Jirsa (2013)
#       The Virtual Brain: a simulator of primate brain network dynamics.
#   Frontiers in Neuroinformatics (in press)
#
#

"""
.. Ionel Ortelecan <ionel.ortelecan@codemart.ro>
"""

from tvb.core.adapters.abcadapter import ABCAdapter
from tvb.basic.traits.types_mapped import MappedType



class StoreAdapter(ABCAdapter):
    """
    The purpose of this adapter is only to allow you to
    store into the db a list of data types.
    """
    list_of_entities_to_store = []

    def __init__(self, list_of_entities_to_store):
        """
        Expacts a list of 'DataType' instances.
        """
        ABCAdapter.__init__(self)
        if (list_of_entities_to_store is None 
            or not isinstance(list_of_entities_to_store, list) 
            or len(list_of_entities_to_store) == 0):
            raise Exception("The adapter expacts a list of entities")

        self.list_of_entities_to_store = list_of_entities_to_store


    def get_input_tree(self):
        return []

    def get_required_memory_size(self, **kwargs):
        """
        Return the required memory to run this algorithm.
        """
        # Don't know how much memory is needed.
        return -1
    
    def get_required_disk_size(self, **kwargs):
        """
        Returns the required disk size to be able to run the adapter.
        """
        return 0

    def get_output(self):
        """
        Describes the outputs of the launch method.
        """
        return [MappedType]


    def launch(self):
        """
        Saves in the db the list of entities passed to the constructor.
        """
        return self.list_of_entities_to_store
    
    
    
    