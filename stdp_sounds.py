#!/usr/bin/env python

"""
Set up a network with:
- an input layer of excitatory neurons
- one or more subsequent layers of excitatory neurons
  with non-plastic lateral inhibitory connections so that
  only one neuron can fire at a time
- plastic connections between layers
"""

from __future__ import print_function, division
import os.path
import pickle
import brian2 as b2
import numpy as np
import matplotlib.pyplot as plt

import modules.utils as utils
import modules.synapses as synapses
import modules.equations as eqs
import modules.neurons as ns
import modules.params as ps
import modules.tests

from pylab import *

def init_neurons(input_spikes, layer_n_neurons, neuron_params):
    """
    Initialise neuron group objects.
    """
    neurons = {}

    n_inputs = 513
    neurons['input'] = ns.prespecified_spike_neurons(
        n_neurons=n_inputs,
        spike_indices=input_spikes['indices'],
        spike_times=input_spikes['times']
    )

    # excitatory neurons
    neurons['layer1e'] = ns.excitatory_neurons(
        n_neurons=layer_n_neurons,
        params=neuron_params
    )

    # inhibitory neurons
    neurons['layer1i'] = ns.inhibitory_neurons(
        n_neurons=layer_n_neurons,
        params=neuron_params
    )

    # visualisation neurons
    if not neuron_params['no_vis']:
        neurons['layer1vis'] = ns.visualisation_neurons(
            n_neurons=layer_n_neurons,
            params=neuron_params
        )

    return neurons

def init_connections(neurons, connection_params):
    """
    Initialise synaptic connections between neurons and between layers.
    """

    connections = {}

    # input to layer 1 connections

    source = neurons['input']
    target = neurons['layer1e']
    connections['input-layer1e'] = synapses.stdp_ex_synapses(
        source=neurons['input'],
        target=neurons['layer1e'],
        connectivity=True, # all-to-all connectivity
        params=connection_params
    )

    # load saved weights, if they exist

    if os.path.exists('input-layer1e-weights.pickle'):
        with open('input-layer1e-weights.pickle', 'rb') as pickle_file:
            pickle_obj = pickle.load(pickle_file)
            connections['input-layer1e'].w = pickle_obj[0]
    else:
        connections['input-layer1e'].w = 'rand() * 0.4'
        weights = np.array(connections['input-layer1e'].w)
        with open('input-layer1e-weights.pickle', 'wb') as pickle_file:
            pickle.dump(weights, pickle_file)

    # excitatory to inhibitory
    connections['layer1e-layer1i'] = synapses.nonplastic_synapses(
        source=neurons['layer1e'],
        target=neurons['layer1i'],
        connectivity='i == j',
        synapse_type='excitatory'
    )
    connections['layer1e-layer1i'].w = connection_params['ex-in-w']

    # inhibitory to excitatory
    connections['layer1i-layer1e'] = synapses.nonplastic_synapses(
        source=neurons['layer1i'],
        target=neurons['layer1e'],
        connectivity='i != j',
        synapse_type='inhibitory'
    )
    connections['layer1i-layer1e'].w = connection_params['in-ex-w']

    # excitatory to visualisation
    if ('layer1vis') in neurons:
        connections['layer1e-layer1vis'] = synapses.visualisation_synapses(
            source=neurons['layer1e'],
            target=neurons['layer1vis'],
            connectivity='i == j',
        )

    return connections

def init_monitors(neurons, connections, monitor_params):
    """
    Initialise objects monitoring state variables in the network.
    """

    monitors = {
        'spikes': {},
        'neurons': {},
        'connections': {}
    }

    for layer in ['input', 'layer1e']:
        monitors['spikes'][layer] = b2.SpikeMonitor(neurons[layer])

    if 'monitors_dt' not in monitor_params:
        dt = None
    else:
        dt = monitor_params['monitors_dt']

    monitors['neurons']['layer1e'] = b2.StateMonitor(
        neurons['layer1e'],
        ['v', 'ge', 'max_ge', 'theta'],
        # record=True is currently broken for standalone simulations
        record=range(len(neurons['layer1e'])),
        dt=dt
    )
    if 'layer1vis' in neurons:
        monitors['neurons']['layer1vis'] = b2.StateMonitor(
            neurons['layer1vis'],
            ['v'],
            # record=True is currently broken for standalone simulations
            record=range(len(neurons['layer1vis'])),
            dt=b2.second/60
        )

    conn = connections['input-layer1e']
    n_connections = len(conn.target) * len(conn.source)
    monitors['connections']['input-layer1e'] = b2.StateMonitor(
        connections['input-layer1e'],
        ['w', 'post', 'pre'],
        record=range(n_connections),
        dt=dt
    )

    return monitors

