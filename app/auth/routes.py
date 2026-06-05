from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import auth_bp
from app.auth.forms import RegisterForm, LoginForm
from app.models import User, Student, Company
from app.extensions import db
from app.utils import create_notification


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        if existing_user:
            if existing_user.username == form.username.data:
                flash('Username is already taken. Please choose another.', 'danger')
            else:
                flash('An account with that email already exists.', 'danger')
            return render_template('auth/register.html', form=form)

        # Create the user
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # Get user.id before creating profile

        # Create role-specific profile
        if form.role.data == 'student':
            student = Student(user_id=user.id, name=form.username.data)
            db.session.add(student)
        elif form.role.data == 'company':
            company = Company(user_id=user.id, company_name=form.username.data)
            db.session.add(company)

            # Notify admins about new company registration
            admin_users = User.query.filter_by(role='admin').all()
            for admin in admin_users:
                create_notification(
                    user_id=admin.id,
                    title='New Company Registration',
                    message=f'{form.username.data} has registered as a company and requires approval.',
                    notif_type='info',
                    link=url_for('admin.companies')
                )

        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', form=form)

        if not user.is_active_user:
            flash('Your account has been deactivated. Please contact the administrator.', 'warning')
            return render_template('auth/login.html', form=form)

        login_user(user, remember=form.remember_me.data)
        flash(f'Welcome back, {user.username}!', 'success')

        # Redirect to the page the user was trying to access, or role-appropriate dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'company':
            return redirect(url_for('company.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
