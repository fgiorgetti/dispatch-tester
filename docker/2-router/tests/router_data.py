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
Provides classes that can be used to represent data queried from Qpid Dispatch
Router through the $management address or qdmanage query.
"""
import json


class AllocatorInfo(object):
    """
    Used to represent JSON output from Dispatch Router's for
    elements whose type is 'org.apache.qpid.dispatch.allocator'.
    It provides a static method for parsing a JSON string, usually
    returned from the $management address or qdmanage query.
    """

    def __init__(self, **kwargs):
        self.heldByThreads = 0
        self.typeSize = 0
        self.transferBatchSize = 0
        self.globalFreeListMax = 0
        self.batchesRebalancedToGlobal = 0
        self.typeName = None
        self.batchesRebalancedToThreads = 0
        self.totalFreeToHeap = 0
        self.localFreeListMax = 0
        self.totalAllocFromHeap = 0
        self.type = None
        self.identity = None
        self.name = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    @staticmethod
    def from_qdmanage_json_out(json_content_allocator):
        """
        Parses a JSON string returned from $management address or qdmanage
        query, if the type element is 'org.apache.qpid.dispatch.allocator'.
        This method returns an array of all parsed allocators.
        :param json_content_allocator:
        :return:
        """
        return [AllocatorInfo(**d) for d in json.loads(json_content_allocator) if d['type'] == 'org.apache.qpid.dispatch.allocator']

    def __str__(self):
        """
        Returns instance representation as a JSON string.
        :return:
        """
        return json.dumps(self.__dict__)

    def threshold_exceeds_list(self):
        """
        Returns a list of tuples containing:
        - metric that exceeds its threshold
        - current value observed
        - max value allowed

        If no threshold exceeded, then return list will be empty.
        :return:
        """
        threshold = AllocatorInfo.THRESHOLDS.get(self.typeName)
        # holds a tuple list composed of (key, cur, max)
        exceeds_list = list()

        # iterates through the threshold dict
        for (key, value) in threshold.iteritems():
            #print "%s.%-25s -> CUR = %d | MAX = %d" % (self.typeName, key, self.__dict__[key], value)
            # If metric exceeds threshold, add a tuple to the list
            if self.__dict__[key] > value:
                exceeds_list.append((key, self.__dict__[key], value))

        return exceeds_list

    #
    # Thresholds dictionary.
    # Key is the typeName.
    # Any metric can be added here as needed.
    #
    THRESHOLDS = {
        'qd_bitmask_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qd_buffer_t': {
            'totalAllocFromHeap': 768,
            'heldByThreads': 512
        },
        'qd_composed_field_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qd_composite_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qd_connection_t': {
            'totalAllocFromHeap': 128,
            'heldByThreads': 128
        },
        'qd_connector_t': {
            'totalAllocFromHeap': 128,
            'heldByThreads': 128
        },
        'qd_deferred_call_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qd_hash_handle_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qd_hash_item_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qd_iterator_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qd_link_ref_t': {
            'totalAllocFromHeap': 384,
            'heldByThreads': 256
        },
        'qd_link_t': {
            'totalAllocFromHeap': 768,
            'heldByThreads': 768
        },
        'qd_listener_t': {
            'totalAllocFromHeap': 128,
            'heldByThreads': 128
        },
        'qd_log_entry_t': {
            'totalAllocFromHeap': 2048,
            'heldByThreads': 2048
        },
        'qd_message_content_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qd_message_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qd_node_t': {
            'totalAllocFromHeap': 128,
            'heldByThreads': 128
        },
        'qd_parsed_field_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qd_parsed_turbo_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qd_parse_node_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qdr_action_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 256
        },
        'qdr_address_config_t': {
            'totalAllocFromHeap': 128,
            'heldByThreads': 128
        },
        'qdr_address_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qdr_connection_info_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qdr_connection_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qdr_connection_work_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qdr_delivery_ref_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qdr_delivery_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qdr_connection_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qdr_error_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qdr_field_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qdr_general_work_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qdr_link_ref_t': {
            'totalAllocFromHeap': 1536,
            'heldByThreads': 1536
        },
        'qdr_link_t': {
            'totalAllocFromHeap': 1024,
            'heldByThreads': 1024
        },
        'qdr_link_work_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qdr_node_t': {
            'totalAllocFromHeap': 128,
            'heldByThreads': 128
        },
        'qdr_query_t': {
            'totalAllocFromHeap': 128,
            'heldByThreads': 128
        },
        'qdr_terminus_t': {
            'totalAllocFromHeap': 512,
            'heldByThreads': 512
        },
        'qd_timer_t': {
            'totalAllocFromHeap': 256,
            'heldByThreads': 256
        },
        'qdtm_router_t': {
            'totalAllocFromHeap': 128,
            'heldByThreads': 128
        }
    }

