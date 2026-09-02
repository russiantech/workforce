
import re
from flask import jsonify
from flask_login import current_user
from wtforms.csrf.session import SessionCSRF
from flask_wtf import FlaskForm

# from wtforms import FileField
# from flask_wtf.file import FileAllowed

# from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    #FileField, 
    DateField, StringField, 
    TextAreaField, PasswordField, SubmitField, 
    BooleanField, SelectField
    )

from wtforms.validators import (
    Optional, DataRequired, Length, Email, EqualTo, ValidationError)
from web.models.users import User, Role

"""  """
from flask_wtf.file import FileField, FileAllowed
"""  """
level_choice = [('','Course Level'), ('novice','Novice'), ('beginner','Beginner'), ('expert','Expert'),  ('pro','Pro'), ('advanced','Advanced') ]
gender_choice = [('', 'Gender'), ('f', 'Female'), ('m', 'Male')]
lang_choice = [('', 'language'), ('english', 'english'), ('french', 'french'), ('spanish', 'spanish'), ('latin', 'latin'), ('pidgin', 'pidgin'), ('other', 'other')]
city_choice = [('', 'current city'), ('Lagos','Lagos'), ('Portharcourt','Portharcourt'), ('New York','New York'), ('Canada','Canada'), ('Calabar','Calabar'), ('Uyo','Uyo')]
role_choice = [('', 'Assign Role')]
#role_choice = [(r.name, r.name) for r in Role.query.all()]

bank_choice = [
    ('', 'Bank'), ('fcmb','First City Monument Bank'), 
    ('uba','United Bank Of Africa'), ('first bank','First Bank'), \
    ('opay','Opay'), ('union bank','Union Bank'), ('gtb','Quaranty Trust Bank'), 
    ('ecobank','Eco bank'), ('access bank','Access Bank')]

completion_status_choice = [
    ('', 'Set Completion Status'), 
    ('completed','Completed'), 
    ('on-going','On going'), 
    ('suspended','Suspended'), 
    ('stopped','Stopped'), 
    ]

cert_status_choice = [
    ('', 'Certificate Status'), 
    ('collect','Completed'), 
    ('not collected','Not Collected'), 
    ('pending','Pending'), 
    ('qualified','Qualified'), 
    ('not qualified','Not Qualified'), 
    ]

qualification_choice = [
    ('', 'Academic Qualification'), 
    ('FSLC','FSLC'), 
    ('SSCE','SSCE'), 
    ('OND','OND'), 
    ('HND','HND'), 
    ('College','College'), 
    ('Bsc','Degree'), 
    ('Msc','Msc'), 
    ('Phd','PHD'), 
    ('Pgd','PGD'),
    ]

# Generate choices for years of experience from 1 to 30
experience_years_choice = [
    ("0", 'Years Of Experience'),  # Initial default option
] + [(str(i), str(i)) for i in range(1, 31)]  # List comprehension to generate options for 1 to 30 years


experience_level_choice = [
    ('', 'Experience Level'), 
    ('professional-level','Professional Level'), 
    ('entry-level','Entry Level'), 
    ('medium-level','Medium Level'), 
    ('no-experience','No Experience'), 
    ]

refferee_choice = [
    ('', 'Who\'s this to you?'), 
    ('father','My Father'), 
    ('mother','My Mother'), 
    ('uncle','My Uncle'), 
    ('aunt','My Aunt'), 
    ('friend','My Friend'), 
    ('others','Other'), 
    ]

course_choice = [
    ('', 'Courses'), 
    ('frontend','Frontend Development'), 
    ('cloud-security','Cloud Security'), 
    ('digital-marketing','Digital Marketing'), 
    ('3d-animation','3D Animation'), 
    ('scratch','Scratch'), 
    ('computer-fundamentals','Computer Fundamentals'),
    ('coding-fundamentals','Coding Fundamentals'),
    ('backend-development','Backend Development'), 
    ('full-stack','Fullstack Development'),
    ('data-science','Data Science / Analysis'), 
    ('cyber-security','Cyber Security'), 
    ('software-enginnering','Software Engineering'), 
    ('ui/ux','UI/UX Design'),
    ('graphics','Graphic Design'), 
    ('kid-basic-ict','Kids Basic ICT'),
    ('coders-web','Coder Web'),
    ('coders-stage-01','Coders Stage 01'),
    ('coders-stage-02','Coders Stage 02'),
    ('coders-stage-03','Coders Stage 03')
    ]

category_choice = [
    ('', 'Choose one'), 
    ('staff', 'Staff(Full time)'), 
    ('intern-staff', 'Intern Staffs'), 
    ('corper-staff', 'Corper Staffs'), 
    ('intern-student', 'Intern Students'), 
    ('customer', 'Customer'), 
    ('student', 'Student')
    ]

