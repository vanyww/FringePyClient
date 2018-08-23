from command_manager import command
from rnode import RNode
from enums import DeviceType, MessageValueType

from os import path
from time import sleep

class TestMessage(object):
    def __init__(self, val):
        self.A = val

    __slots__ = ['A']
    _slot_types = ['int32']

class TestUser(object):
    def __init__(self):
        self.node = RNode('TestNodeName1',
                          param_in='D:\\WS\\VS Code\\fringe\\test_params.yaml',
                          param_out='D:\\WS\\VS Code\\fringe\\test_out.yaml')

        self.top = self.node.def_topic_msgr('TestTopicName', 'TestTopicDeviceName',
                                            DeviceType.Nothing, TestMessage)

        self.srv = self.node.def_service_msgr('JustName', 'JustDevName', DeviceType.Nothing, TestMessage, TestMessage, self.rq_cb)

        self.top.add_command(self.Sum)
        self.node.add_command(self.Sum)

        self.node.start()

        self.node2 = RNode('TestNodeName2',
                    param_in='D:\\WS\\VS Code\\fringe\\test_params.yaml',
                    param_out='D:\\WS\\VS Code\\fringe\\test_out.yaml')

        self.top1 = self.node2.def_topic_msgr('TestTopicName', 'TestTopicDeviceName',
                                            DeviceType.Nothing, TestMessage)

        self.srv1 = self.node2.def_service_msgr('JustName', 'JustDevName', DeviceType.Nothing, TestMessage, TestMessage, self.rq_cb)

        self.node2.start()

    def rq_cb(self, data):
        return data

    @command('Sum',
             [MessageValueType.int32, MessageValueType.int32],
             'Sum two integers',
             [MessageValueType.int32],
             ['Result'])
    def Sum(self, a, b):
        return a + b

if __name__ == '__main__':
    user = TestUser()
    i = 0

    while True:
        user.top.send_reply(TestMessage(i))
        i += 1
        sleep(0.5)
