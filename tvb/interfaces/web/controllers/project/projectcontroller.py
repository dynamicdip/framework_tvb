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
This file will handle Projects related part.
This represents the Controller part (from MVC).

.. moduleauthor:: Lia Domide <lia.domide@codemart.ro>
.. moduleauthor:: Bogdan Neacsa <bogdan.neacsa@codemart.ro>
"""

import json
import cherrypy
import formencode

from formencode import validators
from simplejson import JSONEncoder
from cherrypy.lib.static import serve_file
from tvb.config import SIMULATOR_CLASS, SIMULATOR_MODULE
from tvb.basic.config.settings import TVBSettings as cfg
from tvb.core.entities.transient.structure_entities import DataTypeMetaData
from tvb.core.entities.transient.filtering import StaticFiltersFactory
from tvb.core.adapters.abcadapter import ABCAdapter
from tvb.core.services.projectservice import ProjectService
from tvb.core.services.importservice import ImportService
from tvb.core.services.exceptions import ServicesBaseException, ProjectServiceException
from tvb.core.services.exceptions import RemoveDataTypeException, RemoveDataTypeError
from tvb.adapters.exporters.export_manager import ExportManager
from tvb.interfaces.web.entities.context_overlay import OverlayTabDefinition
from tvb.interfaces.web.controllers.basecontroller import using_template, ajax_call
from tvb.interfaces.web.controllers.userscontroller import logged
from tvb.interfaces.web.controllers.flowcontroller import FlowController, KEY_CONTENT
import tvb.interfaces.web.controllers.basecontroller as bc
import tvb.core.entities.transient.graph_structures as graph_structures


class ProjectController(bc.BaseController):
    """
    Displays pages which deals with Project data management.
    """

    PRROJECTS_FOR_LINK_KEY = "projectsforlink"
    PRROJECTS_LINKED_KEY = "projectslinked"
    KEY_OPERATION_FILTERS = "operationfilters"

    def __init__(self):
        super(ProjectController, self).__init__()
        self.project_service = ProjectService()
        self.import_service = ImportService()


    @cherrypy.expose
    @using_template('base_template')
    @bc.settings()
    @logged()
    def index(self):
        """
        Display project main-menu. Choose one project to work with.
        """
        current_project = bc.get_current_project()
        if current_project is None:
            raise cherrypy.HTTPRedirect("/project/viewall")
        template_specification = dict(mainContent="project_submenu", title="TVB Project Menu")
        return self.fill_default_attributes(template_specification)


    @cherrypy.expose
    @using_template('base_template')
    @bc.settings()
    @logged()
    def viewall(self, create=False, page=1, selected_project_id=None, **_):
        """
        Display all existent projects. Choose one project to work with.
        """
        page = int(page)
        if cherrypy.request.method == 'POST' and create:
            raise cherrypy.HTTPRedirect('/project/editone')
        current_user_id = bc.get_logged_user().id

        ## Select project if user choose one.
        if selected_project_id is not None:
            try:
                selected_project = self.project_service.find_project(selected_project_id)
                self._mark_selected(selected_project)
            except ProjectServiceException, excep:
                self.logger.error(excep)
                self.logger.warning("Could not select project: " + str(selected_project_id))
                bc.set_error_message("Could not select project: " + str(selected_project_id))

        #Prepare template response
        prjs, pages_no = self.project_service.retrieve_projects_for_user(current_user_id, page)
        template_specification = dict(mainContent="project/viewall", title="Available TVB Projects",
                                      projectsList=prjs, page_number=page, total_pages=pages_no)
        return self.fill_default_attributes(template_specification, 'list')


    @cherrypy.expose
    @ajax_call()
    @logged()
    def projectupload(self, **data):
        """Upload Project from TVB ZIP."""
        self.logger.debug("Uploading ..." + str(data))
        try:
            upload_param = "uploadedfile"
            if upload_param in data and data[upload_param]:
                self.import_service.import_project_structure(data[upload_param], bc.get_logged_user().id)
        except ServicesBaseException, excep:
            self.logger.warning(excep.message)
            bc.set_error_message(excep.message)
        raise cherrypy.HTTPRedirect('/project/viewall')


    def _remove_project(self, project_id):
        """Private method for removing project."""
        try:
            self.project_service.remove_project(project_id)
        except ServicesBaseException, exc:
            self.logger.error("Could not delete project!")
            self.logger.exception(exc)
            bc.set_error_message(exc.message)
        prj = bc.get_current_project()
        if prj is not None and prj.id == int(project_id):
            bc.remove_from_session(bc.KEY_PROJECT)


    def _persist_project(self, data, project_id, is_create, current_user):
        """Private method to persist"""
        data = EditForm().to_python(data)
        saved_project = self.project_service.store_project(current_user, is_create, project_id, **data)
        selected_project = bc.get_current_project()
        if len(self.project_service.retrieve_projects_for_user(current_user.id, 1)) == 1:
            selected_project = saved_project
        if selected_project is None or (saved_project.id == selected_project.id):
            self._mark_selected(saved_project)


    @cherrypy.expose
    @using_template('base_template')
    @bc.settings()
    @logged()
    def editone(self, project_id=None, cancel=False, save=False, delete=False, **data):
        """
        Create or change Project. When project_id is empty we create a 
        new entity, otherwise we are to edit and existent one.
        """
        if cherrypy.request.method == 'POST' and cancel:
            raise cherrypy.HTTPRedirect('/project')
        if cherrypy.request.method == 'POST' and delete:
            self._remove_project(project_id)
            raise cherrypy.HTTPRedirect('/project/viewall')

        current_user = bc.get_logged_user()
        is_create = False
        if project_id is None or not int(project_id):
            is_create = True
            data["administrator"] = current_user.username
        else:
            current_project = self.project_service.find_project(project_id)
            if not save:
                # Only when we do not have submitted data,
                # populate fields with initial values for edit.
                data = dict(name=current_project.name, description=current_project.description)
            data["administrator"] = current_project.administrator.username
            self._mark_selected(current_project)
        data["project_id"] = project_id

        template_specification = dict(mainContent="project/editone", data=data, isCreate=is_create,
                                      title="Create new project" if is_create else "Edit " + data["name"],
                                      editUsersEnabled=(current_user.username == data['administrator']))
        try:
            if cherrypy.request.method == 'POST' and save:
                bc.remove_from_session(bc.KEY_PROJECT)
                bc.remove_from_session(bc.KEY_CACHED_SIMULATOR_TREE)
                self._persist_project(data, project_id, is_create, current_user)
                raise cherrypy.HTTPRedirect('/project/viewall')
        except formencode.Invalid, excep:
            self.logger.debug(str(excep))
            template_specification[bc.KEY_ERRORS] = excep.unpack_errors()
        except ProjectServiceException, excep:
            self.logger.debug(str(excep))
            bc.set_error_message(excep.message)
            raise cherrypy.HTTPRedirect('/project/viewall')

        all_users, members, pages = self.user_service.get_users_for_project(current_user.username, project_id)
        template_specification['usersList'] = all_users
        template_specification['usersMembers'] = [m.id for m in members]
        template_specification['usersPages'] = pages
        template_specification['usersCurrentPage'] = 1
        return self.fill_default_attributes(template_specification, 'properties')


    @cherrypy.expose
    @using_template('project/project_members')
    @logged()
    def getmemberspage(self, page, project_id=None):
        """Retrieve a new page of Project members."""
        current_name = bc.get_logged_user().username
        all_users, members, _ = self.user_service.get_users_for_project(current_name, project_id, int(page))
        edit_enabled = True
        if project_id is not None:
            current_project = self.project_service.find_project(project_id)
            edit_enabled = (current_name == current_project.administrator.username)
        return dict(usersList=all_users, usersMembers=[m.id for m in members],
                    usersCurrentPage=page, editUsersEnabled=edit_enabled)


    @cherrypy.expose
    @ajax_call()
    @logged()
    def set_visibility(self, entity_type, entity_gid, to_de_relevant):
        """
        Method used for setting the relevancy/visibility on a DataType(Group)/Operation(Group.
        """
        is_operation, is_group = False, False
        if entity_type == graph_structures.NODE_OPERATION_TYPE:
            is_group = False
            is_operation = True
        elif entity_type == graph_structures.NODE_OPERATION_GROUP_TYPE:
            is_group = True
            is_operation = True

        if is_operation:
            self.project_service.set_operation_and_group_visibility(entity_gid, eval(to_de_relevant), is_group)
        else:
            self.project_service.set_datatype_visibility(entity_gid, eval(to_de_relevant))


    @cherrypy.expose
    @using_template('base_template')
    @bc.settings()
    @logged()
    def viewoperations(self, project_id=None, page=1, filtername=None, reset_filters=None):
        """
        Display table of operations for a given project selected
        """
        if (project_id is None) or (not int(project_id)):
            raise cherrypy.HTTPRedirect('/project')

        ## Toggle filters
        filters = self.__get_operations_filters()
        selected_filters = None
        for my_filter in filters:
            if cherrypy.request.method == 'POST' and (filtername is not None):
                if reset_filters:
                    my_filter.selected = False
                elif my_filter.display_name == filtername:
                    my_filter.selected = not my_filter.selected
            if my_filter.selected:
                selected_filters = my_filter + selected_filters
        ## Iterate one more time, to update counters
        for my_filter in filters:
            if not my_filter.selected:
                new_count = self.project_service.count_filtered_operations(project_id, my_filter + selected_filters)
                my_filter.passes_count = new_count
            else:
                my_filter.passes_count = ''

        page = int(page)
        project, total_op_count, started_ops, filtered_ops, pages_no = self.project_service.retrieve_project_full(project_id,
                                                                                                selected_filters, page)
        ## Select current project
        self._mark_selected(project)

        template_specification = dict(mainContent="project/viewoperations", project=project, started_count=started_ops,
                                      title='Past operations for " ' + project.name + '"', operationsList=filtered_ops,
                                      total_op_count=total_op_count, total_pages=pages_no, page_number=page,
                                      filters=filters, no_filter_selected=(selected_filters is None))
        return self.fill_default_attributes(template_specification, 'operations')


    def __get_operations_filters(self):
        """
        Filters for VIEW_ALL_OPERATIONS page.
        Get from session currently selected filters, or build a new set of filters.
        """
        session_filtes = bc.get_from_session(self.KEY_OPERATION_FILTERS)
        if session_filtes:
            return session_filtes

        else:
            sim_group = self.flow_service.get_algorithm_by_module_and_class(SIMULATOR_MODULE, SIMULATOR_CLASS)[1]
            new_filters = StaticFiltersFactory.build_operations_filters(sim_group, bc.get_logged_user().id)
            bc.add2session(self.KEY_OPERATION_FILTERS, new_filters)
            return new_filters


    @cherrypy.expose
    @using_template("overlay_confirmation")
    @logged()
    def show_confirmation_overlay(self, **data):
        """
        Returns the content of a confirmation dialog, with a given question. 
        """
        if not data:
            data = {}
        question = data.get('question', "Are you sure ?")
        data['question'] = question
        return self.fill_default_attributes(data)
    

    @cherrypy.expose
    @using_template("overlay")
    @logged()
    def get_datatype_details(self, entity_gid, back_page='burst', exclude_tabs=None):
        """
        Returns the HTML which contains the details for the given dataType.
        """
        if exclude_tabs is None:
            exclude_tabs = []
        selected_project = bc.get_current_project()
        datatype_details, states, entity = self.project_service.get_datatype_details(entity_gid)

        ### Load DataType categories
        current_type = datatype_details.data_type
        datatype_gid = datatype_details.gid
        categories = {}
        if not entity.invalid:
            categories = self.getalgorithmsfordatatype(str(current_type), str(datatype_gid))
            categories = json.loads(categories)

        datatype_id = datatype_details.data_type_id
        is_group = False
        if datatype_details.operation_group_id is not None:
            ## Is a DataTypeGroup
            datatype_id = datatype_details.operation_group_id
            is_group = True

        ### Retrieve links
        linkable_projects_dict = self._get_linkable_projects_dict(datatype_id)
        ### Load all exporters
        exporters = {}
        if not entity.invalid:
            exporters = ExportManager().get_exporters_for_data(entity)
        is_relevant = entity.visible

        template_specification = dict()
        template_specification["entity_gid"] = entity_gid
        template_specification["nodeFields"] = datatype_details.get_ui_fields()
        template_specification["allStates"] = states
        template_specification["project"] = selected_project
        template_specification["categories"] = categories
        template_specification["exporters"] = exporters
        template_specification["datatype_id"] = datatype_id
        template_specification["isGroup"] = is_group
        template_specification["isRelevant"] = is_relevant
        template_specification["nodeType"] = 'datatype'
        template_specification["backPageIdentifier"] = back_page
        template_specification.update(linkable_projects_dict)

        overlay_class = "can-browse editor-node node-type-" + str(current_type).lower()
        if is_relevant:
            overlay_class += " node-relevant"
        else:
            overlay_class += " node_irrelevant"
        overlay_title = current_type
        if datatype_details.datatype_tag_1:
            overlay_title += " " + datatype_details.datatype_tag_1

        tabs = []
        overlay_indexes = []
        if "Metadata" not in exclude_tabs:
            tabs.append(OverlayTabDefinition("Metadata", "metadata"))
            overlay_indexes.append(0)
        if "Analyzers" not in exclude_tabs:
            tabs.append(OverlayTabDefinition("Analyzers", "analyzers", enabled=categories and 'Analyze' in categories))
            overlay_indexes.append(1)
        if "Visualizers" not in exclude_tabs:
            tabs.append(OverlayTabDefinition("Visualizers", "visualizers", enabled=categories and 'View' in categories))
            overlay_indexes.append(2)

        enable_link_tab = False
        if (not entity.invalid) and (linkable_projects_dict is not None):
            if self.PRROJECTS_FOR_LINK_KEY in linkable_projects_dict:
                projects_for_link = linkable_projects_dict[self.PRROJECTS_FOR_LINK_KEY]
                if projects_for_link is not None and len(projects_for_link) > 0:
                    enable_link_tab = True
            if self.PRROJECTS_LINKED_KEY in linkable_projects_dict:
                projects_linked = linkable_projects_dict[self.PRROJECTS_LINKED_KEY]
                if projects_linked is not None and len(projects_linked) > 0:
                    enable_link_tab = True
        if "Links" not in exclude_tabs:
            tabs.append(OverlayTabDefinition("Links", "link_to", enabled=enable_link_tab))
            overlay_indexes.append(3)
        if "Export" not in exclude_tabs:
            tabs.append(OverlayTabDefinition("Export", "export", enabled=(exporters and len(exporters) > 0)))
            overlay_indexes.append(4)
        if "Resulted Datatypes" not in exclude_tabs:
            tabs.append(OverlayTabDefinition("Resulted Datatypes", "result_dts", 
                                             enabled=self.project_service.count_datatypes_generated_from(entity_gid)))
            overlay_indexes.append(5)
        template_specification = self.fill_overlay_attributes(template_specification, "DataType Details",
                                                              overlay_title, "project/details_datatype_overlay",
                                                              overlay_class, tabs, overlay_indexes)
        template_specification['baseUrl'] = cfg.BASE_URL
        #template_specification[bc.KEY_OVERLAY_PAGINATION] = True
        #template_specification[bc.KEY_OVERLAY_PREVIOUS] = "alert(1);"
        #template_specification[bc.KEY_OVERLAY_NEXT] = "alert(2);"
        return FlowController().fill_default_attributes(template_specification)


    @cherrypy.expose
    @using_template('project/linkable_projects')
    @logged()
    def get_linkable_projects(self, datatype_id, is_group, entity_gid):
        """
        Returns the HTML which displays the link-able projects for the given dataType
        """
        template_specification = self._get_linkable_projects_dict(datatype_id)
        template_specification["entity_gid"] = entity_gid
        template_specification["isGroup"] = is_group
        return template_specification


    def _get_linkable_projects_dict(self, datatype_id):
        """" UI ready dictionary with projects in which current DataType can be linked."""
        projectsforlink, linked_projects = self.readprojectsforlink(datatype_id, True)
        if projectsforlink is not None:
            projectsforlink = json.loads(projectsforlink)
        else:
            projectsforlink = dict()
        template_specification = dict()
        template_specification[self.PRROJECTS_FOR_LINK_KEY] = projectsforlink
        template_specification[self.PRROJECTS_LINKED_KEY] = linked_projects
        template_specification["datatype_id"] = datatype_id
        return template_specification


    @cherrypy.expose
    @using_template("overlay")
    @logged()
    def get_operation_details(self, entity_gid, is_group=False, back_page='burst'):
        """
        Returns the HTML which contains the details for the given operation.
        """
        if is_group is True or is_group == "1":
            ### we have an OperationGroup entity.
            template_specification = self._compute_operation_details(entity_gid, True)
            #I expect that all the operations from a group are visible or not
            template_specification["nodeType"] = graph_structures.NODE_OPERATION_GROUP_TYPE

        else:
            ### we have a simple Operation
            template_specification = self._compute_operation_details(entity_gid)
            template_specification["displayRelevantButton"] = True
            template_specification["nodeType"] = graph_structures.NODE_OPERATION_TYPE

        template_specification["backPageIdentifier"] = back_page
        overlay_class = "can-browse editor-node node-type-" + template_specification["nodeType"]
        if template_specification["isRelevant"]:
            overlay_class += " node-relevant"
        else:
            overlay_class += " node_irrelevant"

        template_specification = self.fill_overlay_attributes(template_specification, "Details", "Operation",
                                                              "project/details_operation_overlay", overlay_class)
        return FlowController().fill_default_attributes(template_specification)


    def _compute_operation_details(self, entity_gid, is_group=False):
        """
        Returns a dictionary which contains the details for the given operation.
        """
        selected_project = bc.get_current_project()
        op_details = self.project_service.get_operation_details(entity_gid, is_group)
        operation_id = op_details.operation_id

        display_reload_btn = True
        operation = self.flow_service.load_operation(operation_id)

        if (operation.fk_operation_group is not None) or (operation.burst is not None):
            display_reload_btn = False
        else:
            op_categ_id = operation.algorithm.algo_group.fk_category
            raw_categories = self.flow_service.get_raw_categories()
            for category in raw_categories:
                if category.id == op_categ_id:
                    display_reload_btn = False
                    break
        template_specification = dict()
        template_specification["entity_gid"] = entity_gid
        template_specification["nodeFields"] = op_details.get_ui_fields()
        template_specification["operationId"] = operation_id
        template_specification["displayReloadBtn"] = display_reload_btn
        template_specification["project"] = selected_project
        template_specification["isRelevant"] = operation.visible

        return template_specification


    @cherrypy.expose
    @using_template('base_template')
    @bc.settings()
    @logged()
    def editstructure(self, project_id=None, last_selected_tab="treeTab", first_level=DataTypeMetaData.KEY_STATE,
                      second_level=DataTypeMetaData.KEY_SUBJECT, filter_input="", visibility_filter=None, **_ignored):
        """
        Return the page skeleton for displaying the project structure.
        """
        if (project_id is None) or (not int(project_id)):
            raise cherrypy.HTTPRedirect('/project')
        selected_project = self.project_service.find_project(project_id)
        self._mark_selected(selected_project)
        data = self.project_service.get_filterable_meta()
        filters = StaticFiltersFactory.build_datatype_filters(selected=visibility_filter)
        template_specification = dict(mainContent="project/structure", baseUrl=cfg.BASE_URL,
                                      title=selected_project.name,
                                      project=selected_project, data=data,
                                      lastSelectedTab=last_selected_tab, firstLevelSelection=first_level,
                                      secondLevelSelection=second_level, filterInputValue=filter_input, filters=filters)
        return self.fill_default_attributes(template_specification, 'data')


    @cherrypy.expose
    @using_template("overlay")
    @logged()
    def get_data_uploader_overlay(self, project_id):
        """
        Returns the html which displays a dialog which allows the user
        to upload certain data into the application.
        """
        upload_categories = self.flow_service.get_uploader_categories()
        upload_algorithms = self.flow_service.get_groups_for_categories(upload_categories)

        flow_controller = FlowController()
        algorithms_interface = dict()
        tabs = []

        for algo_group in upload_algorithms:
            adapter_template = flow_controller.get_adapter_template(project_id, algo_group.id, True, None)
            algorithms_interface['template_for_algo_' + str(algo_group.id)] = adapter_template
            tabs.append(OverlayTabDefinition(algo_group.displayname, algo_group.subsection_name,
                                             description=algo_group.description))

        template_specification = self.fill_overlay_attributes(None, "Upload", "Upload data for this project",
                                                              "project/upload_data_overlay", "dialog-upload", tabs)
        template_specification['uploadAlgorithms'] = upload_algorithms
        template_specification['projectId'] = project_id
        template_specification['algorithmsInterface'] = algorithms_interface

        return flow_controller.fill_default_attributes(template_specification)

    @cherrypy.expose
    @using_template("overlay")
    @logged()
    def get_project_uploader_overlay(self):
        """
        Returns the html which displays a dialog which allows the user
        to upload an entire project.
        """
        template_specification = self.fill_overlay_attributes(None, "Upload", "Project structure",
                                                              "project/upload_project_overlay",
                                                              "dialog-upload")

        return FlowController().fill_default_attributes(template_specification)


    @cherrypy.expose
    @using_template('base_template')
    @logged()
    def launchloader(self, project_id, algo_group_id, cancel=False, **data):
        """ 
        Start Upload mechanism
        """
        success_link = "/project/editstructure/" + str(project_id)
        if ((cherrypy.request.method == 'POST' and cancel) or
                not (project_id and int(project_id) and (algo_group_id is not None) and int(algo_group_id))):
            raise cherrypy.HTTPRedirect(success_link)

        project = self.project_service.find_project(project_id)
        group = self.flow_service.get_algo_group_by_identifier(algo_group_id)
        template_specification = FlowController().execute_post(project.id, success_link, success_link,
                                                               group.fk_category, group, **data)
        # In case no redirect was done until now, it means there was a problem.
        if template_specification is None or cherrypy.request.method == 'POST':
            # It is a non-recoverable problem, error message is in session.
            raise cherrypy.HTTPRedirect(success_link)
        template_specification[KEY_CONTENT] = "project/structure",
        template_specification["baseUrl"] = cfg.BASE_URL,
        template_specification[bc.KEY_TITLE] = ""
        template_specification["project"] = project
        return self.fill_default_attributes(template_specification, 'data')


    @cherrypy.expose
    @ajax_call(False)
    @logged()
    def readprojectsforlink(self, data_id, return_both=False):
        """ For a given user return a dictionary in form {project_ID: project_Name}. """
        for_link, linked = self.project_service.get_linkable_projects_for_user(bc.get_logged_user().id, data_id)

        to_link_result, linked_result = None, None
        current_project = bc.get_current_project()
        if for_link:
            to_link_result = {}
            for project in for_link:
                if project.id != current_project.id:
                    to_link_result[project.id] = project.name
            to_link_result = json.dumps(to_link_result)

        if return_both:
            if linked:
                linked_result = {}
                for project in linked:
                    linked_result[project.id] = project.name
            return to_link_result, linked_result
        return to_link_result


    @cherrypy.expose
    @ajax_call()
    @logged()
    def getalgorithmsfordatatype(self, dataname, datatype_gid):
        """
        Retrieve the available algorithms for a DataType as a JSON, will
        be used for creating menu items for the context-menu.
        We will return a dictionary, grouped by category.
        """
        algorithms = self.project_service.retrieve_launchers(dataname, datatype_gid)
        for category in algorithms:
            available_launchers = algorithms[category]
            for launcher in available_launchers:
                info = available_launchers[launcher]
                if info['part_of_group'] is False:
                    info['url'] = self.get_url_adapter(info['category'], info['id'])
                else:
                    info['url'] = '/flow/prepare_group_launch/' + datatype_gid + '/' + str(info['category']) + '/' + str(info['id'])
        return algorithms


    @cherrypy.expose
    @logged()
    def readjsonstructure(self, project_id, visibility_filter=StaticFiltersFactory.FULL_VIEW,
                          first_level="Data_State", second_level="Data_Subject", filter_value=None):
        """
        AJAX exposed method. 
        Will return the complete JSON for Project's structure, or filtered tree
        (filter only Relevant entities or Burst only Data).
        """
        selected_filter = StaticFiltersFactory.build_datatype_filters(single_filter=visibility_filter)

        project = self.project_service.find_project(project_id)
        json_structure = self.project_service.get_project_structure(project, selected_filter,
                                                                    first_level, second_level, filter_value)
        # This JSON encoding is necessary, otherwise we will get an error
        # from JSTree library while trying to load with AJAX 
        # the content of the tree.     
        encoder = JSONEncoder()
        return encoder.iterencode(json_structure)


    @cherrypy.expose
    @logged()
    def createlink(self, link_data, project_id, is_group):
        """
        Delegate the creation of the actual link to the flow service.
        """
        if not eval(is_group):
            self.flow_service.create_link([link_data], project_id)
        else:
            all_data = self.project_service.get_datatype_in_group(link_data)
            # Link all datatypes in group
            data_ids = [data.id for data in all_data]
            data_ids.append(int(link_data))
            self.flow_service.create_link(data_ids, project_id)
            group = self.project_service.get_group_by_op_group_id(link_data)
            self.flow_service.create_link([group.id], project_id)


    @cherrypy.expose
    @logged()
    def removelink(self, link_data, project_id, is_group):
        """
        Delegate the creation of the actual link to the flow service.
        """
        if not eval(is_group):
            self.flow_service.remove_link(link_data, project_id)
        else:
            all_data = self.project_service.get_datatype_in_group(link_data)
            for data in all_data:
                self.flow_service.remove_link(data.id, project_id)
            group = self.project_service.get_group_by_op_group_id(link_data)
            self.flow_service.remove_link(group.id, project_id)
            self.flow_service.remove_link(int(link_data), project_id)


    @cherrypy.expose
    @logged()
    def noderemove(self, project_id, node_gid):
        """
        AJAX exposed method, to execute operation of data removal.
        """
        try:
            if node_gid is None:
                return "Remove can only be applied on a Node with GID!"
            self.logger.debug("Removing data with GID=" + str(node_gid))
            self.project_service.remove_datatype(project_id, node_gid)
        except RemoveDataTypeError, excep:
            self.logger.error("Invalid DataType to remove!")
            self.logger.exception(excep)
            return excep.message
        except RemoveDataTypeException, excep:
            self.logger.error("Could not execute operation Node Remove!")
            self.logger.exception(excep)
            return excep.message
        except ServicesBaseException, excep:
            self.logger.error("Could not execute operation Node Remove!")
            self.logger.exception(excep)
            return excep.message
        return None


    @cherrypy.expose
    @logged()
    def updatemetadata(self, **data):
        """ Submit MetaData edited for DataType(Group) or Operation(Group). """
        try:

            self.project_service.update_metadata(data)

        except ServicesBaseException, excep:
            self.logger.error("Could not execute MetaData update!")
            self.logger.exception(excep)
            bc.set_error_message(excep.message)
            return excep.message


    @cherrypy.expose
    @logged()
    def downloaddata(self, data_gid, export_module):
        """ Export the data to a default path of TVB_STORAGE/PROJECTS/project_name """
        current_prj = bc.get_current_project()
        # Load data by GID
        entity = ABCAdapter.load_entity_by_gid(data_gid)
        # Do real export
        export_mng = ExportManager()
        file_name, file_path, delete_file = export_mng.export_data(entity, export_module, current_prj)
        if delete_file:
            # We force parent folder deletion because export process generated it.
            self.mark_file_for_delete(file_path, True)

        self.logger.debug("Data exported in file: " + str(file_path))
        return serve_file(file_path, "application/x-download", "attachment", file_name)


    @cherrypy.expose
    @logged()
    def downloadproject(self, project_id):
        """
        Export the data from a whole project.
        """
        current_project = self.project_service.find_project(project_id)
        export_mng = ExportManager()
        export_file = export_mng.export_project(current_project)

        # Register export file for delete when download complete
        # We force parent folder deletion because export process generated it.
        self.mark_file_for_delete(export_file, True)

        return serve_file(export_file, "application/x-download", "attachment")


    #methods related to data structure - graph

    @cherrypy.expose
    @logged()
    def create_json(self, item_gid, item_type, visibility_filter):
        """
        Method used for creating a JSON representation of a graph.
        """
        selected_filter = StaticFiltersFactory.build_datatype_filters(single_filter=visibility_filter)

        graph_branches = []
        project = bc.get_current_project()

        is_upload_operation = (item_type == graph_structures.NODE_OPERATION_TYPE) and \
                              (self.project_service.is_upload_operation(item_gid) or item_gid == "firstOperation")
        if is_upload_operation:
            uploader_operations = self.project_service.get_all_operations_for_uploaders(project.id)
            for operation in uploader_operations:
                dt_outputs = self.project_service.get_results_for_operation(operation.id, selected_filter)
                dt_outputs = self._create_datatype_nodes(dt_outputs)
                parent_op = self._create_operation_nodes([operation], item_gid)
                branch = graph_structures.GraphBranch([], parent_op, dt_outputs, [])
                graph_branches.append(branch)
            graph = graph_structures.GraphStructure(graph_branches)
            return graph.to_json()

        dt_inputs, parent_op, dt_outputs, op_inputs = [], [], [], []
        if item_type == graph_structures.NODE_OPERATION_TYPE:
            dt_inputs = ProjectService.get_datatype_and_datatypegroup_inputs_for_operation(item_gid, selected_filter)
            parent_op = self.project_service.load_operation_by_gid(item_gid)
            dt_outputs = self.project_service.get_results_for_operation(parent_op.id, selected_filter)
            #create graph nodes
            dt_inputs, parent_op, dt_outputs, op_inputs = self._create_nodes(dt_inputs, [parent_op],
                                                                             dt_outputs, [], item_gid)

        elif item_type == graph_structures.NODE_OPERATION_GROUP_TYPE:
            parent_op_group = self.project_service.get_operation_group_by_gid(item_gid)
            dt_inputs = self.project_service.get_datatypes_inputs_for_operation_group(parent_op_group.id,
                                                                                      selected_filter)
            datatype_group = self.project_service.get_datatypegroup_by_op_group_id(parent_op_group.id)
            datatype = self.project_service.get_datatype_by_id(datatype_group.id)

            dt_inputs = self._create_datatype_nodes(dt_inputs)
            parent_op = graph_structures.OperationGroupNodeStructure(parent_op_group.gid)
            parent_op.selected = True
            parent_op = [parent_op]
            if selected_filter.display_name == StaticFiltersFactory.RELEVANT_VIEW and datatype.visible is False:
                dt_outputs = []
            else:
                dt_outputs = self._create_datatype_nodes([datatype])

        elif item_type == graph_structures.NODE_DATATYPE_TYPE:
            selected_dt = ABCAdapter.load_entity_by_gid(item_gid)
            if self.project_service.is_datatype_group(item_gid):
                datatype_group = self.project_service.get_datatypegroup_by_gid(selected_dt.gid)
                parent_op_group = self.project_service.get_operation_group_by_id(datatype_group.fk_operation_group)
                dt_inputs = self.project_service.get_datatypes_inputs_for_operation_group(parent_op_group.id,
                                                                                          selected_filter)
                op_inputs = self.project_service.get_operations_for_datatype_group(selected_dt.id, selected_filter)
                op_inputs_in_groups = self.project_service.get_operations_for_datatype_group(selected_dt.id,
                                                                                             selected_filter,
                                                                                             only_in_groups=True)
                #create graph nodes
                dt_inputs, parent_op, dt_outputs, op_inputs = self._create_nodes(dt_inputs, [], [selected_dt],
                                                                                 op_inputs, item_gid)
                parent_op = [graph_structures.OperationGroupNodeStructure(parent_op_group.gid)]
                op_inputs_in_groups = self._create_operation_group_nodes(op_inputs_in_groups)
                op_inputs.extend(op_inputs_in_groups)
            else:
                parent_op = self.flow_service.load_operation(selected_dt.fk_from_operation)
                dt_inputs = ProjectService.get_datatype_and_datatypegroup_inputs_for_operation(parent_op.gid,
                                                                                               selected_filter)
                op_inputs = self.project_service.get_operations_for_datatype(selected_dt.gid, selected_filter)
                op_inputs_in_groups = self.project_service.get_operations_for_datatype(selected_dt.gid, selected_filter,
                                                                                       only_in_groups=True)
                dt_outputs = self.project_service.get_results_for_operation(parent_op.id, selected_filter)
                #create graph nodes
                dt_inputs, parent_op, dt_outputs, op_inputs = self._create_nodes(dt_inputs, [parent_op], dt_outputs,
                                                                                 op_inputs, item_gid)
                op_inputs_in_groups = self._create_operation_group_nodes(op_inputs_in_groups)
                op_inputs.extend(op_inputs_in_groups)

        else:
            self.logger.error("Invalid item type: " + str(item_type))
            raise Exception("Invalid item type.")

        branch = graph_structures.GraphBranch(dt_inputs, parent_op, dt_outputs, op_inputs)
        graph_branches.append(branch)
        graph = graph_structures.GraphStructure(graph_branches)
        return graph.to_json()


    def _create_nodes(self, dt_inputs, parent_op, dt_outputs, op_inputs, item_gid=None):
        """Expected a list of DataTypes, Parent Operation, Outputs, and returns NodeStructure entities."""
        dt_inputs = self._create_datatype_nodes(dt_inputs, item_gid)
        parent_op = self._create_operation_nodes(parent_op, item_gid)
        dt_outputs = self._create_datatype_nodes(dt_outputs, item_gid)
        op_inputs = self._create_operation_nodes(op_inputs, item_gid)
        return dt_inputs, parent_op, dt_outputs, op_inputs


    @staticmethod
    def _create_datatype_nodes(datatypes_list, selected_item_gid=None):
        """ Expects a list of DataTypes and returns a list of NodeStructures """
        nodes = []
        if datatypes_list is None:
            return nodes
        for data_type in datatypes_list:
            node = graph_structures.DatatypeNodeStructure(data_type.gid)
            if data_type.gid == selected_item_gid:
                node.selected = True
            nodes.append(node)
        return nodes


    @staticmethod
    def _create_operation_nodes(operations_list, selected_item_gid=None):
        """
        Expects a list of operations and returns a list of NodeStructures
        """
        nodes = []
        for operation in operations_list:
            node = graph_structures.OperationNodeStructure(operation.gid)
            if operation.gid == selected_item_gid:
                node.selected = True
            nodes.append(node)
        return nodes


    def _create_operation_group_nodes(self, operations_list, selected_item_gid=None):
        """
        Expects a list of operations that are part of some operation groups.
        """
        groups = dict()
        for operation in operations_list:
            if operation.fk_operation_group not in groups:
                group = self.project_service.get_operation_group_by_id(operation.fk_operation_group)
                groups[group.id] = group.gid
        nodes = []
        for _, group in groups.iteritems():
            node = graph_structures.OperationGroupNodeStructure(group)
            if group == selected_item_gid:
                node.selected = True
            nodes.append(node)
        return nodes


    def fill_default_attributes(self, template_dictionary, subsection='project'):
        """
        Overwrite base controller to add required parameters for adapter templates.
        """
        template_dictionary[bc.KEY_SECTION] = 'project'
        template_dictionary[bc.KEY_SUB_SECTION] = subsection
        template_dictionary[bc.KEY_INCLUDE_RESOURCES] = 'project/included_resources'
        bc.BaseController.fill_default_attributes(self, template_dictionary)
        return template_dictionary


class EditForm(formencode.Schema):
    """
    Validate creation of a Project entity. 
    """
    invalis_name_msg = "Please enter a name composed only of letters, numbers and underscores."
    name = formencode.All(validators.UnicodeString(not_empty=True),
                          validators.PlainText(messages={'invalid': invalis_name_msg}))
    description = validators.UnicodeString()
    users = formencode.foreach.ForEach(formencode.validators.Int())
    administrator = validators.UnicodeString(not_empty=False)
    project_id = validators.UnicodeString(not_empty=False)
    visited_pages = validators.UnicodeString(not_empty=False)



