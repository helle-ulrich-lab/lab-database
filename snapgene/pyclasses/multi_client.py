import copy
import json
import sys
import time

import zmq


class ClientInstance:
    def __init__(self, index, port, context, poller):
        self.index = index
        self.poller = poller
        self.server_index = index
        self.socket = context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect("tcp://localhost:%s" % port)
        self.poller.register(self.socket, zmq.POLLIN)

        # define the corrent that is currently sent in the socket
        self.current_cmd = None

        # define a list specific to this client.  This is necessary when impelementing
        # the all strategy
        self.pending_list = []

        self.start_time = None

    def close(self):
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.close()
        self.poller.unregister(self.socket)

    def get_index(self):
        return self.index

    def get_socket(self):
        return self.socket

    def send_command(self, json_command):
        self.start_time = time.time()
        self.socket.send_json(json_command)
        self.current_cmd = json_command

    # finishes the command and returns the time it took to complete it
    def finish_command(self):
        duration = time.time() - self.start_time
        self.start_time = None
        self.current_cmd = None
        return duration

    def get_command(self):
        return self.current_cmd

    def get_pending_list(self):
        return self.pending_list


# class to send requests to multiple snapgene server daemons.
# the caller must supply a list of tcp ports (one for each daemon) and
# a json object with the list of requests.
class MutliClient:
    # create a new client bound to a particular tcp port.
    def __init__(self, tcp_ports, zmq_context, verbosity):
        self.verbosity = verbosity
        self.max_ports = sys.maxsize

        self.zmq_context = zmq_context
        self.poller = zmq.Poller()

        # create the clients, we also need a socket to client map later
        self.clients = []
        self.socket_to_clients = {}
        for server_index in tcp_ports:
            client = ClientInstance(
                server_index, tcp_ports[server_index], self.zmq_context, self.poller
            )
            self.clients.append(client)
            self.socket_to_clients[client.get_socket()] = client

    # does a request, waits for a response and returns it.
    # if the response times out then an Exception is thrown.
    # all is a parameter where all the commands must be sent to each server
    # the timeout is in milliseconds
    #
    # returns each command in a list
    def doBatch(self, commandList, all, timeout):
        responseList = []

        # keep a count of the total number of commands to send out.
        unfinishedCommandCount = 0

        # fill command lists
        unsentCommands = []
        if all:
            # For all, we need to copy each comman to the each client.
            for client in self.clients:
                client_pending_list = client.get_pending_list()
                for c in reversed(commandList):
                    client_pending_list.append(copy.deepcopy(c))
                    unfinishedCommandCount += 1
        else:
            # make a copy of the command list and pop off it as we process elements
            # we will be removing from the end of the list, so reverse it.  That we process in the
            # order specified if that makes a difference
            unsentCommands = list(commandList)
            unsentCommands.reverse()
            unfinishedCommandCount += len(unsentCommands)

        # loop until everything was sent or
        while unfinishedCommandCount != 0:
            # send commands for clients that are available
            for client in self.clients:
                if client.get_command() is None:
                    # first try a client specific command
                    cmd = None
                    if client.get_pending_list():
                        cmd = client.get_pending_list().pop()
                    elif unsentCommands:
                        cmd = unsentCommands.pop()

                    # send to available client
                    if cmd:
                        client.send_command(cmd)
                        if self.verbosity >= 2:
                            print(cmd)

            # now wait for response from the poller or timeout
            pollerSockets = dict(self.poller.poll(timeout))
            for s in pollerSockets:
                # get response and add the socket back to the available list
                client = self.socket_to_clients[s]
                responseTime = client.finish_command()
                unfinishedCommandCount -= 1

                response = s.recv_json()
                response["responseTime"] = "{:0.2f}".format(responseTime * 1000)
                responseList.append(response)
                if self.verbosity >= 1:
                    print(
                        json.dumps(
                            response, sort_keys=True, indent=4, separators=(",", ":")
                        )
                    )

            # check for timeouts --- this indicates no progress was made.
            if len(pollerSockets) == 0:
                # timeout condition.  For any pending requests, return them now, but mark them
                # with an extra flag that the request timed out.
                for client in self.clients:
                    cmd = client.get_command()
                    if cmd is not None:
                        errorCmd = copy.deepcopy(cmd)
                        errorCmd["serverIndex"] = client.get_index()
                        errorCmd["response"] = "error"
                        errorCmd["reason"] = "timeout"
                        if self.verbosity >= 1:
                            print(
                                json.dumps(
                                    errorCmd,
                                    sort_keys=True,
                                    indent=4,
                                    separators=(",", ":"),
                                )
                            )
                        responseList.append(errorCmd)

                return responseList

        return responseList

    def close(self):
        for client in self.clients:
            client.close()
