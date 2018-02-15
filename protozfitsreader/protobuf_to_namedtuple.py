from enum import Enum
from collections import namedtuple
import numpy as np
from protozfitsreader import rawzfitsreader
from protozfitsreader import L0_pb2

from google.protobuf.pyext.cpp_message import GeneratedProtocolMessageType
from CoreMessages_pb2 import AnyArray


class File:
    def __init__(self, path):
        self.path = path
        rawzfitsreader.open(path+":Events")

    def __len__(self):
        # not sure if (self.path) is needed
        return rawzfitsreader.getNumRows(self.path)

    def __iter__(self):
        return self

    def __next__(self):
        event = L0_pb2.CameraEvent()
        try:
            event.ParseFromString(rawzfitsreader.readEvent())
            return make_namedtuple(event)
        except EOFError:
            raise StopIteration


def make_namedtuple(message):
    namedtuple_class = named_tuples[message.__class__]
    return namedtuple_class._make(
        message_getitem(message, name)
        for name in namedtuple_class._fields
    )


def message_getitem(msg, name):
    value = msg.__getattribute__(name)
    if isinstance(value, AnyArray):
        value = any_array_to_numpy(value)
    elif (msg.__class__, name) in enum_types:
        value = enum_types[(msg.__class__, name)](value)
    elif type(value) in named_tuples:
        value = make_namedtuple(value)
    return value


messages = set([
    getattr(L0_pb2, name)
    for name in dir(L0_pb2)
    if isinstance(getattr(L0_pb2, name), GeneratedProtocolMessageType)
])

named_tuples = {
    m: namedtuple(
        m.__name__,
        list(m.DESCRIPTOR.fields_by_name)
    )
    for m in messages
}

enum_types = {}
for m in messages:
    d = m.DESCRIPTOR
    for field in d.fields:
        if field.enum_type is not None:
            et = field.enum_type
            enum = Enum(
                field.name,
                zip(et.values_by_name, et.values_by_number)
            )
            enum_types[(m, field.name)] = enum


def any_array_to_numpy(any_array):
    any_array_type_to_numpy_type = {
        1: np.int8,
        2: np.uint8,
        3: np.int16,
        4: np.uint16,
        5: np.int32,
        6: np.uint32,
        7: np.int64,
        8: np.uint64,
        9: np.float,
        10: np.double,
    }
    if any_array.type == 0:
        if any_array.data:
            raise Exception("any_array has no type", any_array)
        else:
            return np.array([])
    if any_array.type == 11:
        print(any_array)
        raise Exception(
            "I have no idea if the boolean representation of"
            " the anyarray is the same as the numpy one",
            any_array
        )

    return np.frombuffer(
        any_array.data,
        any_array_type_to_numpy_type[any_array.type]
    )

if __name__ is '__main__':
    path = 'example_10evts.fits.fz'
    file = File(path)
    event = next(file)
