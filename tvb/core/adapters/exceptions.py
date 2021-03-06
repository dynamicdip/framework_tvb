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
.. moduleauthor:: Lia Domide <lia.domide@codemart.ro>
"""
from tvb.basic.traits.exceptions import TVBException

class LaunchException(TVBException):
    """
    Exception class for problem with launching an operation.
    """
    def __init__(self, message, parent_exception = None):
        TVBException.__init__(self, message, parent_exception)

 
class InvalidParameterException(LaunchException):
    """
    Exception class for parameter validation issue.
    """
    pass
        
        
class IntrospectionException(TVBException):
    """
    Exception class for problems when introspection failed.
    """
    def __init__(self, message):
        TVBException.__init__(self, message)


class XmlParserException(IntrospectionException):
    """
    Exception class for problems when parsing xml files.
    """
    def __init__(self, message):
        IntrospectionException.__init__(self, message)


class ParseException(TVBException):
    """
    Exception class for problem with parsing files an operation.
    """
    def __init__(self, message):
        TVBException.__init__(self, message)

        
class MethodUnimplementedException(TVBException):
    """
    Exception class raised when an 'abstact' method is not implemented in any subclasses.
    """
    def __init__(self, message):
        TVBException.__init__(self, message)


class NoMemoryAvailableException(TVBException):
    """
    Exception class raised when an adapter requires more memory that is available on machine.
    """
    def __init__(self, message):
        TVBException.__init__(self, message)