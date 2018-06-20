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
Provides a concrete implementation of self terminating
router processes that can be used in this test.
"""
import os, re, time, signal
import subprocess
from process import Process
from router_data import AllocatorInfo
from enum import Enum


class RouterContainerQuery(Process):
    """
    Used to run qdmanage query process on a running container
    in this particular test scenario.
    """
    def __init__(self, container_id, tcp_port, query_type=None, **kwargs):

        self._result = ''
        args = list()
        args.append('docker')
        args.append('exec')
        args.append('-t')
        args.append(container_id)
        args.append('qdmanage')
        args.append('query')
        args.append('-b')
        args.append('0.0.0.0:%d' % tcp_port)
        args.append('--type')
        if query_type:
            args.append(query_type)

        kwargs.setdefault('stdout', subprocess.PIPE)
        kwargs.setdefault('stderr', subprocess.PIPE)
        Process.__init__(self,
                         args,
                         name='%s-%s-%s' % (type(self).__name__, container_id, query_type),
                         **kwargs)

        # Save stdout into _result
        self._result = self.communicate()[0]

    @property
    def result(self):
        return self._result
