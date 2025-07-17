# from astm.mapping import (
#     Record, TextField, ConstantField, SetField, NotUsedField, RepeatedComponentField
# )

# class AssayComponentInfo(Component):
#     assay_no            = TextField(name='assay_no', length=12)
#     assay_name          = TextField(name='assay_name', length=20)
#     dilution_rate       = IntegerField(name='dilution_rate', length=4)
#     repeat_no           = IntegerField(name='repeat_no', length=2)

# class PatientNameComponent(Component):
#     patient_name        = TextField(name='patient_name')
#     last_name           = TextField(name='last_name',  length=20)
#     first_name          = TextField(name='first_name', length=20)
#     middle_name_initial = TextField(name='middle_name_initial', length=1)

# class SamplePositionComponent(Component):
#     sample_id           = TextField(name='sample_id', length=20)
#     sample_tray_no      = IntegerField(name='sample_tray_no', length=2)
#     sample_position_no  = IntegerField(name='sample_position_no', length=2)

# class OrderingPhysicianComponent(Component):
#     ordering_physician  = NotUsedField(name='ordering_physician')
#     last_name           = TextField(name='last_name', length=20)
#     first_name          = TextField(name='first_name', length=20)
#     middle_initial      = TextField(name='middle_initial', length=1)    

# class SenderNameComponent(Component):
#     last_name       = TextField(name='last_name', length=20)
#     first_name      = TextField(name='first_name', length=20)
#     middle_initial  = TextField(name='middle_initial', length=1)


# ExtendedOrderRecord = Record.build(
#     ConstantField(name='record_type_id', default='O'),                          
#     IntegerField(name='sequence_number'),                                       
#     ComponentField(SamplePositionComponent, name='sample_position'),
#     TextField(name='instrument_id', length=29),
#     RepeatedComponentField(Component.build(
#         TextField(name='test_code'),
#         TextField(name='test_name'),
#         NotUsedField(name='not_used_1'),
#         NotUsedField(name='not_used_2')
#     ), name='assay_info'),                     
#     SetField(name='priority', values={'R', 'S'}),                   
#     DateTimeField(name='created_at', length=14),                    
#     DateTimeField(name='sampled_at', length=14), 
#     DecimalField(name='collection_volume', length=7),                        
#     TextField(name='collector_id', length=18),       
#     SetField(name='action_code', values={'A', 'N', 'R', 'C', 'F'}, length=1),                           
#     TextField(name='delivered_at', length=14),            
#     SetField(name='specimen_type',values={'serum', 'urine', 'CSF', 'plasma', 'timed', 'other','blood', 'amniotic', 'urethral', 'saliva', 'cervical', 'synovial'},length=10),
#     ComponentField(OrderingPhysicianComponent, name='ordering_physician_info'), 
#     TextField(name='physician_phone', length=30),
#     ComponentField(SenderNameComponent, name='user_field_2'),
#     SetField(name='report_type', values={'O', 'Q', 'F'}, length=1),    
# )

# class PatientAgeComponent(Component):
#     birth_date = TextField(name='birth_date', length=8)
#     age = IntegerField(name='age', length=6)
#     age_unit = SetField(name='age_unit', values={'Y', 'M', 'W', 'D', 'H'}, default='Y', length=1)

# ExtendedPatientRecord = Record.build(
#     ConstantField(name='record_type_id', default='P'),                       
#     IntegerField(name='sequence_number', length=3),                                                        
#     TextField(name='patient_id', length=25),                                                                      
#     ComponentField(PatientNameComponent, name='patient_name'),                                               
#     ComponentField(PatientAgeComponent, name='age_info'),                    
#     SetField(name='patient_sex', values={'M', 'F', 'U'}, length=1),          
#     TextField(name='patient_race', length=20),                               
#     TextField(name='patient_address', length=50),                                                                   
#     TextField(name='patient_telephone', length=13),                                                              
#     TextField(name='special_field_1', length=30),                            
#     TextField(name='body_surface_area', length=20),                                                         
#     TextField(name='patient_diagnosis', length=50),                                                            
#     TextField(name='location', length=10),                                   
#     TextField(name='alt_diag_code', length=10),                                                                 
# )

# class PatientSampleIdMap:
#     patient_id      = TextField(name='patient_id',  length=20) 
#     specimen_id     = TextField(name='specimen_id', length=29)

# ExtendedQueryRecord = Record.build(
#     ConstantField(name='record_type_id', default='Q'),
#     IntegerField(name='sequence_number', length=3),
#     ComponentField(PatientSampleIdMap, name='patient_speciment_id'),
#     NotUsedField(name='ending_range_id'),
#     NotUsedField(name='universal_test_id'),
#     NotUsedField(name='nature_of_request_time_limits'),
#     TextField(name='begin_request_datetime', length=14),
#     TextField(name='end_request_datetime', length=14),
#     NotUsedField(name='requesting_physician_name'),
#     NotUsedField(name='requesting_physician_telephone'),
#     NotUsedField(name='user_field_1'),
#     NotUsedField(name='user_field_2'),
#     SetField(
#         name='request_info_status_code',
#         values={'O', 'A'},
#         length=1
#     ),
# )


# class AssayResultComponent(Component):
#     assay_number        = TextField(name='assay_number', length=12)     
#     assay_name          = TextField(name='assay_name', length=20)       
#     replicate_number    = IntegerField(name='replicate_number', length=2)
#     result_type         = SetField(                                      
#         name='result_type',
#         values={'I', 'F'},
#         length=1
#     )

# class ResultValueComponent(Component):
#     measurement_value  = DecimalField(name='measurement_value', length=14)      
#     interpretation     = TextField(name='interpretation', length=15)            
#     si_l_value         = DecimalField(name='si_l_value', length=14)            
#     si_h_value         = DecimalField(name='si_h_value', length=14)            
#     si_i_value         = DecimalField(name='si_i_value', length=14)            

# class MeasurementComponent(Component):
#     low_range          = DecimalField(name='range_low',  length=12)
#     high_range         = DecimalField(name='range_high', length=12)

# class OriginalResultComponent(Component):
#     measurement_value = DecimalField(name='measurement_value', length=14)
#     interpretation    = TextField(name='interpretation', length=15)
#     si_l_value        = NotUsedField(name='si_l_value')
#     si_h_value        = NotUsedField(name='si_h_value')
#     si_i_value        = NotUsedField(name='si_i_value')


# class InstrumentComponent(Component):
#     sender_name = TextField(name='sender_name', length=16)
#     device_id   = IntegerField(name='devide_id', length=10)

# ExtendedResultRecord = Record.build(
#     ConstantField(name='record_type_id', default='R'),
#     IntegerField(name='sequence_number'),
#     ComponentField(AssayResultComponent, name='Assay_info'),
#     ComponentField(ResultValueComponent, name='sample_position'),
#     TextField(name='units', length=12),
#     ComponentField(MeasurementComponent, name='MeasurementComponent'),  
#     SetField(name='abnormal_flag', values={'L', 'H', 'N'}, length=1),
#     TextField(name='abnormal_nature', length=15),
#     SetField(name='result_status', values={'F'}, length=1),
#     ComponentField(OriginalResultComponent, name='OriginalResultComponent'),
#     TextField(name='started_at', length=14),
#     TextField(name='completed_at', length=14),
#     ComponentField(InstrumentComponent, name='InstrumentComponent')
# )

# ExtendedTerminatorRecord = Record.build(
#     ConstantField(name='type', default='L'),
#     IntegerField(name='seq', length=3),
#     SetField(name='code', values={'N', 'I', 'Q'}, length=1)
# )