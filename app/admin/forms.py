from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length


class BulkNotificationForm(FlaskForm):
    title = StringField(
        'Notification Title',
        validators=[DataRequired(), Length(min=3, max=150)]
    )
    message = TextAreaField(
        'Message',
        validators=[DataRequired(), Length(min=10, max=1000)]
    )
    target = SelectField(
        'Target Audience',
        choices=[
            ('all', 'All Users'),
            ('students', 'Students Only'),
            ('companies', 'Companies Only')
        ]
    )
    notif_type = SelectField(
        'Notification Type',
        choices=[
            ('info', 'Info'),
            ('success', 'Success'),
            ('warning', 'Warning'),
            ('danger', 'Danger')
        ]
    )