def is_admin(user):
    return user.is_authenticated and 'admin' in user.roles
    # return 'admin' in user.roles
# photo = FileField('Photo', validators=[FileAllowed(['jpg', 'svg', 'webp', 'gif', 'jpeg', 'png'])])

class QueryForm(FlaskForm):
    file = FileField('Attach File', validators=[DataRequired()])
    message = TextAreaField('Message')
    submit = SubmitField('Send Query')
    
class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=2, max=50)])
    tnc = BooleanField('Terms & Conditions', validators=[DataRequired()])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        excluded_chars = " *?!'^+%&/()=}][{$#" #clean_ups
        for char in self.username.data:
            if char in excluded_chars:
                # raise ValidationError(f"Character {char} Is Not Allowed In Username.") 
                message = f"Character {char} Is Not Allowed In Username."
                return jsonify({"success": False, "error": str(message) }), 200

        user = User.query.filter_by(username=username.data).first()
        if user:
            # raise ValidationError('That username is taken. Please choose a different one.')
            message = 'That username is taken. Please choose a different one.'
            return jsonify({"success": False, "error": str(message) }), 200
        
    def validate_phone(self, phone):
        excluded_chars = "~@*?!;$%`\":<>'^%&/()=}][{$#" #clean_ups
        for char in self.phone.data:
            if char in excluded_chars:
                # raise ValidationError(f"Character {char} Is Not Allowed In Phone Numbers.") 
                message = f"Character {char} Is Not Allowed In Phone Numbers."
                return jsonify({"success": False, "error": str(message) }), 200 
            
            if len(phone.data) < 7:
                # raise ValidationError(f" ({phone.data}) Is Not A Valid Phone Number.") 
                message = f" ({phone.data}) Is Not A Valid Phone Number."
                return jsonify({"success": False, "error": str(message) }), 200 
            
        user = User.query.filter_by(phone=phone.data).first()
        if user:
            # raise ValidationError('That Phone Number is Already In Use. Please choose a different one.')
            message = 'That Phone Number is Already In Use. Please choose a different one.'
            return jsonify({"success": False, "error": str(message) }), 200 
        
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            # raise ValidationError('That email is taken. Please choose a different one.')
            message = 'That email is taken. Please choose a different one.'
            return jsonify({"success": False, "error": str(message) }), 200 

