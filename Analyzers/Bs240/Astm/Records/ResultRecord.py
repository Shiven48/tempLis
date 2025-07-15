from astm.mapping import (
    Component, 
    TextField, 
    IntegerField,
    ConstantField,
    SetField,
    DecimalField,
    Record,
    ComponentField,
    NotUsedField
)

class AssayResultComponent(Component):
    assay_number        = TextField(name='assay_number', length=12)     
    assay_name          = TextField(name='assay_name', length=20)       
    replicate_number    = IntegerField(name='replicate_number', length=2)
    result_type         = SetField(                                      
        name='result_type',
        values={'I', 'F'},
        length=1
    )

class ResultValueComponent(Component):
    measurement_value  = DecimalField(name='measurement_value', length=14)      
    interpretation     = TextField(name='interpretation', length=15)            
    si_l_value         = DecimalField(name='si_l_value', length=14)            
    si_h_value         = DecimalField(name='si_h_value', length=14)            
    si_i_value         = DecimalField(name='si_i_value', length=14)            

class MeasurementComponent(Component):
    low_range          = DecimalField(name='range_low',  length=12)
    high_range         = DecimalField(name='range_high', length=12)

class OriginalResultComponent(Component):
    measurement_value = DecimalField(name='measurement_value', length=14)
    interpretation    = TextField(name='interpretation', length=15)
    si_l_value        = NotUsedField(name='si_l_value')
    si_h_value        = NotUsedField(name='si_h_value')
    si_i_value        = NotUsedField(name='si_i_value')

class InstrumentInfoComponent(Component):
    sender_name  = TextField(name='sender_name', length=16)
    device_id    = IntegerField(name='device_id', length=10)

class InstrumentComponent(Component):
    sender_name = TextField(name='sender_name', length=16)
    device_id   = IntegerField(name='devide_id', length=10)

ExtendedResultRecord = Record.build(
    ConstantField(name='record_type_id', default='R'),
    IntegerField(name='sequence_number'),
    ComponentField(AssayResultComponent, name='Assay_info'),
    ComponentField(ResultValueComponent, name='sample_position'),
    TextField(name='units', length=12),
    ComponentField(MeasurementComponent, name='MeasurementComponent'),  
    SetField(name='abnormal_flag', values={'L', 'H', 'N'}, length=1),
    TextField(name='abnormal_nature', length=15),
    SetField(name='result_status', values={'F'}, length=1),
    ComponentField(OriginalResultComponent, name='OriginalResultComponent'),
    NotUsedField(name='Operator Identification'),
    TextField(name='started_at', length=14),
    TextField(name='completed_at', length=14),
    ComponentField(InstrumentComponent, name='InstrumentComponent')
)

# newcls = type('ExtendedResultRecord', (cls,), {})
# for name, field in fields:
#     setattr(newcls, name, field)
# newcls._fields = fields
# return newcls