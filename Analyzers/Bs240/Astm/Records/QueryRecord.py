from astm.mapping import (
    Record,
    TextField,
    IntegerField,
    ConstantField,
    SetField,
    NotUsedField,
    ComponentField
)

""" 
    As the astm library dont have the query record implementation 
    hence we are not creating ExtendedQueryRecord class as it has nothing
    to override as we did wirh ExtendedHeader and other classes. Hence,
    we are dorectly building the query record. 
"""

class PatientSampleIdMap:
    patient_id      = TextField(name='patient_id',  length=20) 
    specimen_id     = TextField(name='specimen_id', length=29)

ExtendedQueryRecord = Record.build(
    ConstantField(name='record_type_id', default='Q'),
    IntegerField(name='sequence_number', length=3),
    ComponentField(PatientSampleIdMap, name='patient_speciment_id'),
    NotUsedField(name='ending_range_id'),
    NotUsedField(name='universal_test_id'),
    NotUsedField(name='nature_of_request_time_limits'),
    TextField(name='begin_request_datetime', length=14),
    TextField(name='end_request_datetime', length=14),
    NotUsedField(name='requesting_physician_name'),
    NotUsedField(name='requesting_physician_telephone'),
    NotUsedField(name='user_field_1'),
    NotUsedField(name='user_field_2'),
    SetField(
        name='request_info_status_code',
        values={'O', 'A'},
        length=1
    ),
)