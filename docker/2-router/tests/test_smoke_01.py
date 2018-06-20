#!/usr/bin/env python2
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
"""
Run smoke tests to ensure compatibility between Qpid Dispatch Router
and oslo.messaging library and clients is satisfied.

It is also useful to perform basic performance validation based on values
observed during initial tests, that must be adjusted as needed through the
THRESHOLD_BASELINE dictionary.

Router related thresholds are also validated through based on limits defined
at the AllocatorInfo class.
"""
from __future__ import print_function
from ombt_process import *
from router_query_process import *
from enum import Enum
import pytest

# Static and pre-defined configuration
QDSTAT_SNAPSHOTS = True
ROUTER1_URL = 'amqp://127.0.0.1:15672'
ROUTER2_URL = 'amqp://127.0.0.1:25672'
CONTAINER1 = 'Router1-2router'
CONTAINER2 = 'Router2-2router'
INIT_DELAY = 4.0

#
# Threshold baseline is a dictionary that stores an array with the
# limits for each test command (key). The stored array holds the
# following info:
# 0 = Latency client 1024
# 1 = Latency client 65536
# 2 = Latency server 1024
# 3 = Latency server 65536
# 4 = TPS client 1024
# 5 = TPS client 65536
# 6 = TPS server 1024
# 7 = TPS server 65536
#
THRESHOLD_BASELINE = {
    OmbtControllerCommand.NOTIFY.value: [10.5, 22.0, 5.7, 15.4, 27.1, 24.8, 27.3, 25.0],
    OmbtControllerCommand.RPC_CALL.value: [15.0, 33.5, 7.2, 13.4, 35.0, 30.4, 35.0, 30.7],
    OmbtControllerCommand.RPC_CAST.value: [4.0, 4.8, 6.5, 9.9, 38.6, 38.3, 39.0, 38.7],
    OmbtControllerCommand.RPC_FANOUT.value: [3.1, 4.3, 7.7, 12.8, 38.5, 38, 77.9, 76.8]
}

#
# Tolerance allowed in the calculated thresholds for tests
# performed through ombt2. It holds a percentage that is considered
# as an upper limit for Latency and lower limit for throughputs.
#
TOLERANCE = 30.0


class Metric(Enum):
    """
    Enum that represents the metrics that are parsed from
    ombt2 command output. Its integer value is relative to the initial
    position of related data in the command array from THRESHOLD_BASELINE.
    In example, LATENCY_CLIENT = 0 means if you want to know the client latency
    thresholds for a NOTIFY command, then it will be positions 0 and 1 of the array.
    If you want Server TPS, then it will be 6 and 7.
    """
    LATENCY_CLIENT = 0
    LATENCY_SERVER = 2
    TPS_CLIENT = 4
    TPS_SERVER = 6


def calculate_threshold(ombt_controller_command, metric, length):
    """
    Performs a simple linear regression based on THRESHOLD_BASELINE values
    for the specified command and metric, estimating the value for the
    given length. It considers the TOLERANCE (percentage) as well.
    :param ombt_controller_command:
    :param metric:
    :param length:
    :return:
    """
    orig_min_max = THRESHOLD_BASELINE.get(ombt_controller_command)[metric:][:2]
    if metric in [Metric.LATENCY_CLIENT.value, Metric.LATENCY_SERVER.value]:
        min_max = [v + (v / 100.0 * TOLERANCE) for v in orig_min_max]
        return ((min_max[1] - min_max[0]) / (64 - 1)) * ((length-1024) / 1024) + min_max[0]
    else:
        min_max = [v - (v / 100.0 * TOLERANCE) for v in orig_min_max]
        return min_max[0] - ((min_max[0] - min_max[1]) / (64 - 1)) * ((length-1024) / 1024)


def pytest_generate_tests(metafunc):
    """
    Iterate through tests with length parameter and make
    sure tests will be executed with 1024 increment.
    """
    if 'length' in metafunc.fixturenames:
        metafunc.parametrize("length", [x*1024 for x in range(1, 65)])
        # metafunc.parametrize("length", [x*1024 for x in range(1, 2)])


def tear_down():
    """
    Shuts down all ombt2 processes and collect final information before
    completing the test.
    :return:
    """
    #Send a shutdown message to the controller
    OmbtController('amqp://127.0.0.1:15672', OmbtControllerCommand.SHUTDOWN.value, timeout=10)

    # Snapshot routers memory
    if QDSTAT_SNAPSHOTS:
        snapshot_router_memory(CONTAINER1, 15672, 'router1', 99999)
        snapshot_router_memory(CONTAINER2, 25672, 'router2', 99999)


def snapshot_router_memory(container, port, prefix, suffix_length):
    """
    Used to save snapshots from the router running in the provided container id,
    and tcp port. A temporary file will be saved (basically a qdstat -m output).
    These files can be used along with the utils/router_memory_plotter.sh script
    to generate a compiled data file and charts that can be used for observation.
    :param container:
    :param port:
    :param prefix:
    :param suffix_length:
    :return:
    """
    if not QDSTAT_SNAPSHOTS:
        return

    output_path = "results/%s.%d" % (prefix, suffix_length)
    subprocess.call(['docker', 'exec', '-t', container,
                     'qdstat', '-b', '0.0.0.0:%d' % port, '-m'], stdout=open(output_path, 'w'))


