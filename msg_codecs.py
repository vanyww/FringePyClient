import struct
from itertools import izip

from enums import (CommandMessageSubtype, MessageSubtype, MessageType,
                   MessageValueType, MessengerType, ParamFlags, NodeSignals)
from utils import grouped


class MessageDescription(object):
    def __init__(self, message):
        self.type = message
        self.arg_types = [MessageValueType[slot].value for slot in message._slot_types]
        self.arg_names = message.__slots__

class Parameter(object):
    def __init__(self, name, param_id, 
                 description=None, param_type=MessageValueType.nothing, value=None, flags=ParamFlags.normal.value):
        self.id = param_id
        self.name = name
        self.description = description
        self.flags = flags
        self.value = value
        self.type = param_type

_TO_BYTES = {
    MessageValueType.nothing.value: lambda x: None,
    MessageValueType.bool.value: lambda x: struct.pack(b'?', x),
    MessageValueType.int8.value: lambda x: struct.pack(b'b', x),
    MessageValueType.uint8.value: lambda x: struct.pack(b'B', x),
    MessageValueType.int16.value: lambda x: struct.pack(b'h', x),
    MessageValueType.uint16.value: lambda x: struct.pack(b'H', x),
    MessageValueType.int32.value: lambda x: struct.pack(b'i', x),
    MessageValueType.uint32.value: lambda x: struct.pack(b'I', x),
    MessageValueType.int64.value: lambda x: struct.pack(b'l', x),
    MessageValueType.uint64.value: lambda x: struct.pack(b'L', x),
    MessageValueType.float32.value: lambda x: struct.pack(b'f', x),
    MessageValueType.float64.value: lambda x: struct.pack(b'd', x),
    MessageValueType.string.value: lambda x: x,
    MessageValueType.raw.value: lambda x: x
}

_FROM_BYTES = {
    MessageValueType.nothing.value: lambda x: None,
    MessageValueType.bool.value: lambda x: struct.unpack(b'?', x)[0],
    MessageValueType.int8.value: lambda x: struct.unpack(b'b', x)[0],
    MessageValueType.uint8.value: lambda x: struct.unpack(b'B', x)[0],
    MessageValueType.int16.value: lambda x: struct.unpack(b'h', x)[0],
    MessageValueType.uint16.value: lambda x: struct.unpack(b'H', x)[0],
    MessageValueType.int32.value: lambda x: struct.unpack(b'i', x)[0],
    MessageValueType.uint32.value: lambda x: struct.unpack(b'I', x)[0],
    MessageValueType.int64.value: lambda x: struct.unpack(b'l', x)[0],
    MessageValueType.uint64.value: lambda x: struct.unpack(b'L', x)[0],
    MessageValueType.float32.value: lambda x: struct.unpack(b'f', x)[0],
    MessageValueType.float64.value: lambda x: struct.unpack(b'd', x)[0],
    MessageValueType.string.value: lambda x: x,
    MessageValueType.raw.value: lambda x: x
}

class _BaseMessageCodec(object):
    def encode_init_msg(self, msgr_id, transport_protocol, 
                        msgr_type, name, dev_name, dev_type):
        return [msgr_type.value +           
                    dev_type.value +
                    transport_protocol.value,
                name,
                dev_name,
                msgr_id]

class RawMessageCodec(_BaseMessageCodec):
    def encode_raw_message(self, message):
        encoded_message = [MessageType.Common.value,
                           MessageSubtype.Reply.value]
        if isinstance(message, list):
            encoded_message.extend(message)
        else:
            encoded_message.append(message)
        return encoded_message

class ROSMessageCodec(_BaseMessageCodec):
    def __init__(self, msgr_type, reply_type, request_type=None, feedback_type=None):
        self.reply = MessageDescription(reply_type)
        self.request = None
        self.feedback = None

        if msgr_type == MessengerType.Service:
            self.request = MessageDescription(request_type)

        if msgr_type == MessengerType.Action:
            self.feedback = MessageDescription(feedback_type)

        super(ROSMessageCodec, self).__init__()

    def encode_init_msg(self, msgr_id, transport_protocol, msgr_type, name, dev_name, dev_type):
        encoded_message = super(ROSMessageCodec, self).\
            encode_init_msg(msgr_id, transport_protocol, msgr_type, name, dev_name, dev_type)

        encoded_message.extend(self._encode_msg_desc(self.reply))

        if self.request:
            encoded_message.append(b'')
            encoded_message.extend(self._encode_msg_desc(self.request))

        if self.feedback:
            encoded_message.append(b'')
            encoded_message.extend(self._encode_msg_desc(self.feedback))

        return encoded_message

    def encode_reply_msg(self, messenger_id, msg):
        encoded_message = [MessageType.Common.value,
                           MessageSubtype.Reply.value,
                           messenger_id]
        encoded_message.extend(self._encode_msg_data(self.reply, msg))
        return encoded_message

    def encode_feedback_msg(self, msg):
        assert self.feedback is not None, 'No Feedback'

        encoded_message = [MessageType.Common.value,
                           MessageSubtype.Feedback.value]
        encoded_message.extend(self._encode_msg_data(self.feedback, msg))
        return encoded_message

    def decode_request_msg(self, msg):
        assert self.request is not None, 'No Request'

        decoded_params = []
        #why 1?
        for (param_type, arg) in izip(self.request.arg_types, msg[3:]):
            decoded_params.append(_FROM_BYTES[param_type](arg))
        return self.request.type(*decoded_params)

    @staticmethod
    def _encode_msg_desc(msg_desc):
        encoded_msg_desc = []
        for var_name, var_type in izip(msg_desc.arg_names, msg_desc.arg_types):
            encoded_msg_desc.append(var_name)
            encoded_msg_desc.append(var_type)
        return encoded_msg_desc

    @staticmethod
    def _encode_msg_data(msg_desc, message):
        decoded_args = []
        for var_name, var_type in izip(msg_desc.arg_names, msg_desc.arg_types):
            decoded_args.append(_TO_BYTES[var_type](getattr(message, var_name)))
        return decoded_args

