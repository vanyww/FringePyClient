from yaml import load, dump
from utils import eprint
from msg_codecs import ParamsCodec

import os

class ParamManager(object):
    def __init__(self, params_file, out_params_file=None):
        self._params_path = params_file
        self._out_params_path = out_params_file
        self._callbacks = {}
        self._global_callback = None
        
        self.params = None
        self._set_file(params_file)

    def _set_file(self, file_path):
        with open(file_path, 'r') as stream:
            self.params = ParamsCodec.decode_params_info_yaml(load(stream))

    def set_global_callback(self, callback):
        self._global_callback = callback

    def add_callback(self, key, callback):
        if callback:
            # use in instead of has_key
            if not self.params.has_key(key):
                eprint('There are no param with this name: %s' % key)
                return

            self._callbacks[key] = callback

    def save_params(self):
        with open(self._params_path, 'w') as stream:
            dump(ParamsCodec.encode_params_info_yaml(self.params), stream, default_flow_style=False)

    def save_params_ros(self):
        if self._out_params_path:
            with open(self._out_params_path, 'w') as stream:
                dump(ParamsCodec.encode_params_yaml(self.params), stream, default_flow_style=False)       

    def get_parameters_info(self):
        return ParamsCodec.encode_params_info(self.params.values())

    def change_params(self, changes):
        decoded_msg = ParamsCodec.decode_params(self.params, changes)

        for param, value in decoded_msg:
            param.value = value
            if self._callbacks.has_key(param.name):
                self._callbacks[param.name](value)
        self.save_params()
        self.save_params_ros()
