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
.. moduleauthor:: Bogdan Neacsa <bogdan.neacsa@codemart.ro>
"""

import tvb.core.services.eventhandler as eventhandler
from tvb.basic.logger.builder import get_logger
from tvb.basic.config.settings import TVBSettings as cfg
from tvb.core.utils import get_matlab_executable
from tvb.core.entities.storage import dao


LOGGER = get_logger(__name__)
PAGE_SIZE = 20
EVENT_FILE_IDENTIFIER = "CodeVersionsManager.update.4455"


def update():
    """
    Update TVB code to SVN revision version 4455.
    This update was done for release 1.0.2.
    """
    projects_count = dao.get_all_projects(is_count=True)
    
    for page_start in range(0, projects_count, PAGE_SIZE):
        projects_page = dao.get_all_projects(page_start=page_start, page_end=min(page_start +PAGE_SIZE, projects_count))
        
        for project in projects_page:
            try:
                eventhandler.handle_event(EVENT_FILE_IDENTIFIER, dao.get_system_user(), project)
            except Exception, excep:
                LOGGER.exception(excep)
                
    cfg.add_entries_to_config_file({cfg.KEY_MATLAB_EXECUTABLE : get_matlab_executable()})
    
    
    