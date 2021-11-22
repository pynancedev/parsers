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


class ISO8583Message(Message):
    @classmethod
    def parse(cls, data):
        bitmap = ""
        state = data

        model = cls()
        bit = 0
        for name, field in cls._fields.items():
            primary = isinstance(field, Primary)
            if not primary and bitmap[bit] == "0":
                pass
            else:
                length, value = field.parse(state)
                state = state[length:]
                setattr(model, name, value)
                if isinstance(field, Bitmap):
                    bitmap += value
            if not primary:
                bit += 1

        assert len(state) == 0

        bit = 0
        for name, field in cls._fields.items():
            if getattr(model, name) is not None:
                print(
                    name.rjust(5, " "),
                    field.name.ljust(42) if field.name else field.name,
                    getattr(model, name),
                )
        return model


class TietoNative(ISO8583Message):
    """ Tieto Card Suite Native interface """

    mti = MTI("Message Type Identifier")
    b1 = PrimaryBitmap("Primary bitmap")

    de1 = Bitmap("Secondary bitmap")
    de2 = LLVAR("Primary account number (PAN)", max_length=19)
    de3 = FixedString("Processing code", 6)
    de4 = FixedNumber("Amount, transaction", 12)
    de5 = FixedNumber("Amount, settlement", 12)
    de6 = FixedNumber("Amount, cardholder billing", 12)
    de7 = FixedString("Date and time, transaction", 14)
    de8 = FixedString("Amount, cardholder billing fee", 8)
    de9 = FixedNumber("Conversion rate, reconciliation", 8)
    de10 = FixedNumber("Conversion rate, cardholder billing", 8)
    de11 = FixedString("System trace audit number (STAN)", 6)
    de12 = FixedString("Date and time, local transaction", 14)
    de13 = FixedString("Date, effective", 4)
    de14 = FixedString("Date, expiration", 4)
    de15 = FixedString("Date, settlement", 14)
    de16 = FixedString("Date, conversion", 4)
    de17 = FixedString("Date, capture", 4)
    de18 = FixedString("Merchant type", 4)
    de19 = FixedString("Country code, acquiring institution", 3)
    de20 = FixedString("Country code, PAN", 3)
    de21 = FixedString("Country code, forwarding institution", 3)
    de22 = FixedString("POS data code (point code", 12)
    de23 = FixedString("Card sequence number", 3)
    de24 = FixedString("Function code", 3)
    de25 = FixedString("Message reason code", 4)
    de26 = FixedString("Card acceptor business code", 4)
    de27 = FixedString("Approval code length", 1)
    de28 = FixedString("Date, reconciliation", 14)
    de29 = FixedString("Reconciliation, indicator", 3)
    de30 = FixedString("Amounts, original", 24)
    de31 = LLVAR("ATM audit ID")
    de32 = LLVAR("Acquirer ID")
    de33 = LLVAR("Forwarder ID")
    de34 = LLVAR("PAN, extended")
    de35 = LLVAR("Track 2 data")
    de36 = LLLVAR("Track 3 data")
    de37 = FixedString("Retrieval reference number", 12)
    de38 = FixedString("Approval code", 6)
    de39 = FixedString("Action code", 3)
    de40 = FixedString("Service code", 3)
    de41 = FixedString("Card acceptor terminal identification", 8)
    de42 = FixedString("Card acceptor identification", 15)
    de43 = LLVAR("Card acceptor name/location")
    de44 = LLVAR("Additional response data")
    de45 = LLVAR("Track 1 data")
    de46 = LLLVAR("Amounts, fees")
    de47 = LLLVAR("Additional data, national")
    de48 = LLLVAR("Additional data, private")
    de49 = FixedString("Currency code, transaction", 3)
    de50 = FixedString("Currency code, reconciliation", 3)
    de51 = FixedString("Currency code, cardholder billing", 3)
    de52 = FixedString("PIN data", 16)
    de53 = LLVAR("Security related control information")
    de54 = LLLVAR("Amounts, additional")
    de55 = LLLVAR("Integrated circuit card system related data")
    de56 = LLVAR("Original data elements")
    de57 = FixedString("Authorization life cycle code", 3)
    de58 = LLVAR("Authorizing agent ID")
    de59 = LLLVAR("Transport data")
    de60 = LLLVAR("Reserved for national use")
    de61 = LLLVAR("Reserved for national use")
    de62 = LLLVAR("Reserved for private use")
    de63 = LLLVAR("Reserved for private use")
    de64 = FixedString("Message authentication code (MAC)", 16)
    de65 = FixedString("Reserved for ISO code", 16)
    de66 = LLLVAR("Amounts, original fees")
    de67 = FixedString("Extended payment data", 2)
    de68 = FixedString("Country code, receiving institution", 3)
    de69 = FixedString("Country code, settlement institution", 3)
    de70 = FixedString("Country code, authorizing agent", 3)
    de71 = FixedString("Message number", 8)
    de72 = LLLVAR("Data record")
    de73 = FixedString("Date, action", 6)
    de74 = FixedNumber("Credits, number", 10)
    de75 = FixedNumber("Credits, reversal number", 10)
    de76 = FixedNumber("Debits, number", 10)
    de77 = FixedNumber("Debits, reversal number", 10)
    de78 = FixedNumber("Transfer, number", 10)
    de79 = FixedNumber("Transfer, reversal number", 10)
    de80 = FixedNumber("Inquiries, number", 10)
    de81 = FixedNumber("Authorizations, number", 10)
    de82 = FixedNumber("Inquiries, reversal number", 10)
    de83 = FixedNumber("Payments, number", 10)
    de84 = FixedNumber("Payments, reversal number", 10)
    de85 = FixedNumber("Fee collections, number", 10)
    de86 = FixedNumber("Credits, amount", 16)
    de87 = FixedNumber("Credits, reversal amount", 16)
    de88 = FixedNumber("Debits, amount", 16)
    de89 = FixedNumber("Debits, reversal amount", 16)
    de90 = FixedNumber("Authorizations, reversal number", 10)
    de91 = FixedString("Country code, transaction destination institution", 3)
    de92 = FixedString("Country code, transaction originator institution", 3)
    de93 = LLVAR("Transaction destination institution ID")
    de94 = LLVAR("Transaction originator institution ID")
    de95 = LLVAR("Card issuer reference data")
    de96 = LLLVAR("Key management data")
    de97 = FixedString("Amount, net reconciliation", 17)
    de98 = FixedString("Payee", 25)
    de99 = LLVAR("Settlement institution ID")
    de100 = LLVAR("Receiving institution ID")
    de101 = LLVAR("File name")
    de102 = LLVAR("Account identification 1")
    de103 = LLVAR("Account identification 2")
    de104 = LLLVAR("Transaction description")
    de105 = FixedString("Credits, chargeback amount", 16)
    de106 = FixedString("Debits, chargeback amount", 16)
    de107 = FixedString("Credits, chargeback number", 10)
    de108 = FixedString("Debits, chargeback number", 10)
    de109 = LLVAR("Credits, fee amounts")
    de110 = LLVAR("Debits, fee amounts")
    de111 = LLLVAR("Reserved for ISO use")
    de112 = LLLVAR("Reserved for ISO use")
    de113 = LLLVAR("Reserved for ISO use")
    de114 = LLLVAR("Reserved for ISO use")
    de115 = LLLVAR("Reserved for ISO use")
    de116 = LLVAR("Reserved for national use")
    de117 = LLVAR("Reserved for national use")
    de118 = LLVAR("Reserved for national use")
    de119 = LLVAR("Reserved for national use")
    de120 = LLVAR("Reserved for national use")
    de121 = LLLVAR("Reserved for national use")
    de122 = LLLVAR("Acquirer additional data transport field (limited usage)")
    de123 = LLLVAR("Prevalidation results")
    de124 = LLLVAR("Reserved for private use")
    de125 = LLLVAR("Reserved for private use")
    de126 = LLLLVAR("Acquirer request additional data")
    de127 = LLLVAR("Reserved for private use")
    de128 = FixedString("Message authentication code (MAC)", 16)


sample = "1100f4340553a8e0b8000000000c100000001654307200000000020000000000000005250000000006254405122019011321280235122111012130461085999201901130000001420070913113215084280001107RTPSNIF345430720000000002D35121010950808620826102588524ATM000021000025        40Merchant 1000025>Riga                 LV42842888F17D635AB3E9BD089801100007RTPSNIF07RTPSNIF07RTPSNIF"

foo = TietoNative.parse(sample)
print(foo.dict())
print(foo.dict(True))