@pytest.fixture(scope="module", autouse=True)
def set_up(request):
    """
    Starts all daemons
    :param request:
    :return:
    """
    # Add a teardown method
    request.addfinalizer(tear_down)

    # Snapshot routers memory
    snapshot_router_memory(CONTAINER1, 15672, 'router1', 0)
    snapshot_router_memory(CONTAINER2, 25672, 'router2', 0)

    # Start the daemon processes
    OmbtDaemon(ROUTER1_URL, OmbtOperationalMode.RPC_SERVER.value)
    OmbtDaemon(ROUTER1_URL, OmbtOperationalMode.RPC_SERVER.value)

    OmbtDaemon(ROUTER2_URL, OmbtOperationalMode.RPC_CLIENT.value)
    OmbtDaemon(ROUTER2_URL, OmbtOperationalMode.RPC_CLIENT.value)
    OmbtDaemon(ROUTER2_URL, OmbtOperationalMode.RPC_CLIENT.value)
    OmbtDaemon(ROUTER2_URL, OmbtOperationalMode.RPC_CLIENT.value)

    OmbtDaemon(ROUTER2_URL, OmbtOperationalMode.LISTENER.value)
    OmbtDaemon(ROUTER2_URL, OmbtOperationalMode.LISTENER.value)

    OmbtDaemon(ROUTER1_URL, OmbtOperationalMode.NOTIFIER.value)
    OmbtDaemon(ROUTER1_URL, OmbtOperationalMode.NOTIFIER.value)
    OmbtDaemon(ROUTER1_URL, OmbtOperationalMode.NOTIFIER.value)

    # Snapshot routers memory
    snapshot_router_memory(CONTAINER1, 15672, 'router1', 1)
    snapshot_router_memory(CONTAINER2, 25672, 'router2', 1)

    # Sleep so all servers are properly running
    time.sleep(INIT_DELAY)


def execute_ombt_command(url, ombt_ctrl_cmd, length):
    ombt_proc = OmbtController(url, ombt_ctrl_cmd, length='%d' % length)
    ombt_results = ombt_proc.get_results()
    assert(ombt_proc.completed_successfully()), \
        "Not completed successfully: Timed-out=%s|Running=%s|RC=%s\nResults=%s" \
        % (ombt_proc.terminated, ombt_proc.is_running(), ombt_proc.returncode, str(ombt_results))
    assert(isinstance(ombt_results, OmbtResults))
    assert(ombt_results.error_found is False), \
        "Error found: %s" % ombt_results.error_message
    assert(ombt_results.client_data.latency <= calculate_threshold(ombt_ctrl_cmd, Metric.LATENCY_CLIENT.value, length))
    assert(ombt_results.client_data.throughput >= calculate_threshold(ombt_ctrl_cmd, Metric.TPS_CLIENT.value, length))
    assert(ombt_results.server_data.latency <= calculate_threshold(ombt_ctrl_cmd, Metric.LATENCY_SERVER.value, length))
    assert(ombt_results.server_data.throughput >= calculate_threshold(ombt_ctrl_cmd, Metric.TPS_SERVER.value, length))
    return True


def test_ombt2_modes(length):
    """
    Sends messages through a controller using the
    provided length and validate if processes complete
    successfully and thresholds are not exceeded.
    After testing all operational modes against both routers,
    validate router memory usage to detect possible leaks.
    """

    #
    # Router 1 first (not iterating to make it easier to track issues)
    #
    router_url = ROUTER1_URL

    # Notify test
    assert(execute_ombt_command(router_url, OmbtControllerCommand.NOTIFY.value, length))

    # Rpc-call test
    assert(execute_ombt_command(router_url, OmbtControllerCommand.RPC_CALL.value, length))

    # Rpc-cast test
    assert(execute_ombt_command(router_url, OmbtControllerCommand.RPC_CAST.value, length))

    # Rpc-fanout test
    assert(execute_ombt_command(router_url, OmbtControllerCommand.RPC_FANOUT.value, length))

    #
    # Router 2 second
    #
    router_url = ROUTER2_URL

    # Notify test
    assert(execute_ombt_command(router_url, OmbtControllerCommand.NOTIFY.value, length))

    # Rpc-call test
    assert(execute_ombt_command(router_url, OmbtControllerCommand.RPC_CALL.value, length))

    # Rpc-cast test
    assert(execute_ombt_command(router_url, OmbtControllerCommand.RPC_CAST.value, length))

    # Rpc-fanout test
    assert(execute_ombt_command(router_url, OmbtControllerCommand.RPC_FANOUT.value, length))

    # Snapshot router qdstat info
    snapshot_router_memory(CONTAINER1, 15672, 'router1', length)
    snapshot_router_memory(CONTAINER2, 25672, 'router2', length)

    #
    # Queries both routers before proceeding with next message length
    # and validates if any threshold has been exceeded (probably caused by
    # some possible resource leak).
    #

    # Perform threshold analysis on Router 1
    router_query = RouterContainerQuery(CONTAINER1, 15672, 'org.apache.qpid.dispatch.allocator')
    allocator_info_list = AllocatorInfo.from_qdmanage_json_out(router_query.result)
    for allocator_info in allocator_info_list:
        exceeded_list = allocator_info.threshold_exceeds_list()
        assert(len(exceeded_list) == 0), 'Router thresholds exceeded for [%s]: %s' % \
                                         (allocator_info.typeName, exceeded_list)

    # Perform threshold analysis on Router 2
    router_query = RouterContainerQuery(CONTAINER2, 25672, 'org.apache.qpid.dispatch.allocator')
    allocator_info_list = AllocatorInfo.from_qdmanage_json_out(router_query.result)
    for allocator_info in allocator_info_list:
        exceeded_list = allocator_info.threshold_exceeds_list()
        assert(len(exceeded_list) == 0), 'Router thresholds exceeded for [%s]: %s' % \
                                         (allocator_info.typeName, exceeded_list)
