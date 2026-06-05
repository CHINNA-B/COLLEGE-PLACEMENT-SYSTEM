from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, FloatField, TextAreaField, SelectField
from wtforms.validators import DataRequired, NumberRange, Optional, Length


class ProfileForm(FlaskForm):
    name = StringField(
        'Full Name',
        validators=[DataRequired(message='Name is required.'), Length(max=120)]
    )
    branch = SelectField(
        'Branch',
        choices=[
            ('', '-- Select Branch --'),
            ('Computer Science', 'Computer Science'),
            ('Electronics', 'Electronics'),
            ('Mechanical', 'Mechanical'),
            ('Civil', 'Civil'),
            ('Electrical', 'Electrical'),
            ('Information Technology', 'Information Technology'),
            ('Chemical', 'Chemical'),
            ('Other', 'Other'),
        ],
        validators=[DataRequired(message='Please select your branch.')]
    )
    cgpa = FloatField(
        'CGPA',
        validators=[
            DataRequired(message='CGPA is required.'),
            NumberRange(min=0, max=10, message='CGPA must be between 0 and 10.')
        ]
    )
    skills = TextAreaField(
        'Skills',
        validators=[Optional(), Length(max=500)],
        render_kw={'placeholder': 'Python, Java, SQL, Machine Learning...'}
    )
    phone = StringField(
        'Phone Number',
        validators=[Optional(), Length(max=15)]
    )
    address = TextAreaField(
        'Address',
        validators=[Optional(), Length(max=300)]
    )
    resume = FileField(
        'Resume',
        validators=[
            FileAllowed(['pdf', 'doc', 'docx'], 'Only PDF, DOC, and DOCX files are allowed.')
        ]
    )