def run_simulation(run_params, neurons, connections, monitors, run_id):
    """
    Run the simulation using all the objects created so far.
    """

    net = b2.Network()
    for group in neurons:
        net.add(neurons[group])
    for connection in connections:
        net.add(connections[connection])
    for mon_type in monitors:
        for neuron_group in monitors[mon_type]:
            net.add(monitors[mon_type][neuron_group])

    if run_params['no_standalone']:
        net.run(run_params['run_time'], report='text')
    else:
        print("Preparing simulation...")
        net.run(run_params['run_time'], report='text')
        print("done!")

        print("Building and running simulation...")
        if os.name == 'nt':
            build_dir = 'C:\\temp\\'
        else:
            build_dir = '/tmp/'
        build_dir += run_id
        b2.device.build(
            directory=build_dir,
            compile=True, run=True, debug=False
        )
        print("done!")

    return net

def load_input(run_params):
    """
    Load spikes to be used as output from input layer.
    """

    pickle_filename = run_params['input_spikes_filename']
    with open(pickle_filename, 'rb') as pickle_file:
        (input_spike_times, input_spike_indices) = pickle.load(pickle_file)
    input_spike_times = input_spike_times * b2.second

    spikes = {}
    spikes['indices'] = input_spike_indices
    spikes['times'] = input_spike_times

    return spikes

def analyse_results(monitors, connections, run_id, analysis_params):
    """
    Analyse results of simulation and plot graphs.
    """

    if len(monitors['spikes']['layer1e']) == 0:
        print("No spikes detected; not analysing")
        return

    if analysis_params['note_separation'] is not None and \
            analysis_params['n_notes'] is not None:
        end_time = max(monitors['spikes']['layer1e'].t)
        utils.analyse_note_responses(
            monitors['spikes']['layer1e'],
            note_length=analysis_params['note_separation'],
            n_notes=analysis_params['n_notes'],
            from_time=end_time/2
        )

    if not analysis_params['batch']:
        plt.ion()

    plt.figure()
    for i, group in enumerate(monitors['spikes']):
        plt.subplot(len(monitors['spikes']), 1, i+1)
        plt.title('Group "%s" spikes' % group)
        plt.plot(
            monitors['spikes'][group].t/b2.second,
            monitors['spikes'][group].i,
            'k.',
            markersize=2
        )
        min_i = np.amin(monitors['spikes'][group].i)
        max_i = np.amax(monitors['spikes'][group].i)
        plt.ylim([min_i-1, max_i+1])
        key0 = monitors['spikes'].keys()[0]
        max_t = np.amax(monitors['spikes'][key0].t/b2.second,)
        plt.xticks(np.arange(0, max_t, 0.5))
        plt.grid()

    plt.xlabel("Time (seconds)")
    plt.ylabel("Neuron no.")
    plt.subplot(len(monitors['spikes']), 1, 1)
    plt.title("Run '%s'" % run_id)
    plt.tight_layout()

    firing_neurons = set(monitors['spikes']['layer1e'].i)
    utils.plot_state_var(
        monitors['neurons']['layer1e'],
        monitors['neurons']['layer1e'].ge/b2.siemens,
        firing_neurons,
        'Current'
    )
    utils.plot_state_var(
        monitors['neurons']['layer1e'],
        monitors['neurons']['layer1e'].theta/b2.mV,
        firing_neurons,
        'Theta'
    )
    utils.plot_state_var(
        monitors['neurons']['layer1e'],
        monitors['neurons']['layer1e'].v/b2.mV,
        firing_neurons,
        'Membrane potential'
    )

    utils.plot_weight_diff(
        connections['input-layer1e'],
        monitors['connections']['input-layer1e']
    )

    if not analysis_params['no_save_figs']:
        utils.save_figures(run_id)

