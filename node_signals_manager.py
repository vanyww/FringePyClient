from threading import Event

from msg_codecs import NodeSignalsCodec
from enums import NodeSignals
from utils import EventManager

class NodeSignalsManager(object):
    def __init__(self, send_callback):
        self._send_cb = send_callback
        self._event_manager = EventManager()

        for signal in NodeSignals.get_IN_signals():
            self._event_manager.add_event(signal)

    def subscribe_on_signal(self, signal, callback):
        self._event_manager.subscribe(signal, callback)

    def unsubscribe_from_signal(self, signal, callback):
        self._event_manager.unsubscribe(signal, callback)

    def perform_and_block_until_signal(self, func, signal):
        event = Event()
        
        def _free_on_signal():
            event.set()
            self.unsubscribe_from_signal(signal, _free_on_signal)

        self.subscribe_on_signal(signal, lambda: event.set())
        func()
        event.wait()

    def block_until_signal(self, signal):
        event = Event()
        
        def _free_on_signal():
            event.set()
            self.unsubscribe_from_signal(signal, _free_on_signal)

        self.subscribe_on_signal(signal, lambda: event.set())
        event.wait()

    def process_signal(self, message):
        (signal, data) = NodeSignalsCodec.decode_node_signal(message)
        self._event_manager.call_event(signal, data)

    def send_signal(self, signal, data=None):
        self._send_cb(NodeSignalsCodec.encode_node_signal(signal, data))