class CommandCodec(object):
    @staticmethod
    def encode_command_init(command):
        encoded_message = [command.msgr_id,
                           struct.pack('i', command.id),
                           command.name,
                           command.description,
                           command.usage.value]

        if command.params is None:
            encoded_message.append('')
        else:
            for name, v_type in izip(command.param_names, command.params):
                encoded_message.append(name)
                encoded_message.append(v_type.value)

        encoded_message.append('')

        if command.repl is None:
            encoded_message.append('')
        else:
            for name, v_type in izip(command.repl_names, command.repl):
                encoded_message.append(name)
                encoded_message.append(v_type.value)

        return encoded_message

    @staticmethod
    def decode_command_call(call_message):
        #0 and 1 indexes are Command(contains CommandInit) and Request values
        decoded_message = { 'command_id': struct.unpack(b'i', call_message[3])[0],
                            'call_id': call_message[4],
                            'args': call_message[5:] }
        return decoded_message

    @staticmethod
    def decode_command_call_args(arg_types, args):
        if not arg_types:
            return []

        if arg_types[0] == MessageValueType.raw:
            return [args]

        return [_FROM_BYTES[arg_type.value](arg) for arg_type, arg in izip(arg_types, args)]

    @staticmethod
    def encode_command_reply(command_id, call_id, reply_desc, reply):
        encoded_message = [MessageType.Command.value,
                           struct.pack('i', command_id),
                           CommandMessageSubtype.Reply.value,
                           call_id]
        if not reply:
            return encoded_message

        if reply_desc[0] == MessageValueType.raw:
            encoded_message.extend(reply)
            return encoded_message

        if isinstance(reply, list):
            for reply_type, param in izip(reply_desc, reply):
                encoded_message.append(_TO_BYTES[reply_type.value](param))
            return encoded_message

        encoded_message.append(_TO_BYTES[reply_desc[0].value](reply))
        return encoded_message

class ParamsCodec(object):
    @staticmethod
    def decode_params_info_yaml(params):
        decoded_info = {}

        for (index, (name, value)) in enumerate(params.iteritems()):
            decoded_info[index] = (Parameter(name, 
                                             index,
                                             value['description'] if 'description' in value else None,
                                             MessageValueType[value['type']] if 'type' in value else MessageValueType.nothing,
                                             value['value'] if 'value' in value else None, 
                                             value['flags'] if 'flags' in value else ParamFlags.normal.value))
        return decoded_info

    @staticmethod
    def decode_params(params, changes):
        decoded_result = []
        
        for index, value in grouped(changes, 2):
            command_id = struct.unpack('i', index)[0]
            parameter = params[command_id]

            decoded_result.append((parameter, _FROM_BYTES[parameter.type.value](value)))

        return decoded_result

    @staticmethod
    def encode_params_info(params):
        result = []

        for param in params:
            param_type = param.type.value
            result.extend([struct.pack('i', param.id), 
                           param.name, 
                           param.description,
                           struct.pack('B', param.flags), 
                           param_type])

            value = _TO_BYTES[param_type](param.value)
        
            if type(value) is list:
                result.extend(value)
            else:
                result.append(value)

        return result

    @staticmethod
    def encode_params_yaml(params):
        return {param.name: param.value for param in params.itervalues()}

    @staticmethod
    def encode_params_info_yaml(params):
        return {param.name: {'flags': param.flags,
                             'type': param.type.name,
                             'description': param.description,
                             'value': param.value} for param in params.itervalues()} 

class NodeSignalsCodec(object):
    @staticmethod
    def encode_node_signal(signal, data):
        result = [MessageType.NodeSignal.value, signal.value]
        if data:
            result.extend(data)
        return result

    @staticmethod
    def decode_node_signal(msg):
        msg_length = len(msg)

        signal = NodeSignals(msg[1])
        data = None if msg_length <= 2 else msg[2 : msg_length]

        return (signal, data)

class NodeMessageCodec(object):
    @staticmethod
    def encode_node_initialization(name):
        return [MessageType.NodeInitialization.value, name]