class SigninForm(FlaskForm):
    signin = StringField('Username, Email Or Phone', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

    def validate_me(self, email):
        if User.query.filter_by(email=email.data).first():
            # raise ValidationError('Invalid login details, consider trying again.')
            message = "Invalid login details, consider trying again."
            return jsonify({"success": False, "error": str(message) }), 200

class UpdateMeForm(FlaskForm):
    photo = FileField('Photo', validators=[FileAllowed(['jpg', 'svg', 'webp', 'gif', 'jpeg', 'png'])])
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=20)])
    username = StringField('Username:', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Mobile Number',  validators=[ DataRequired(), Length(min=2, max=12)])
    password = StringField('Password:')
    repeat_password = StringField('Repeat Password:')
    # acct_no = StringField('Account Number:',  validators=[Length(min=10, max=10)])
    acct_no = StringField('Account Number:', validators=[Optional(), Length(min=10, max=10)])
    bank = SelectField('Bank:', validators=[Optional()], choices=bank_choice )
    city = SelectField('City', choices=city_choice, validators=[DataRequired()])
    address = StringField('Your Residential Address', validators=[DataRequired()])
    # role = SelectField('My Role', coerce=int, choices=role_choice)
    role = SelectField('My Role', choices=role_choice)
    category = SelectField('User Category', choices=category_choice )
    gender = SelectField('Gender', validators=[DataRequired()], choices=gender_choice)
    about = TextAreaField('About You')
    
    instagram = StringField('Instagram Url:')
    facebook = StringField('Facebook Url:')
    twitter = StringField('Twitter Url:')
    linkedin = StringField('Linkedin Url:')
    
    """ staffs-only """
    designation = StringField('Your Designation:')
    academic_qualification = SelectField('Academic Qualification:', validators=[Optional()], choices=qualification_choice)
    experience_years = SelectField('Years Of Experience:', validators=[Optional()], choices=experience_years_choice)
    experience_level = SelectField('Experience Level:', validators=[Optional()], choices=experience_level_choice )
    
    """ Reffere & Quarantor """
    refferee_type = SelectField('Who\'s this Person to you?:', choices=refferee_choice )
    refferee_email = StringField('Refferee Email Address:')
    refferee_phone = StringField('Refferee Phone Number:')
    refferee_address = StringField('Refferee\'s Address:')
    
    dob = DateField('Date Of Birth', validators=[DataRequired()], format='%Y-%m-%d')
    reg_num = StringField('Reg/ID Number:')
    course = SelectField('Enrolled in:', choices=course_choice )
    cert_status = SelectField('Certificate Status:', choices=cert_status_choice )
    completion_status = SelectField('Completion Status:', choices=completion_status_choice )
    
    submit = SubmitField('Save Informations')

    def load_role(self):
        self.role = Role.query.all()
        return self.role
    
    """ def validate_critical_fields(self):
        # Check if the current user is an admin
        if not current_user.is_admin():
            message = "Admin privileges are required to update the following fields:\
                password, username, registration number, course, completion status & certificate status."
            return jsonify({"success": False, "error": str(message)}), 200
        return jsonify({"success": True}), 200 """
    
    
    def validate_password(self, password):
        # Check if the current user is an admin
        if not current_user.is_admin() and password:
            message = "Admin privileges are required to update another user's password."
            return jsonify({"success": False, "error": str(message)}), 200

        # Add any additional password validation logic here
        # For example, checking if the password meets certain complexity requirements

        # If validation passes, return success
        # return jsonify({"success": True}), 200

    def validate_reg_num(self, reg_num):
        # Define excluded characters (including foreign characters)
        excluded_chars = re.compile(r'[^a-zA-Z0-9]')
        
        # Check for excluded characters
        if excluded_chars.search(reg_num.data):
            # raise ValidationError("Registration number contains invalid characters. Only letters and numbers are allowed.")
            message = "Registration number contains invalid characters. Only letters and numbers are allowed."
            return jsonify({"success": False, "error":str(message)}), 200
        
        # Check if the user is not an admin and trying to change the registration number
        if not current_user.is_admin():
            if reg_num.data != current_user.reg_num:
                # raise ValidationError("Only admins can change the registration number.")
                message = "Only admins can change the registration number."
                return jsonify({"success": False, "error":str(message)}), 200
        
        # Check for duplicates in the database, excluding current_user(who owns it initially)
        existing_user = User.query.filter(User.reg_num == reg_num.data, User.username\
            != current_user.username).first()
        if existing_user:
            # raise ValidationError(f'That registration number `{reg_num.data}` is already taken. Please choose a different one.')
            message = f'That registration number `{reg_num.data}` is already taken. Please choose a different one.'
            return jsonify({"success": False, "error":str(message)}), 200


    def validate_username(self, username):
        #if ( (current_user.is_admin()) | (current_user.username == usr.username) ):
        # Check if the current user is an admin or if they are changing their own username
        if username.data != current_user.username and not current_user.is_admin():
            return jsonify({"success": False, "error": "Only admins can change another user's username."}), 200
        
        excluded_chars = " *?!'^+%&/()=}][{$#"
        for char in self.username.data:
            if char in excluded_chars:
                # raise ValidationError(f"Character {char} Is Not Allowed In Username.") 
                message = f"Character {char} Is Not Allowed In Username."
                return jsonify({"success": False, "error":str(message)}), 200
            
        if username.data != current_user.username and not current_user.is_admin():
            user = User.query.filter_by(username=username.data).first()
            if user:
                # raise ValidationError(f'That username `{username.data}` is taken. Please choose a different one.') 
                message = f'That username `{username.data}` is taken. Please choose a different one.'
                return jsonify({"success": False, "error":str(message)}), 200

    def validate_email(self, email):
        if email.data != current_user.email and not current_user.is_admin():
            user = User.query.filter_by(email=email.data).first()
            if user:
                # raise ValidationError('That email is taken. Please choose a different one.')
                message = 'That email is taken. Please choose a different one.'
                return jsonify({"success": False, "error":str(message)}), 200
            
    def validate_phone(self, phone):
        if phone == None or phone == "":
            # return f"({phone}) appears to be missing/invalid"
            message =  f"({phone}) appears to be missing/invalid"
            return jsonify({"success": False, "error":str(message)}), 200
            
        if phone.data != current_user.phone and not current_user.is_admin():
            user = User.query.filter_by(phone=phone.data).first()
            if user:
                # raise ValidationError('Phone number belongs to a different account. Please use another one.')
                message = 'Phone number belongs to a different account. Please use another one.'
                return jsonify({"success": False, "error":str(message)}), 200

class ForgotForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Reset')
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            # raise ValidationError(f'Email({email.data}) Not Recognized')
            message = "Invalid email address"
            return jsonify({"success": False, "error":str(message)}), 200

class ResetForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')