from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class RegisterForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(message='Username is required.'),
            Length(min=3, max=80, message='Username must be between 3 and 80 characters.')
        ]
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email is required.'),
            Email(message='Please enter a valid email address.')
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.'),
            Length(min=6, message='Password must be at least 6 characters long.')
        ]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password.'),
            EqualTo('password', message='Passwords must match.')
        ]
    )
    role = SelectField(
        'Register as',
        choices=[('student', 'Student'), ('company', 'Company')],
        validators=[DataRequired()]
    )


class LoginForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(message='Email is required.')]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(message='Password is required.')]
    )
    remember_me = BooleanField('Remember Me')
