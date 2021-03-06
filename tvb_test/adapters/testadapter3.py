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
Created on Jul 21, 2011

.. moduleauthor:: Bogdan Neacsa <bogdan.neacsa@codemart.ro>
"""

from tvb.core.adapters.abcadapter import ABCAdapter, ABCAsynchronous, ABCSynchronous
from tvb_test.datatypes.datatype1 import Datatype1
from tvb_test.datatypes.datatype2 import Datatype2
from tvb.datatypes.arrays import MappedArray
from tvb.datatypes.mapped_values import ValueWrapper


class TestAdapter3(ABCAsynchronous):
    """
    This class is used for testing purposes.
    It will be used as an adapter for testing Groups of operations. For ranges to work, it need to be asynchronous.
    """ 
        
    def get_input_tree(self):
        return [    {'name': 'param_1', 'label': 'Param 1:', 'type': MappedArray, 'datatype': True},
                    {'name': 'param_2', 'label': 'Param 2:', 'type': MappedArray, 'datatype': True},
                    {'name': 'param_3', 'label': 'Param 3:', 'type': MappedArray, 'datatype': True},
                    {'name': 'param_4', 'label': 'Param 4:', 'type': ValueWrapper, 'datatype': True},
                    {'name': 'param_5', 'label': 'Param 5:', 'type':'int', 'default':'0'},
                    {'name': 'param_6', 'label': 'Param 6:', 'type':'int', 'default':'0'},
                    {'name':'test', 'type':Datatype1, 'default':'0'}
                ]
                
    def get_output(self):
        return [Datatype2]
    
    def get_required_memory_size(self, **kwargs):
        return -1
    
    def get_required_disk_size(self, **kwargs):
        """
        Returns the required disk size to be able to run the adapter.
        """
        return 0
        
    def launch(self, **kwargs):
        result = Datatype2()
        if 'param_5' in kwargs:
            result.row1 = str(kwargs['param_5'])
        if 'param_6' in kwargs:
            result.row2 = str(kwargs['param_6'])
        result.storage_path = self.storage_path
        result.string_data = ["data"]
        return result



class TestAdapterHugeMemoryRequired(ABCAdapter):
    """
    Adapter used for testing launch when a lot of memory is required.
    """
    
    def __init__(self):
        ABCAdapter.__init__(self)
        
    def get_input_tree(self):
        return [{'name':'test', 'type':'int', 'default':'0'}]
                
    def get_output(self):
        return []
    
    def get_required_memory_size(self, **kwargs):
        """
        Huge memory requirement, should fail launch.
        """
        return 999999999999999
    
    def get_required_disk_size(self, **kwargs):
        """
        Returns the required disk size to be able to run the adapter.
        """
        return 0
    
    def launch(self, test):
        str(test)


class TestAdapterHDDRequired(ABCSynchronous):
    """
    Adapter used for testing launch when a lot of memory is required.
    """
    
    def __init__(self):
        ABCAdapter.__init__(self)
        
    def get_input_tree(self):
        return [{'name':'test', 'type':'int', 'default':'0'}]
                
    def get_output(self):
        return [Datatype2]
    
    def get_required_memory_size(self, **kwargs):
        """
        Huge memory requirement, should fail launch.
        """
        return 0
    
    def get_required_disk_size(self, **kwargs):
        """
        Returns the required disk size to be able to run the adapter.
        """
        return int(kwargs['test']) * 8 / 2 ** 10
    
    def launch(self, test):
        """
        Mimics launching with a lot of memory usage

        :param test: should be a very large integer; the larger, the more memory is used
        :returns: a `Datatype2` object, with big string_data
        """
        result = Datatype2()
        result.row1 = 'param_5'
        result.row2 = 'param_6'
        result.storage_path = self.storage_path
        res_array = []
        for _ in range(int(test)):
            res_array.append("data")
        result.string_data = res_array
        return result
    
class TestAdapterNoMemoryImplemented(ABCAdapter):
    """
    Test adapter for TVB capability to launch algorithm with memory constraints.
    """
    
    def __init__(self):
        ABCAdapter.__init__(self)
        
    def get_input_tree(self):
        return [{'name':'test', 'type':'int', 'default':'0'}]
                
    def get_output(self):
        return []
    
    def launch(self, test):
        str(test)
    
    
    
    