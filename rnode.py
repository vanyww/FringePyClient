from struct import pack
from threading import Thread

import messaging
from msg_codecs import NodeSignalsCodec, NodeMessageCodec
from enums import NodeSignals, MessageType, TransportProtocol
from node_socket_worker import NodeSocketWorker

class RNode(object):
    _MESSAGE_TYPE_INDEX = 0
    _MESSENGER_ID_INDEX = 2
    #params (kwargs):
    #   param_in
    #   param_out
    #   loop_condition
    #   main_endpoint
    #   cmd_endpoint
    def __init__(self, name, **kwargs):
        self._name = name
        self._param_in = kwargs.get('param_in')
        self._param_out = kwargs.get('param_out')
        
        self._loop_condition = kwargs.get('loop_condition', lambda: True)
        self._msg_process_loop_started = False
        self._node_id = pack('i', hash(name))

        self._socket_worker = NodeSocketWorker(self._node_id, 
                                               kwargs.get('main_tcp_endpoint', 'tcp://localhost:5557'),
                                               #kwargs.get('main_udp_endpoint', 'udp://localhost:5557'),
                                               kwargs.get('cmd_endpoint', 'tcp://localhost:5558'),
                                               self._loop_condition)

        self._messenger_id_cnt = 0
        self._node_messenger = messaging.MockMessengeer(self._node_id, pack('B', self._messenger_id_cnt),
                                                        self._socket_worker, 
                                                        self._param_in, self._param_out)
        self._messenger_id_cnt += 1

        self._msgrs_dict = {self._node_messenger.messenger_id: self._node_messenger}
        
        self._socket_worker.msg_tcp_sig_manager.subscribe_on_signal(NodeSignals.IN_Ping, 
                                                                    lambda: self._socket_worker.msg_tcp_sig_manager.send_signal(NodeSignals.OUT_Pong))
        #self._socket_worker.msg_udp_sig_manager.subscribe_on_signal(NodeSignals.IN_Ping, 
        #                                                            lambda: self._socket_worker.msg_udp_sig_manager.send_signal(NodeSignals.OUT_Pong))
        self._socket_worker.cmd_sig_manager.subscribe_on_signal(NodeSignals.IN_Ping, 
                                                                lambda: self._socket_worker.cmd_sig_manager.send_signal(NodeSignals.OUT_Pong))
 
    def start(self):
        self._socket_worker.connect() 

        self._socket_worker.start_polling()
        self._start_message_process_loop()

        func = lambda: self._socket_worker.send_message_tcp(NodeMessageCodec.encode_node_initialization(self._name))
        self._socket_worker.msg_tcp_sig_manager.perform_and_block_until_signal(func, NodeSignals.IN_Null)

        for msgr in self._msgrs_dict.values():
            msgr._initialize()

    def _start_message_process_loop(self):
        if self._msg_process_loop_started:
            return

        self._msg_process_loop_started = True

        def _message_process_loop():
            while self._loop_condition():
                (assignment, msg) = self._socket_worker.msg_queue.get(timeout=)
                msg_type = MessageType(msg[self._MESSAGE_TYPE_INDEX])

                if msg_type == MessageType.Common:
                    msgr = self._msgrs_dict[msg[self._MESSENGER_ID_INDEX]]
                    msgr.receive_request(msg)
                    continue

                if msg_type == MessageType.NodeSignal:
                    if assignment == self._socket_worker.MESSAGE_ASSIGNMENT_MESSANGER:
                        self._socket_worker.msg_tcp_sig_manager.process_signal(msg)
                        continue

                    if assignment == self._socket_worker.MESSAGE_ASSIGNMENT_COMMAND:
                        self._socket_worker.cmd_sig_manager.process_signal(msg)
                        continue

                if msg_type == MessageType.Command:
                    msgr = self._msgrs_dict[msg[self._MESSENGER_ID_INDEX]]
                    msgr.process_command(msg)
                    continue

        thread = Thread(target=_message_process_loop)
        thread.start()

    def add_command(self, command):
        self._node_messenger.add_command(command)

    def set_param_on_change_callback(self, key, callback):
        if not self._node_messenger._params_mngr:
            raise Exception()

        self._node_messenger._params_mngr.add_callback(key, callback)
    
    def set_global_param_callback(self, callback):
        if not self._node_messenger._params_mngr:
            raise Exception()

        self._node_messenger._params_mngr.set_global_callback(callback)

    def get_param(self, key):
        if not self._node_messenger._params_mngr:
            raise Exception()

        return self._node_messenger._params_mngr.params[key].value

    def get_defined_messenger(self, name):
        for msgr in self._msgrs_dict.values():
            if msgr.name == name:
                return msgr

    def def_raw_msgr(self, name, device_name, device_type,
                     param_in=None, param_out=None,
                     transport_protocol=TransportProtocol.TCP):
        msgr_id = pack('B', self._messenger_id_cnt)
        raw_messenger = messaging.RawMessenger(self._node_id, msgr_id, 
                                               name, device_name, device_type,
                                               self._socket_worker, transport_protocol,
                                               param_in, param_out)
        self._msgrs_dict[msgr_id] = raw_messenger        
        self._messenger_id_cnt += 1

        if(self._msg_process_loop_started):
            raw_messenger._initialize()

        return raw_messenger

    def def_topic_msgr(self, name, device_name, device_type,
                       reply_type,
                       param_in=None, param_out=None,
                       transport_protocol=TransportProtocol.TCP):
        msgr_id = pack('B', self._messenger_id_cnt)
        topic_messenger = messaging.TopicNode(self._node_id, msgr_id, 
                                              name, device_name, device_type,
                                              self._socket_worker, transport_protocol,
                                              reply_type,
                                              param_in, param_out)
        self._msgrs_dict[msgr_id] = topic_messenger        
        self._messenger_id_cnt += 1

        if(self._msg_process_loop_started):
            topic_messenger._initialize()

        return topic_messenger

    def def_service_msgr(self, name, device_name, device_type,
                         reply_type, request_type, request_callback,
                         param_in=None, param_out=None,
                         transport_protocol=TransportProtocol.TCP):
        msgr_id = pack('B', self._messenger_id_cnt)
        servive_messenger = messaging.ServiceNode(self._node_id, msgr_id, 
                                                  name, device_name, device_type,
                                                  self._socket_worker, transport_protocol, request_callback,
                                                  reply_type, request_type,
                                                  param_in, param_out)
        self._msgrs_dict[msgr_id] = servive_messenger        
        self._messenger_id_cnt += 1

        if(self._msg_process_loop_started):
            servive_messenger._initialize()

        return servive_messenger

    def def_action_msgr(self):
        pass

    @property
    def node_name(self):
        return self._name

    @property
    def param_in_file(self):
        return self._param_in

    @property
    def param_out_file(self):
        return self._param_out

    @property
    def main_tcp_endpoint(self):
        return self._socket_worker.main_tcp_endpoint

    #@property
    #def main_udp_endpoint(self):
    #    return self._socket_worker.main_udp_endpoint

    @property
    def cmd_endpoint(self):
        return self._socket_worker.cmd_endpoint