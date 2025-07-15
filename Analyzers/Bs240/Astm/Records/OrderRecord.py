from astm.mapping import (
    Component, 
    TextField, 
    IntegerField,
    ConstantField,
    ComponentField,
    SetField,
    DateTimeField,
    DecimalField,
    NotUsedField,
    Record,
    RepeatedComponentField
)
from astm.records import OrderRecord

class PatientNameComponent(Component):
    patient_name        = TextField(name='patient_name')
    last_name           = TextField(name='last_name',  length=20)
    first_name          = TextField(name='first_name', length=20)
    middle_name_initial = TextField(name='middle_name_initial', length=1)

class SamplePositionComponent(Component):
    sample_id           = TextField(name='sample_id', length=20)
    sample_tray_no      = IntegerField(name='sample_tray_no', length=2)
    sample_position_no  = IntegerField(name='sample_position_no', length=2)

# class AssayComponentInfo(Component):
#     assay_no            = TextField(name='assay_no', length=12)
#     assay_name          = TextField(name='assay_name', length=20)
#     dilution_rate       = IntegerField(name='dilution_rate', length=4)
#     repeat_no           = IntegerField(name='repeat_no', length=2)

class OrderingPhysicianComponent(Component):
    ordering_physician  = NotUsedField(name='ordering_physician')
    last_name           = TextField(name='last_name', length=20)
    first_name          = TextField(name='first_name', length=20)
    middle_initial      = TextField(name='middle_initial', length=1)    

class SenderNameComponent(Component):
    last_name       = TextField(name='last_name', length=20)
    first_name      = TextField(name='first_name', length=20)
    middle_initial  = TextField(name='middle_initial', length=1)


ExtendedOrderRecord = Record.build(
    ConstantField(name='record_type_id', default='O'),                          
    IntegerField(name='sequence_number'),                                       
    ComponentField(SamplePositionComponent, name='sample_position'),
    TextField(name='instrument_id', length=29),
    RepeatedComponentField(Component.build(
        TextField(name='test_code'),
        TextField(name='test_name'),
        NotUsedField(name='not_used_1'),
        NotUsedField(name='not_used_2')
    ), name='assay_info'),                     
    SetField(name='priority', values={'R', 'S'}),                   
    DateTimeField(name='created_at', length=14),                    
    DateTimeField(name='sampled_at', length=14), 
    NotUsedField(name='collection_end_datetime'),
    DecimalField(name='collection_volume', length=7),                        
    TextField(name='collector_id', length=18),       
    SetField(name='action_code', values={'A', 'N', 'R', 'C', 'F'}, length=1),   
    NotUsedField(name='danger_code'),                                    
    NotUsedField(name='clinical_info'),                                  
    TextField(name='delivered_at', length=14),            
    SetField(name='specimen_type',values={'serum', 'urine', 'CSF', 'plasma', 'timed', 'other','blood', 'amniotic', 'urethral', 'saliva', 'cervical', 'synovial'},length=10),
    ComponentField(OrderingPhysicianComponent, name='ordering_physician_info'), 
    TextField(name='physician_phone', length=30),
    NotUsedField(name='offline_dilution_factor'),
    ComponentField(SenderNameComponent, name='user_field_2'),
    NotUsedField(name='lab_field_1'),                                      
    NotUsedField(name='lab_field_2'),  
    NotUsedField(name='results_reported_datetime'),                                                                                            # 22
    NotUsedField(name='instrument_charge'),     
    NotUsedField(name='instrument_section_id'),
    SetField(name='report_type', values={'O', 'Q', 'F'}, length=1),
    NotUsedField(name='reserved_field_27'),                                
    NotUsedField(name='location_collected'),                               
    NotUsedField(name='nosocomial_infection_flag'),                        
    NotUsedField(name='specimen_service'),                                 
    NotUsedField(name='specimen_institution')     
)

# newcls = type('ExtendedOrderRecord', (cls,), {})
# for name, field in fields:
#     setattr(newcls, name, field)
# newcls._fields = fields
# return newcls