import struct
from threading import Thread
from Queue import Queue

from utils import eprint
from command_manager import command, CommandManager
from param_manager import ParamManager
from msg_codecs import RawMessageCodec, ROSMessageCodec, CommandCodec, ParamsCodec
from enums import MessageValueType, MessengerType, CommandUsage, NodeSignals, TransportProtocol, DeviceType

class _Messenger(object):
    def __init__(self, node_id, messenger_id,
                 name, device_name, device_type, messenger_type,
                 codec,
                 socket_worker, transport_protocol,
                 param_in, param_out):
        self._node_id = node_id
        self._codec = codec

        self.name = name
        self.device_name = device_name
        self.device_type = device_type
        self.messenger_type = messenger_type
        self.messenger_id = messenger_id
        self.transport_protocol = transport_protocol

        self._params_mngr = None
        self._commands_mngr = CommandManager()
        self._socket_worker = socket_worker
        self._send_func = self._socket_worker.send_message_tcp #\
                          #if transport_protocol == TransportProtocol.TCP else \
                          #self._socket_worker.send_message_udp

        self.param_in = param_in
        self.param_out = param_out

        self._is_initialized = False

        if param_in:
            self._params_mngr = ParamManager(param_in, param_out)
            self.add_command(self._change_params)
            self.add_command(self._get_parameters_info)

    def _initialize(self):
        msg = self._codec.encode_init_msg(self.messenger_id,
                                          self.transport_protocol,
                                          self.messenger_type,
                                          self.name,
                                          self.device_name,
                                          self.device_type)
  
        func = lambda: self._socket_worker.msg_tcp_sig_manager.send_signal(NodeSignals.OUT_MessangerInitialization, msg)
        self._socket_worker.msg_tcp_sig_manager.perform_and_block_until_signal(func, NodeSignals.IN_Null)
    
        for cmd in self._commands_mngr.commands.values():
            msg = CommandCodec.encode_command_init(cmd)
            self._socket_worker.cmd_sig_manager.send_signal(NodeSignals.OUT_CommandInitialization, msg)

        self._is_initialized = True

    def process_command(self, call_message):
        call_result = self._commands_mngr.call_command(call_message)
        self._socket_worker.send_command(call_result)

    def add_command(self, command):
        self._commands_mngr.register_command(command, self.messenger_id)

        if self._is_initialized:
            msg = CommandCodec.encode_command_init(command)
            self._socket_worker.cmd_sig_manager.send_signal(NodeSignals.OUT_CommandInitialization, msg)

    def set_param_on_change_callback(self, key, callback):
        if not self._params_mngr:
            raise Exception()

        self._params_mngr.add_callback(key, callback)
    
    def set_global_param_callback(self, callback):
        if not self._params_mngr:
            raise Exception()

        self._params_mngr.set_global_callback(callback)

    def get_param(self, key):
        if not self._params_mngr:
            raise Exception()

        return self._params_mngr.params[key].value

    #region commands

    @command('GetParInf', 
             description='Get parameters information', 
             repl=[MessageValueType.raw], 
             usage=CommandUsage.System)
    def _get_parameters_info(self):
        return self._params_mngr.get_parameters_info()

    @command('ChPar', 
             description='Change parameters value', 
             params=[MessageValueType.raw], 
             usage=CommandUsage.System)
    def _change_params(self, changes):
        self._params_mngr.change_params(changes)

    #endregion    

class MockMessengeer(_Messenger):
    def __init__(self, node_id, messenger_id,
                 socket_worker, 
                 param_in, param_out):
        super(MockMessengeer, self).__init__(node_id, messenger_id,
                                             '', '', DeviceType.Nothing, MessengerType.Nothing,
                                             RawMessageCodec(),
                                             socket_worker, TransportProtocol.UDP,
                                             param_in, param_out)
    
    def _(self):
        pass

class RawMessenger(_Messenger):
    def __init__(self, node_id, messenger_id,
                 name, device_name, device_type,
                 socket_worker, transport_protocol,
                 param_in, param_out):
        super(RawMessenger, self).__init__(node_id, messenger_id,
                                           name, device_name, device_type, MessengerType.Raw,
                                           RawMessageCodec(),
                                           socket_worker, transport_protocol,
                                           param_in, param_out)

    def send_reply(self, raw_message):
        msg = self._codec.encode_raw_message(raw_message)
        self._send_func(msg)

class _ROSMessageWrapper(_Messenger):
    def __init__(self, node_id, messenger_id,
                 name, device_name, device_type, messenger_type,
                 socket_worker, transport_protocol,
                 reply_type, request_type, feedback_type,
                 param_in, param_out):
        super(_ROSMessageWrapper, self).__init__(node_id, messenger_id,
                                                 name, device_name, device_type, messenger_type,
                                                 ROSMessageCodec(messenger_type, reply_type, request_type, feedback_type),
                                                 socket_worker, transport_protocol,
                                                 param_in, param_out)

class TopicNode(_ROSMessageWrapper):
    def __init__(self, node_id, messenger_id,
                 name, device_name, device_type,
                 socket_worker, transport_protocol,
                 reply_type, 
                 param_in, param_out):
        super(TopicNode, self).__init__(node_id, messenger_id,
                                        name, device_name, device_type, MessengerType.Topic,
                                        socket_worker, transport_protocol,
                                        reply_type, None, None, param_in, param_out)

    def send_reply(self, reply_message):
        if reply_message is not None:
            if not isinstance(reply_message, self._codec.reply.type):
                raise Exception()

        msg = self._codec.encode_reply_msg(self.messenger_id, reply_message)
        self._send_func(msg)

class ServiceNode(TopicNode):
    def __init__(self, node_id, messenger_id,
                 name, device_name, device_type,
                 socket_worker, transport_protocol, request_callback,
                 reply_type, request_type, 
                 param_in, param_out):
        super(TopicNode, self).__init__(node_id, messenger_id,
                                        name, device_name, device_type, MessengerType.Service,
                                        socket_worker, transport_protocol,
                                        reply_type, request_type, None, param_in, param_out)
        self._request_cb = request_callback

    def receive_request(self, request):
        decoded_request = self._codec.decode_request_msg(request)
        reply = self._request_cb(decoded_request)

        self.send_reply(reply)

class ActionNode(ServiceNode):
    pass
