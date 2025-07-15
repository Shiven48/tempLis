from astm.mapping import (
    ConstantField,
    Record,
    IntegerField,
    SetField
)

ExtendedTerminatorRecord = Record.build(
    ConstantField(name='type', default='L'),
    IntegerField(name='seq', length=3),
    SetField(name='code', values={'N', 'I', 'Q'}, length=1)
)

# newcls = type('ExtendedTerminatorRecord', (cls,), {})
# for name, field in fields:
#     setattr(newcls, name, field)
# newcls._fields = fields
# return newcls
    