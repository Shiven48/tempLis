from astm.mapping import (
    Record, TextField, IntegerField, SetField,
    NotUsedField, ConstantField, ComponentField, Component
)

# Name component (Field 6)
class PatientNameComponent(Component):
    last_name = TextField(name='last_name', length=20)
    first_name = TextField(name='first_name', length=20)
    middle_initial = TextField(name='middle_initial', length=1)

# Age + Birthdate component (Field 8)
class PatientAgeComponent(Component):
    birth_date = TextField(name='birth_date', length=8)
    age = IntegerField(name='age', length=6)
    age_unit = SetField(name='age_unit', values={'Y', 'M', 'W', 'D', 'H'}, default='Y', length=1)

ExtendedPatientRecord = Record.build(
    ConstantField(name='record_type_id', default='P'),                       
    IntegerField(name='sequence_number', length=3),                          
    NotUsedField(name='practice_assigned_id'),                               
    TextField(name='patient_id', length=25),                                 
    NotUsedField(name='patient_id_3'),                                       
    ComponentField(PatientNameComponent, name='patient_name'),               
    NotUsedField(name='reserved_field_7'),                                   
    ComponentField(PatientAgeComponent, name='age_info'),                    
    SetField(name='patient_sex', values={'M', 'F', 'U'}, length=1),          
    TextField(name='patient_race', length=20),                               
    TextField(name='patient_address', length=50),                            
    NotUsedField(name='blood_type'),                                         
    TextField(name='patient_telephone', length=13),                          
    NotUsedField(name='physician_name'),                                     
    TextField(name='special_field_1', length=30),                            
    TextField(name='body_surface_area', length=20),                          
    NotUsedField(name='patient_height'),                                     
    NotUsedField(name='patient_height_unit'),                                
    NotUsedField(name='patient_weight'),                                     
    NotUsedField(name='patient_weight_unit'),                                
    TextField(name='patient_diagnosis', length=50),                          
    NotUsedField(name='patient_medications'),                                
    NotUsedField(name='patient_diet'),                                       
    NotUsedField(name='practice_field_1'),                                   
    NotUsedField(name='practice_field_2'),                                   
    TextField(name='location', length=10),                                   
    TextField(name='alt_diag_code', length=10),                              
    NotUsedField(name='alt_diag_code_class'),                                
    NotUsedField(name='patient_religion'),                                   
    NotUsedField(name='marital_status'),                                     
    NotUsedField(name='isolation_status'),                                   
    NotUsedField(name='language'),                                           
    NotUsedField(name='hospital_service'),                                   
    NotUsedField(name='hospital_institution'),                               
    NotUsedField(name='dosage_category'),                                    
)



# Build a new class
# newcls = type('ExtendedPatientRecord', (cls,), {})
# for name, field in fields:
#     setattr(newcls, name, field)
# newcls._fields = fields
# return newcls