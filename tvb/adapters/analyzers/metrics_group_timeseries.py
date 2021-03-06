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
Adapter that uses the traits module to generate interfaces for group of 
Analyzer used to calculate a single measure for TimeSeries.

.. moduleauthor:: Bogdan Neacsa <bogdan.neacsa@codemart.ro>
.. moduleauthor:: Stuart A. Knock <Stuart@tvb.invalid>
.. moduleauthor:: Lia Domide <lia.domide@codemart.ro>

"""
import numpy
from tvb.core.adapters.abcadapter import ABCAsynchronous, ABCAdapter
from tvb.datatypes.time_series import TimeSeries
from tvb.datatypes.mapped_values import DatatypeMeasure
from tvb.basic.traits.util import log_debug_array
from tvb.basic.traits.parameters_factory import get_traited_subclasses
from tvb.basic.filters.chain import FilterChain
from tvb.analyzers.metrics_base import BaseTimeseriesMetricAlgorithm
from tvb.basic.logger.builder import get_logger


LOG = get_logger(__name__)


class TimeseriesMetricsAdapter(ABCAsynchronous):
    """ TVB adapter for calling the VarianceNodeVariance algorithm. """
    
    _ui_name = "TimeSeries Metrics"
    _ui_description = "Compute a single number for a TimeSeries input DataType."
    _ui_subsection = "timeseries"
    available_algorithms = get_traited_subclasses(BaseTimeseriesMetricAlgorithm)
    
    
    def get_input_tree(self):
        """
        Compute interface based on introspected algorithms found.
        """
        input_tree = [{'name': 'time_series', 'label' : 'TimeSeries to be analyzed: ', 
                       'type' : TimeSeries, 'required' : True,
                       'conditions' : FilterChain(fields=[FilterChain.datatype + '._nr_dimensions'], 
                                                  operations=["=="], values=[4]),
                       'description' : 'Input TimeSeries on which to launch available metrics.' }]
        
        algo_names = self.available_algorithms.keys()
        options = []
        for name in algo_names:
            options.append({ABCAdapter.KEY_NAME : name, ABCAdapter.KEY_VALUE : name})
        input_tree.append({'name' : 'algorithms', 'label' : 'Selected metrics to be applied',
                           'type' : ABCAdapter.TYPE_MULTIPLE, 'required' : False, 'options': options,
                           'description' : 'The selected metric algorithms will be applied on the input TimeSeries'})
        return input_tree
    
    
    def get_output(self):
        return [DatatypeMeasure]
    
    
    def configure(self, time_series, algorithms = None):
        """
        Store the input shape to be later used to estimate memory usage.
        """
        self.input_shape = time_series.read_data_shape()


    def get_required_memory_size(self, **kwargs):
        """
        Return the required memory to run this algorithm.
        """
        input_size = numpy.prod(self.input_shape) * 8.0
        return input_size   
    
    
    def get_required_disk_size(self, **kwargs):
        """
        Returns the required disk size to be able to run the adapter (in kB).
        """
        return 0
    
    
    def launch(self, time_series, algorithms = None):
        """ 
        Launch algorithm and build results.

        :param time_series: the time series on which the algorithms are run
        :param algorithms:  the algorithms to be run for computing measures on the time series
        :type  algorithms:  any subclass of BaseTimeseriesMetricAlgorithm (KuramotoIndex, \
                    GlobalVariance, VarianceNodeVariance)
        :rtype: `DatatypeMeasure`
        """
        if algorithms is None:
            algorithms = self.available_algorithms.keys()
        shape = time_series.read_data_shape()
        log_debug_array(LOG, time_series, "time_series")
        
        metrics_results = {}
        for algorithm_name in algorithms:
            ##------------- NOTE: Assumes 4D, Simulator timeSeries. --------------##
            node_slice = [slice(shape[0]), slice(shape[1]), slice(shape[2]), slice(shape[3])]
            
            ##---------- Iterate over slices and compose final result ------------##
            unstored_ts = TimeSeries(use_storage=False)
            
            unstored_ts.data = time_series.read_data_slice(tuple(node_slice))
            
            ##-------------------- Fill Algorithm for Analysis -------------------##
            algorithm = self.available_algorithms[algorithm_name](time_series=unstored_ts)
            ## Validate that current algorithm's filter is valid.
            if (algorithm.accept_filter is not None and 
                not algorithm.accept_filter.get_python_filter_equivalent(time_series)):
                LOG.warning('Measure algorithm will not be computed because of incompatibility on input. '
                            'Filters failed on algo: '+ str(algorithm_name))
                continue
            else:
                LOG.debug("Applying measure: "+ str(algorithm_name))
                
            unstored_result = algorithm.evaluate()
            ##----------------- Prepare a Float object for result ----------------##
            metrics_results[algorithm_name] = unstored_result
            
        result = DatatypeMeasure(analyzed_datatype = time_series, storage_path=self.storage_path, 
                                 data_name = self._ui_name, metrics=metrics_results)
        return result


