/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>


#include "proton/reactor.h"
#include "proton/message.h"
#include "proton/connection.h"
#include "proton/session.h"
#include "proton/link.h"
#include "proton/delivery.h"
#include "proton/event.h"
#include "proton/handlers.h"

static int quiet = 0;

#define MAX_SIZE 512

// Example application data.  This data will be instantiated in the event
// handler, and is available during event processing.  In this example it
// holds configuration and state information.
//
typedef struct {
    int count;          // # of messages to receive before exiting
    int credit;         // max credit window
    char *source;       // name of the source node to receive from
    pn_message_t *message;      // holds the received message
} app_data_t;

// helper to pull pointer to app_data_t instance out of the pn_handler_t
//
#define GET_APP_DATA(handler) ((app_data_t *)pn_handler_mem(handler))

// Called when reactor exits to clean up app_data
//
static void delete_handler(pn_handler_t *handler)
{
    app_data_t *d = GET_APP_DATA(handler);
    if (d->message) {
        pn_decref(d->message);
        d->message = NULL;
    }
}


/* Process each event posted by the reactor.
 */
static void event_handler(pn_handler_t *handler,
                          pn_event_t *event,
                          pn_event_type_t type)
{
    app_data_t *data = GET_APP_DATA(handler);

    switch (type) {

    case PN_CONNECTION_INIT: {
        // Create and open all the endpoints needed to send a message
        //
        pn_connection_t *conn = pn_event_connection(event);
        pn_connection_open(conn);
        pn_session_t *ssn = pn_session(conn);
        pn_session_open(ssn);
        pn_link_t *receiver = pn_receiver(ssn, "MyReceiver");
        pn_terminus_set_address(pn_link_source(receiver), data->source);
        pn_link_open(receiver);
        // cannot receive without granting credit:
        pn_link_flow(receiver, data->credit);
    } break;

    case PN_DELIVERY: {
        // A message has been received
        //
        pn_delivery_t *dlv = pn_event_delivery(event);
        if (pn_delivery_readable(dlv) && !pn_delivery_partial(dlv)) {
            // A full message has arrived
            if (!quiet && pn_delivery_pending(dlv) < MAX_SIZE) {
                // try to decode the message body
                pn_bytes_t bytes;
                bool found = false;
                static char buffer[MAX_SIZE];
                size_t len = pn_link_recv(pn_delivery_link(dlv), buffer, MAX_SIZE);
                pn_message_clear(data->message);
                // decode the raw data into the message instance
                if (pn_message_decode(data->message, buffer, len) == PN_OK) {
                    // Assuming the message came from the sender example, try
                    // to parse out a single string from the payload
                    //
                    int rc = pn_data_scan(pn_message_body(data->message)
                                          , "?S", &found, &bytes);
                    if (!rc && found) {
                        fprintf(stdout, "Message: [%.*s]\n",
                                (int)bytes.size, bytes.start);
                    } else {
                        fprintf(stdout, "Message received!\n");
                    }
                } else {
                    fprintf(stdout, "Message received!\n");
                }
            }

            pn_link_t *link = pn_delivery_link(dlv);

            if (!pn_delivery_settled(dlv)) {
                // remote has not settled, so it is tracking the delivery.  Ack
                // it.
                pn_delivery_update(dlv, PN_ACCEPTED);
            }

            // done with the delivery, move to the next and free it
            pn_link_advance(link);
            pn_delivery_settle(dlv);  // dlv is now freed

            if (pn_link_credit(link) < data->credit/2) {
                // Grant enough credit to bring it up to CAPACITY:
                pn_link_flow(link, data->credit - pn_link_credit(link));
            }

            if (data->count && --data->count == 0) {
                // done receiving, close the endpoints
                pn_link_close(link);
                pn_session_t *ssn = pn_link_session(link);
                pn_session_close(ssn);
                pn_connection_close(pn_session_connection(ssn));
            }
        }
    } break;

    default:
        break;
    }
}

static void usage(void)
{
  printf("Usage: receiver <options>\n");
  printf("-a      \tThe host address [localhost:5672]\n");
  printf("-c      \t# of messages to receive, 0=receive forever [1]\n");
  printf("-s      \tSource address [examples]\n");
  printf("-i      \tContainer name [ReceiveExample]\n");
  printf("-q      \tQuiet - turn off stdout\n");
  printf("-f      \tCredit window [100]\n");
  exit(1);
}

int main(int argc, char** argv)
{
    char *address = "localhost";
    char *container = "ReceiveExample";

    /* create a handler for the connection's events.
     * event_handler will be called for each event.  The handler will allocate
     * a app_data_t instance which can be accessed when the event_handler is
     * called.
     */
    pn_handler_t *handler = pn_handler_new(event_handler,
                                           sizeof(app_data_t),
                                           delete_handler);

    /* set up the application data with defaults */
    app_data_t *app_data = GET_APP_DATA(handler);
    memset(app_data, 0, sizeof(app_data_t));
    app_data->count = 1;
    app_data->source = "examples";
    app_data->message = pn_message();
    app_data->credit = 100;

    /* Attach the pn_handshaker() handler.  This handler deals with endpoint
     * events from the peer so we don't have to.
     */
    pn_handler_add(handler, pn_handshaker());

    /* command line options */
    opterr = 0;
    int c;
    while((c = getopt(argc, argv, "i:a:c:s:qhf:")) != -1) {
        switch(c) {
        case 'h': usage(); break;
        case 'a': address = optarg; break;
        case 'c':
            app_data->count = atoi(optarg);
            if (app_data->count < 0) usage();
            break;
        case 's': app_data->source = optarg; break;
        case 'i': container = optarg; break;
        case 'q': quiet = 1; break;
        case 'f':
            app_data->credit = atoi(optarg);
            if (app_data->credit <= 0) usage();
            break;
        default:
            usage();
            break;
        }
    }

    pn_reactor_t *reactor = pn_reactor();
    pn_connection_t *conn = pn_reactor_connection(reactor, handler);

    // the container name should be unique for each client
    pn_connection_set_container(conn, container);
    pn_connection_set_hostname(conn, address);  // FIXME

    // wait up to 5 seconds for activity before returning from
    // pn_reactor_process()
    pn_reactor_set_timeout(reactor, 5000);

    pn_reactor_start(reactor);

    while (pn_reactor_process(reactor)) {
        /* Returns 'true' until the connection is shut down.
         * pn_reactor_process() will return true at least once every 5 seconds
         * (due to the timeout).  If no timeout was configured,
         * pn_reactor_process() returns as soon as it finishes processing all
         * pending I/O and events. Once the connection has closed,
         * pn_reactor_process() will return false.
         */
    }

    return 0;
}
