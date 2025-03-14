import zmq


class Client:
    # create a new client bound to a particular tcp port.
    def __init__(self, tcp_port, zmq_context):
        self.tcp_port = tcp_port
        self.zmq_context = zmq_context
        self.last_request_time = 0
        self.socket = zmq_context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect("tcp://localhost:%s" % self.tcp_port)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    # returns the time of the last request
    def lastRequestTime(self):
        return self.last_request_time

    # does a request, waits for a response and returns it.
    # if the response times out then an Exception is thrown.
    def requestResponse(self, request, timeout):
        self.socket.send_json(request)

        sockets = dict(self.poller.poll(timeout))
        if self.socket in sockets:
            response = self.socket.recv_json()
            return response
        else:
            raise Exception("Request timeout")

    def close(self):
        self.poller.unregister(self.socket)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.close()
