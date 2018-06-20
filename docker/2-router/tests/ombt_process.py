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
Provides classes to execute self-terminating ombt2 processes,
that will be stopped automatically when the running code exits,
or will be forcibly killed in case a timeout occurs.
"""
import os, re, time, signal, json
import subprocess
import select
from tempfile import mkstemp
from process import Process
from enum import Enum


# Operational modes that can be used with ombt2
class OmbtOperationalMode(Enum):
    """
    Possible operational modes for running ombt2 process.
    """
    RPC_SERVER = 'rpc-server'
    RPC_CLIENT = 'rpc-client'
    LISTENER = 'listener'
    NOTIFIER = 'notifier'

    def __repr__(self):
        return '%s' % self.value


# Allowed controller commands
class OmbtControllerCommand(Enum):
    """
    Commands that can be issued through the ombt2 controller.
    """
    RPC_CALL = 'rpc-call'
    RPC_CAST = 'rpc-cast'
    RPC_FANOUT = 'rpc-fanout'
    NOTIFY = 'notify'
    SHUTDOWN = 'shutdown'

    def __repr__(self):
        return '%s' % self.value


class OmbtResults(object):
    """
    Represents results parsed from a successful execution of
    an ombt2 controller command (test).
    """
    class OmbtData(object):
        def __init__(self):
            self.throughput = 0.0
            self.latency = 0.0

    def __init__(self, ombt_controller_cmd):
        self.ombt_controller_cmd = ombt_controller_cmd
        self.error_found = False
        self.error_message = None
        self.client_data = OmbtResults.OmbtData()
        self.server_data = OmbtResults.OmbtData()

    def __str__(self):
        """
        Returns instance representation as a JSON string.
        :return:
        """
        return json.dumps(self.__dict__)

    @staticmethod
    def from_output(ombt_controller_cmd, stdout):
        """
        Reads the given stdout str and returns a new instance
        of the OmbtResults class. If stdout not provided,
        None is returned.
        :param ombt_controller_cmd:
        :param stdout:
        :return:
        """

        if not stdout:
            return None

        # Preparing results object
        results = OmbtResults(ombt_controller_cmd)

        ombt_data = None
        for line in [line.rstrip('\n') for line in stdout.split('\n')]:
            # Error found
            error = re.match(r'^Error: (.*)', line)
            if error:
                results.error_found = True
                results.error_message = error.group(1)
                continue

            # Found beginning of Server results
            if re.match(r'^Aggregated .*Server.* results:', line):
                ombt_data = results.server_data
            elif re.match(r'^Aggregated .*Client.* results:', line):
                ombt_data = results.client_data
            elif ombt_data is None:
                continue

            # Throughput found
            throughput = re.match(r'^Aggregate throughput: ([0-9]+\.[0-9]+) msgs/sec', line)
            if throughput:
                ombt_data.throughput = float(throughput.group(1))
                continue

            # Latency found
            latency = re.match(r'^Latency [0-9]+ samples \(msecs\): Average ([0-9]+\.[0-9]+) StdDev', line)
            if latency:
                ombt_data.latency = float(latency.group(1))

        return results


class OmbtDaemon(Process):
    """
    Runs an ombt2 process as a daemon (stdout and stderr will be redirected
    to /dev/null).
    """
    def __init__(self, url, ombt_operational_mode, **kwargs):
        args = list()
        args.append('ombt2')
        args.append('--url')
        args.append(url or 'amqp://127.0.0.1:5672')
        args.append(ombt_operational_mode)
        # --daemon not needed
        # args.append('--daemon')
        FNULL = open(os.devnull, 'w')
        kwargs.setdefault('stdout', FNULL)
        kwargs.setdefault('stderr', FNULL)
        Process.__init__(self, args, name=ombt_operational_mode, **kwargs)


class OmbtController(Process):
    """
    Runs the ombt2 controller command using the provided info in
    the constructor. It waits till process completes or times out.
    Stdout and stderr are available once completed.
    """
    def __init__(self, url, ombt_controller_cmd, events_calls='100',
                 delay='0.1', length='1024', timeout=120, **kwargs):

        self.terminated = False
        self.started = time.time()
        self.url = url
        self.length = length
        self.ombt_controller_cmd = ombt_controller_cmd
        self._result = ''

        args = list()
        args.append('ombt2')
        args.append('--url')
        args.append(url or 'amqp://127.0.0.1:5672')

        if timeout > 0:
            args.append('--timeout')
            args.append('%d' % timeout)

        args.append('controller')
        args.append(ombt_controller_cmd)

        # If not a shutdown command, add number of events/calls
        if ombt_controller_cmd != OmbtControllerCommand.SHUTDOWN.value:
            if ombt_controller_cmd == OmbtControllerCommand.NOTIFY.value:
                args.append('--events')
            else:
                args.append('--calls')
            args.append(str(events_calls))

            args.append('--pause')
            args.append(str(delay))
            args.append('--length')
            args.append(str(length))

        # define a timeout alarm
        if timeout > 0:
            signal.signal(signal.SIGALRM, self._timeout)
            signal.alarm(timeout)

        # creating a temporary file to hold stdout
        temp_fd, temp_path = mkstemp(suffix=".tmp", prefix="ombt2-out")
        TEMPF = open(temp_path, 'w')
        FNULL = open(os.devnull, 'w')
        kwargs.setdefault('stdout', TEMPF)
        kwargs.setdefault('stderr', FNULL)
        kwargs.setdefault('stdin', FNULL)
        Process.__init__(self,
                         args,
                         name='controller-%s' % ombt_controller_cmd,
                         **kwargs)

        # wait till process is done
        while self.is_running():
            time.sleep(0.5)

        # reading output
        TEMPF.close()
        self._result = open(temp_path, 'r').read()
        os.close(temp_fd)
        os.remove(temp_path)

        if timeout > 0:
            signal.alarm(0)

    def _timeout(self, signum, frame):
        """
        Callback method invoked by the alarm in case process has
        timed out.
        :param signum:
        :param frame:
        :return:
        """
        # If still running after timeout, force to terminate
        if self.is_running():
            self.terminate()
            self.terminated = True

    def get_results(self):
        """
        If process has completed successfully, it will parse the ombt2
        output and return an instance of the OmbtResults class.
        :return:
        """
        if self.returncode != 0 or self.terminated:
            # print('Completed with error - %s'
            #       % 'timed-out' if self.terminated else self.returncode)
            return None

        return OmbtResults.from_output(self.ombt_controller_cmd,
                                       self._result)

