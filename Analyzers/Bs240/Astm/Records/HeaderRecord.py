from astm.mapping import (
    Record, TextField, ConstantField, NotUsedField,
    SetField, ComponentField, DateTimeField, Component
)
from datetime import datetime

class AddressComponent(Component):
    sender_name = TextField(name='sender_name')
    software_version = TextField(name='software_version')
    sequence_number = TextField(name='sequence_number')

ExtendedHeaderRecord = Record.build(
    ConstantField(name='record_type_id', default='H'),                
    ConstantField(name='delimeter', default='\\^&'),                  
    ComponentField(AddressComponent, name='sender_name_id'),                                 
    SetField(name='Processing_Id', values={'PR', 'QR', 'CR', 'RQ', 'QA', 'SA'}),
    TextField(name='protocol_version', length=10),                    
    DateTimeField(name='timestamp', default=datetime.now, required=True)
)

# newcls = type('ExtendedHeaderRecord', (cls,), {})
# for name, field in fields:
#     setattr(newcls, name, field)
# newcls._items = fields
# return newcls