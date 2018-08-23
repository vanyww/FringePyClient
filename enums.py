from enum import Enum

class TransportProtocol(Enum):
    TCP = b"\x00"
    UDP = b"\x01"

class MessageType(Enum):
    Common = b"\x00"
    NodeSignal = b"\x01"
    Command = b"\x02"
    NodeInitialization = b"\x03"

class NodeSignals(Enum):
    IN_Null = "\x00"
    IN_Ping = "\x01"

    OUT_MessangerInitialization = "\x80"
    OUT_CommandInitialization = "\x81"
    OUT_Pong = "\x82"
    OUT_Null = "\x83"

    @classmethod
    def get_IN_signals(cls):
        attr_names = (name for name in dir(cls) if name.startswith('IN'))
        return tuple((getattr(cls, name) for name in attr_names))

class CommandMessageSubtype(Enum):
    Request = b'\x00'
    Reply = b'\x01'

class MessageSubtype(Enum):
    Reply = b"\x00"
    Goal = b"\01"
    Feedback = b"\02"

class MessengerType(Enum):
    Nothing = b"\xFF"
    Raw = b"\x00"
    Topic = b"\x01"
    Service = b"\x02"
    Action = b"\x03",

class DeviceType(Enum):
    Nothing = b"\x00"
    Thruster = b"\x01"
    BCS = b"\x02"
    LED = b"\x03"
    MJPEGCamera = b"\x04"
    IMU = b"\x05"

class MessageValueType(Enum):
    nothing = b"\x00"
    bool = b"\x01"
    int8 = b"\x02"
    uint8 = b"\x03"
    int16 = b"\x04"
    uint16 = b"\x05"
    int32 = b"\x06"
    uint32 = b"\x07"
    int64 = b"\x08"
    uint64 = b"\x09"
    float32 = b"\x0A"
    float64 = b"\x0B"
    string = b"\x0C"
    raw = b"\xFF"

class ParamFlags(Enum):
    normal = b"\x00"
    readonly = b"\x01"

class CommandUsage(Enum):
    Common = b"\x00"
    System = b"\x01"
