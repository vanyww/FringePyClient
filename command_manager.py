from inspect import getargspec
from threading import Lock

from enums import CommandUsage, MessageValueType
from msg_codecs import CommandCodec
from utils import eprint, static_vars

_COMMAND_ID_ATTR_NAME = 'cmd_id'
_COMMAND_NAME_ATTR_NAME = 'cmd_name'
_DESCRIPTION_ATTR_NAME = 'cmd_desc'
_PARAMS_ATTR_NAME = 'cmd_params'
_REPLY_ATTR_NAME = 'cmd_repl'
_PARAM_NAMES_ATTR_NAME = 'cmd_param_names'
_REPLY_NAMES_ATTR_NAME = 'cmd_repl_names'
_COMMAND_USAGE_ATTR_NAME = 'cmd_usage'

@static_vars(cmd_id_counter = 0, lock = Lock())
def command(name, params=None, description='', repl=None, repl_names=None, usage=CommandUsage.Common):
    def dec(func):
        command.lock.acquire()
        setattr(func, _COMMAND_ID_ATTR_NAME, command.cmd_id_counter)
        command.cmd_id_counter += 1
        command.lock.release()

        setattr(func, _COMMAND_NAME_ATTR_NAME, name)
        setattr(func, _PARAMS_ATTR_NAME, params)
        setattr(func, _DESCRIPTION_ATTR_NAME, description)
        setattr(func, _REPLY_ATTR_NAME, repl)
        setattr(func, _COMMAND_USAGE_ATTR_NAME, usage)

        setattr(func, _PARAM_NAMES_ATTR_NAME, _del_self(getargspec(func).args))
        setattr(func, _REPLY_NAMES_ATTR_NAME, ['repl%i' % i for i in ([] if not repl else range(len(repl)))] if not repl_names else \
                                                repl_names if len(repl) <= len(repl_names) else \
                                                repl + ['repl%i' % i  for i in range(len(repl_names), len(repl))])
        
        if params and len(func.cmd_param_names) != len(params):
            eprint('Number of declared param types is not equal to real params number')
            raise Exception()

        return func
    return dec

def _del_self(names):
    if names[0] is 'self':
        del names[0]
    return names

class Command(object):
    def __init__(self, callback, msgr_id):
        self.callback = callback
        self.id = getattr(callback, _COMMAND_ID_ATTR_NAME)
        self.description = getattr(callback, _DESCRIPTION_ATTR_NAME)
        self.name = getattr(callback, _COMMAND_NAME_ATTR_NAME)
        self.params = getattr(callback, _PARAMS_ATTR_NAME)
        self.repl = getattr(callback, _REPLY_ATTR_NAME)
        self.param_names = getattr(callback, _PARAM_NAMES_ATTR_NAME)
        self.repl_names = getattr(callback, _REPLY_NAMES_ATTR_NAME)
        self.usage = getattr(callback, _COMMAND_USAGE_ATTR_NAME)
        self.msgr_id = msgr_id

class CommandManager(object):
    def __init__(self):
        self.commands = {}

    def register_command(self, callback, msgr_id):
        try:
            command = Command(callback, msgr_id)
        except AttributeError:
            eprint('Function %s is not a command. Registration aborted.' % callback.__name__)
            return

        self.commands[command.id] = command

    def call_command(self, call_message):
        decoded_message = CommandCodec.decode_command_call(call_message)
        command = self.commands[decoded_message['command_id']]
        args = CommandCodec.decode_command_call_args(command.params, decoded_message['args'])

        try:
            command_result = command.callback(*args)
        except:
            eprint('Error while calling command: [%i] %s' % (command.id, command.name))
            return
            
        call_result = CommandCodec.encode_command_reply(command.id, 
                                                        decoded_message['call_id'], 
                                                        command.repl, 
                                                        command_result)
        return call_result
