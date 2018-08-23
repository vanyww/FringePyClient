from threading import Thread
from Queue import Queue

import zmq

from node_signals_manager import NodeSignalsManager

class NodeSocketWorker(object):
    MESSAGE_ASSIGNMENT_COMMAND = 0x00
    MESSAGE_ASSIGNMENT_MESSANGER = 0x01

    def __init__(self, identity, 
                 main_tcp_endpoint, #main_udp_endpoint, 
                 cmd_endpoint,
                 loop_condition):
        _zmq_HWM = 500
        _zmq_LINGER = 0
        
        self._loop_condition = loop_condition
        self._poll_loop_started = False 

        self._context = zmq.Context()
        self._identity = identity

        self.main_tcp_endpoint = main_tcp_endpoint
        self._main_tcp_socket = self._context.socket(zmq.DEALER)
        self._main_tcp_socket.setsockopt(zmq.IDENTITY, self._identity)
        self._main_tcp_socket.setsockopt(zmq.RCVHWM, _zmq_HWM)
        self._main_tcp_socket.setsockopt(zmq.SNDHWM, _zmq_HWM)
        self._main_tcp_socket.setsockopt(zmq.LINGER, _zmq_LINGER)

        #self.main_udp_endpoint = main_udp_endpoint
        #self._main_udp_socket = self._context.socket(zmq.DEALER)
        #self._main_udp_socket.setsockopt(zmq.IDENTITY, self._identity)
        #self._main_udp_socket.setsockopt(zmq.RCVHWM, _zmq_HWM)
        #self._main_udp_socket.setsockopt(zmq.SNDHWM, _zmq_HWM)
        #self._main_udp_socket.setsockopt(zmq.LINGER, _zmq_LINGER)

        self.cmd_endpoint = cmd_endpoint
        self._cmd_socket = self._context.socket(zmq.DEALER) 
        self._cmd_socket.setsockopt(zmq.IDENTITY, self._identity)
        self._cmd_socket.setsockopt(zmq.RCVHWM, _zmq_HWM)
        self._cmd_socket.setsockopt(zmq.SNDHWM, _zmq_HWM)
        self._cmd_socket.setsockopt(zmq.LINGER, _zmq_LINGER)
        
        self.msg_queue = Queue()

        self._poller = zmq.Poller()

        self._thread = None

        #self.msg_udp_sig_manager = NodeSignalsManager(self.send_message_udp)
        self.cmd_sig_manager = NodeSignalsManager(self.send_command)
        self.msg_tcp_sig_manager = NodeSignalsManager(self.send_message_tcp)

    def __del__(self):
        self.close()

    def connect(self):
        self._cmd_socket.connect(self.cmd_endpoint)
        self._main_tcp_socket.connect(self.main_tcp_endpoint)
        #self._main_udp_socket.connect(self.main_udp_endpoint)

    def start_polling(self):
        self._poller.register(self._cmd_socket, zmq.POLLIN)
        self._poller.register(self._main_tcp_socket, zmq.POLLIN)
        #self._poller.register(self._main_udp_socket, zmq.POLLIN)

        self._start_poll_loop()
    
    def close(self):
        self._thread.join()
        self._main_tcp_socket.close()
        self._cmd_socket.close()
        self._context.term()

    def send_command(self, command):
        self._cmd_socket.send_multipart(command)

    def send_message_tcp(self, message):
        self._main_tcp_socket.send_multipart(message)

    #def send_message_udp(self, message):
    #    self._main_udp_socket.send_multipart(message)

    def _start_poll_loop(self):
        if self._poll_loop_started:
            return

        self._poll_loop_started = True
    
        def _poll_loop():
            while self._loop_condition():
                sockets = self._poller.poll(timeout=64)

                for (socket, event) in sockets:
                    if(socket is self._main_tcp_socket): #or socket is self._main_udp_socket):
                        msg = socket.recv_multipart()
                        self.msg_queue.put((self.MESSAGE_ASSIGNMENT_MESSANGER, msg))
                        continue

                    if(socket is self._cmd_socket):
                        msg = socket.recv_multipart()
                        self.msg_queue.put((self.MESSAGE_ASSIGNMENT_COMMAND, msg))
                        continue

        self._thread = Thread(target=_poll_loop)
        self._thread.start()
