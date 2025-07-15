from astm.mapping import (
    Record, TextField, ConstantField, SetField, NotUsedField
)

ExtendedCommentRecord = Record.build(
    ConstantField(name='record_type_id', default='C'),     
    NotUsedField(name='sequence_number'),                  
    ConstantField(name='comment_source', default='I'),     
    TextField(name='comment_text', length=90),             
    SetField(name='comment_type', values={'G', 'I'}, length=1)
)

# newcls = type('ExtendedCommentRecord', (cls,), {})
# for name, field in fields:
#     setattr(newcls, name, field)
# newcls._fields = fields
# return newcls
