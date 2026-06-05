from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, FloatField, SelectField,
    DateField, TimeField
)
from wtforms.validators import (
    DataRequired, Email, Optional, NumberRange, Length
)


class CompanyProfileForm(FlaskForm):
    """Form for company profile creation and editing."""

    company_name = StringField(
        'Company Name',
        validators=[DataRequired(), Length(min=2, max=200)]
    )
    industry = SelectField(
        'Industry',
        choices=[
            ('', '-- Select Industry --'),
            ('IT/Software', 'IT/Software'),
            ('Finance', 'Finance'),
            ('Consulting', 'Consulting'),
            ('Manufacturing', 'Manufacturing'),
            ('Healthcare', 'Healthcare'),
            ('Education', 'Education'),
            ('E-commerce', 'E-commerce'),
            ('Other', 'Other')
        ],
        validators=[Optional()]
    )
    website = StringField(
        'Website',
        validators=[Optional(), Length(max=200)]
    )
    description = TextAreaField(
        'Company Description',
        validators=[Optional(), Length(max=2000)]
    )
    contact_email = StringField(
        'Contact Email',
        validators=[DataRequired(), Email(), Length(max=120)]
    )
    contact_phone = StringField(
        'Contact Phone',
        validators=[Optional(), Length(max=20)]
    )


class JobPostForm(FlaskForm):
    """Form for creating a new job posting."""

    title = StringField(
        'Job Title',
        validators=[DataRequired(), Length(min=2, max=200)]
    )
    description = TextAreaField(
        'Job Description',
        validators=[DataRequired(), Length(min=10, max=5000)]
    )
    min_cgpa = FloatField(
        'Minimum CGPA',
        default=0.0,
        validators=[Optional(), NumberRange(min=0, max=10, message='CGPA must be between 0 and 10')]
    )
    required_skills = TextAreaField(
        'Required Skills',
        validators=[Optional()],
        description='Enter skills separated by commas'
    )
    eligible_branches = TextAreaField(
        'Eligible Branches',
        validators=[Optional()],
        description='Enter branches separated by commas'
    )
    location = StringField(
        'Location',
        validators=[Optional(), Length(max=200)]
    )
    salary_lpa = FloatField(
        'Salary (LPA)',
        default=0.0,
        validators=[Optional(), NumberRange(min=0, message='Salary cannot be negative')]
    )
    job_type = SelectField(
        'Job Type',
        choices=[
            ('Full-time', 'Full-time'),
            ('Internship', 'Internship'),
            ('Part-time', 'Part-time')
        ],
        validators=[DataRequired()]
    )
    deadline = DateField(
        'Application Deadline',
        validators=[Optional()],
        format='%Y-%m-%d'
    )


class InterviewForm(FlaskForm):
    """Form for scheduling an interview."""

    scheduled_date = DateField(
        'Interview Date',
        validators=[DataRequired()],
        format='%Y-%m-%d'
    )
    scheduled_time = TimeField(
        'Interview Time',
        validators=[DataRequired()],
        format='%H:%M'
    )
    mode = SelectField(
        'Interview Mode',
        choices=[
            ('online', 'Online'),
            ('offline', 'Offline')
        ],
        validators=[DataRequired()]
    )
    venue_or_link = StringField(
        'Venue / Meeting Link',
        validators=[DataRequired(), Length(max=500)]
    )
