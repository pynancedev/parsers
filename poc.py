from pynance.message.format import TietoNative

sample = "1100f4340553a8e0b8000000000c100000001654307200000000020000000000000005250000000006254405122019011321280235122111012130461085999201901130000001420070913113215084280001107RTPSNIF345430720000000002D35121010950808620826102588524ATM000021000025        40Merchant 1000025>Riga                 LV42842888F17D635AB3E9BD089801100007RTPSNIF07RTPSNIF07RTPSNIF"

foo = TietoNative.parse(sample)
print(foo.dict())
print(foo.dict(True))

assert sample == foo.compose()

for name, field, value in foo.describe():
    print(
        name.rjust(5, " "),
        field.name.ljust(42) if field.name else field.name,
        value,
    )
