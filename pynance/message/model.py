class DataElement:
    pass


class Primary:
    """ Primary field is always present and does not depend on bits in bitmap """

    pass


class MTI(DataElement, Primary):
    def __init__(self, name="Message Type Identifier"):
        self.name = name

    def parse(self, msg):
        return 4, msg[:4]

    def compose(self, value):
        return value


class Bitmap(DataElement):
    def __init__(self, name):
        self.name = name

    def parse(self, msg):
        return 16, bin(int(msg[:16], 16))[2:].rjust(64, "0")

    def compose(self, value):
        return hex(int(value, 2))[2:].rjust(16, "0")


class PrimaryBitmap(Bitmap, Primary):
    pass


class XVAR(DataElement):
    X = 1

    def __init__(self, name=None, max_length=None):
        self.name = name
        if max_length is None:
            max_length = pow(10, self.X) - 1
        self.max_length = max_length

    def parse(self, msg):
        length = int(msg[: self.X])
        if length > self.max_length:
            raise ValueError(f"Value larger than maximum {self.max_length}")
        return self.X + length, msg[self.X : self.X + length]

    def compose(self, value):
        if len(value) > self.max_length:
            raise ValueError(f"Value larger than maximum {self.max_length}")
        return f"{len(value):0{self.X}}{value}"


class LVAR(XVAR):
    X = 1


class LLVAR(XVAR):
    X = 2


class LLLVAR(XVAR):
    X = 3


class LLLLVAR(XVAR):
    X = 4


class Fixed(DataElement):
    def __init__(self, name, length, rpad=None, lpad=None):
        self.name = name
        self.length = length
        self.rpad = rpad
        self.lpad = lpad

    def parse(self, msg):
        if self.rpad is not None:
            return self.length, msg[: self.length].rstrip(self.rpad)
        elif self.lpad is not None:
            return self.length, msg[: self.length].lstrip(self.lpad)
        return self.length, msg[: self.length]

    def compose(self, value):
        if len(value) > self.length:
            raise ValueError(f"Value larger than maximum {self.length}")
        if self.rpad is not None:
            return value.ljust(self.length, self.rpad)
        elif self.lpad is not None:
            return value.rjust(self.length, self.lpad)
        return value


class FixedString(Fixed):
    def __init__(self, name, length):
        super().__init__(name, length, rpad=" ")


class FixedNumber(Fixed):
    def __init__(self, name, length):
        super().__init__(name, length, lpad="0")


class MessageMeta(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        super_new = super().__new__

        # Also ensure initialization is only performed for subclasses of Message
        # (excluding Message class itself).
        parents = [b for b in bases if isinstance(b, MessageMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        # Create the class.
        module = attrs.pop("__module__")
        new_attrs = {"__module__": module}
        classcell = attrs.pop("__classcell__", None)
        if classcell is not None:
            new_attrs["__classcell__"] = classcell

        fields = {}
        for obj_name, obj in attrs.items():
            if isinstance(obj, DataElement):
                fields[obj_name] = obj
            else:
                new_attrs[obj_name] = obj
        new_attrs["_fields"] = fields
        new_class = super_new(cls, name, bases, new_attrs, **kwargs)
        return new_class


class Message(metaclass=MessageMeta):
    def __init__(self):
        for name in self._fields:
            setattr(self, name, None)

    def dict(self, full=False):
        result = {}
        for name in self._fields:
            value = getattr(self, name)
            if full or value is not None:
                result[name] = value
        return result

    def describe(self, full=False):
        for name, field in self._fields.items():
            value = getattr(self, name)
            if full or value is not None:
                yield name, field, value

class ISO8583Message(Message):
    @classmethod
    def parse(cls, data):
        bitmap = ""
        state = data

        message = cls()
        bit = 0
        for name, field in cls._fields.items():
            primary = isinstance(field, Primary)
            if not primary and bitmap[bit] == "0":
                pass
            else:
                length, value = field.parse(state)
                state = state[length:]
                setattr(message, name, value)
                if isinstance(field, Bitmap):
                    bitmap += value
            if not primary:
                bit += 1

        if len(state) != 0:
            raise ValueError(f"Have {len(state)} unparsed bytes")
        return message
