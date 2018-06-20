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
This module brings an abstraction of a process execution in a way
that all concrete processes will be tracked and forcibly terminated
in case the running program completes and process is still running.
It waits for a pre-defined amount of time * attempts, before killing
the running process.
"""
import time
import subprocess
import atexit


class Process(subprocess.Popen):
    """
    Abstract Popen wrapper that ensures all opened processes will be
    closed when code finishes.
    """

    MAX_ATTEMPTS = 3
    ATTEMPT_DELAY = 1

    def __init__(self, args, name=None, **kwargs):
        self.name = name
        atexit.register(self.teardown)
        kwargs.setdefault('bufsize', 1)
        kwargs.setdefault('universal_newlines', True)
        super(Process, self).__init__(args, **kwargs)

    def is_running(self):
        return self.poll() is None

    def completed_successfully(self):
        return not self.is_running() and self.returncode == 0

    def teardown(self):
        # Delay till max attempts reached
        attempt = 0
        while self.is_running() and attempt < self.MAX_ATTEMPTS:
            # print("Process still running (%s) - retrying in %d seconds"
            #       % (self.name, Process.ATTEMPT_DELAY))
            attempt += 1
            time.sleep(Process.ATTEMPT_DELAY)

        # If not terminated after all attempts, kill process
        if self.returncode is None:
            # print("Killing process (%s [%d])"
            #       % (self.name, self.pid))
            self.kill()
