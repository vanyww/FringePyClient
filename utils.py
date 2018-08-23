from __future__ import print_function
from itertools import izip
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

def grouped(iterable, n):
    return izip(*[iter(iterable)] * n)

class EventManager(object):
    def __init__(self):
        self._event_table = {}

    def add_event(self, event):
        self._event_table[event] = []

    def call_event(self, event, data=None):
        for cb in self._event_table[event]:
            cb(data) if data else cb()

    def subscribe(self, event, callback):
        self._event_table[event].append(callback)
    
    def unsubscribe(self, event, callback):
        del self._event_table[event][callback]