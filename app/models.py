from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """Base user model with role-based access."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student, company, admin
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    company_profile = db.relationship('Company', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Student(db.Model):
    """Student profile linked to a User."""
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False, default='')
    branch = db.Column(db.String(100), default='')
    cgpa = db.Column(db.Float, default=0.0)
    skills = db.Column(db.Text, default='')  # Comma-separated
    resume_filename = db.Column(db.String(255), default='')
    resume_original_name = db.Column(db.String(255), default='')
    phone = db.Column(db.String(20), default='')
    address = db.Column(db.Text, default='')
    profile_verified = db.Column(db.Boolean, default=False)
    profile_completed = db.Column(db.Boolean, default=False)

    # Relationships
    applications = db.relationship('Application', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def skills_list(self):
        """Return skills as a cleaned list."""
        if not self.skills:
            return []
        return [s.strip().lower() for s in self.skills.split(',') if s.strip()]

    @property
    def placement_status(self):
        """Check if student is placed."""
        selected = self.applications.filter_by(status='selected').first()
        return 'Placed' if selected else 'Not Placed'

    def __repr__(self):
        return f'<Student {self.name} ({self.branch})>'


class Company(db.Model):
    """Company profile linked to a User."""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    company_name = db.Column(db.String(200), nullable=False, default='')
    industry = db.Column(db.String(100), default='')
    website = db.Column(db.String(200), default='')
    description = db.Column(db.Text, default='')
    contact_email = db.Column(db.String(120), default='')
    contact_phone = db.Column(db.String(20), default='')
    logo_filename = db.Column(db.String(255), default='')
    is_approved = db.Column(db.Boolean, default=False)

    # Relationships
    job_postings = db.relationship('JobPosting', backref='company', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Company {self.company_name}>'


class JobPosting(db.Model):
    """Job posting created by a company."""
    __tablename__ = 'job_postings'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    min_cgpa = db.Column(db.Float, default=0.0)
    required_skills = db.Column(db.Text, default='')  # Comma-separated
    eligible_branches = db.Column(db.Text, default='')  # Comma-separated
    location = db.Column(db.String(200), default='')
    salary_lpa = db.Column(db.Float, default=0.0)
    job_type = db.Column(db.String(50), default='Full-time')  # Full-time, Internship, Part-time
    deadline = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='open')  # open, closed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    applications = db.relationship('Application', backref='job', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def eligible_branches_list(self):
        if not self.eligible_branches:
            return []
        return [b.strip() for b in self.eligible_branches.split(',') if b.strip()]

    @property
    def required_skills_list(self):
        if not self.required_skills:
            return []
        return [s.strip().lower() for s in self.required_skills.split(',') if s.strip()]

    @property
    def applicant_count(self):
        return self.applications.count()

    def __repr__(self):
        return f'<JobPosting {self.title}>'


class Application(db.Model):
    """Student application to a job posting."""
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_postings.id'), nullable=False)
    applied_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(30), default='applied')
    # Status flow: applied -> shortlisted -> interviewed -> selected / rejected

    # Relationships
    interview = db.relationship('Interview', backref='application', uselist=False, cascade='all, delete-orphan')

    # Unique constraint: one application per student per job
    __table_args__ = (db.UniqueConstraint('student_id', 'job_id', name='_student_job_uc'),)

    @property
    def status_color(self):
        colors = {
            'applied': 'info',
            'shortlisted': 'warning',
            'interviewed': 'primary',
            'selected': 'success',
            'rejected': 'danger'
        }
        return colors.get(self.status, 'info')

    def __repr__(self):
        return f'<Application Student:{self.student_id} Job:{self.job_id} Status:{self.status}>'


class Interview(db.Model):
    """Interview scheduled for an application."""
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False, unique=True)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    mode = db.Column(db.String(20), default='online')  # online, offline
    venue_or_link = db.Column(db.String(500), default='')
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    feedback = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Interview App:{self.application_id} on {self.scheduled_at}>'


class Notification(db.Model):
    """In-app notification for users."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='info')  # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(500), default='')  # Optional link to related page
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Notification {self.title} for User:{self.user_id}>'
