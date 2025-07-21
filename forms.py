from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired, EqualTo, Length

class LoginForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=25)]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()]
    )
    submit = SubmitField('Login')


class SignupForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=25)]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password')]
    )
    dob = DateField(
        'Date of Birth',
        format='%Y-%m-%d',
        validators=[DataRequired()],
        render_kw={"placeholder": "YYYY-MM-DD"}
    )
    gender = SelectField(
        'Gender',
        choices=[
            ('', 'Select Gender'),
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other')
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Sign Up')