def pickle_results(monitors, run_id):
    """
    Pickle results for future plotting.
    """
    monitors_safe = {}
    for group_type in monitors:
        monitors_safe[group_type] = {}
        for group in monitors[group_type]:
            monitor = monitors[group_type][group]
            var_dict = {}
            if isinstance(monitor, b2.SpikeMonitor):
                var_dict['t'] = np.copy(monitor.t)
                var_dict['i'] = np.copy(monitor.i)
            else:
                for var in monitor.needed_variables:
                    var_dict[var] = np.copy(getattr(monitor, var))
            monitors_safe[group_type][group] = var_dict

    with open('results/monitors_' + run_id + '.pickle', 'w') as pickle_file:
        pickle.dump(monitors_safe, pickle_file)

def pickle_visualisation(monitors, connections, run_id):
    """
    Pickle variables used for visualisation.
    (Separate from main pickle function because that one can take aaaages to
    run.)
    """
    fname = 'results/vis_vars_%s.pickle' % run_id
    with open(fname, 'wb') as pickle_file:
        objects = (monitors['neurons']['layer1vis'].v / b2.mV,
                   monitors['connections']['input-layer1e'].w,
                   np.array(connections['input-layer1e'].j),
                   monitors['spikes']['input'].t / b2.second,
                   np.array(monitors['spikes']['input'].i),
                   monitors['spikes']['layer1e'].t / b2.second,
                   np.array(monitors['spikes']['layer1e'].i))
        pickle.dump(objects, pickle_file)

def main_simulation(params):
    (neuron_params, connection_params, monitor_params, run_params,
     analysis_params) = params

    if not run_params['no_standalone']:
        b2.set_device('cpp_standalone')

    spike_filename = os.path.basename(run_params['input_spikes_filename'])
    run_id = spike_filename.replace('.pickle', '')
    if not run_params['from_paramfile']:
        ps.record_params(params, run_id)
    input_spikes = load_input(run_params)

    input_end_time = np.ceil(np.amax(input_spikes['times']))
    if 'run_time' not in run_params:
        run_params['run_time'] = input_end_time

    print("Initialising neuron groups...")
    neurons = init_neurons(
        input_spikes, run_params['layer_n_neurons'],
        neuron_params
    )
    print("done")

    print("Initialising connections...")
    connections = init_connections(
        neurons,
        connection_params
    )
    print("done")

    print("Initialising monitors...")
    monitors = init_monitors(neurons, connections, monitor_params)
    print("done")

    print("Running simulation...")
    net = run_simulation(run_params, neurons, connections, monitors, run_id)
    print("done")

    analyse_results(
        monitors,
        connections,
        run_id,
        analysis_params
    )

    if not run_params['no_save_results']:
        print("Saving results...")
        pickle_results(monitors, run_id)
        print("done!")

    if 'layer1vis' in monitors['neurons']:
        print("Saving visualisation variables...")
        pickle_visualisation(monitors, connections, run_id)
        print("done!")

    return (neurons, connections, monitors, net)

def main():
    """
    Orchestrate the rest of the program.
    """

    np.random.seed(1)

    params = ps.get_params()
    (neuron_params, connection_params, monitor_params, run_params,
     analysis_params) = params

    if run_params['test_stdp_curve']:
        neurons, connections, monitors, net = \
            tests.test_stdp_curve(connection_params)
    elif run_params['test_neurons']:
        neurons, connections, monitors, net = tests.test_neurons(
            neuron_params,
            connection_params,
            with_competition=False
        )
    elif run_params['test_competition']:
        neurons, connections, monitors, net = tests.test_neurons(
            neuron_params,
            connection_params,
            with_competition=True
        )
    else:
        neurons, connections, monitors, net = main_simulation(params)

    return (neuron_params, connection_params, monitor_params, run_params, \
        neurons, connections, monitors, net)

(n_p, c_p, m_p, r_p, ns, cs, ms, n) = main()
