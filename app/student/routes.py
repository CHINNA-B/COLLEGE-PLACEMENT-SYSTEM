import os
from flask import render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import login_required, current_user

from app.student import student_bp
from app.student.forms import ProfileForm
from app.extensions import db
from app.models import Student, JobPosting, Application, Interview, Company
from app.utils import role_required, check_eligibility, get_recommendations, create_notification, save_resume


@student_bp.route('/dashboard')
@login_required
@role_required('student')
def dashboard():
    student = current_user.student_profile

    # Count applications by status
    total_applications = Application.query.filter_by(student_id=student.id).count() if student else 0
    shortlisted = Application.query.filter_by(student_id=student.id, status='shortlisted').count() if student else 0
    selected = Application.query.filter_by(student_id=student.id, status='selected').count() if student else 0

    # Upcoming interviews
    upcoming_interviews = []
    if student:
        upcoming_interviews = (
            db.session.query(Interview, Application, JobPosting, Company)
            .join(Application, Interview.application_id == Application.id)
            .join(JobPosting, Application.job_id == JobPosting.id)
            .join(Company, JobPosting.company_id == Company.id)
            .filter(Application.student_id == student.id)
            .filter(Interview.status == 'scheduled')
            .order_by(Interview.scheduled_at.asc())
            .all()
        )

    # Recommended jobs
    recommended_jobs = []
    if student:
        open_jobs = JobPosting.query.filter_by(status='open').all()
        recommended_jobs = get_recommendations(student, open_jobs, top_n=5)

    # Profile completion check
    profile_completed = student.profile_completed if student else False

    return render_template(
        'student/dashboard.html',
        student=student,
        total_applications=total_applications,
        shortlisted=shortlisted,
        selected=selected,
        upcoming_interviews=upcoming_interviews,
        recommended_jobs=recommended_jobs,
        profile_completed=profile_completed,
    )


@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('student')
def profile():
    student = current_user.student_profile

    # Create student profile if it doesn't exist yet
    if not student:
        student = Student(user_id=current_user.id)
        db.session.add(student)
        db.session.commit()

    form = ProfileForm(obj=student)

    if form.validate_on_submit():
        student.name = form.name.data
        student.branch = form.branch.data
        student.cgpa = form.cgpa.data
        student.skills = form.skills.data
        student.phone = form.phone.data
        student.address = form.address.data

        # Handle resume upload
        if form.resume.data:
            saved_filename, original_name = save_resume(form.resume.data)
            student.resume_filename = saved_filename
            student.resume_original_name = original_name

        # Mark profile as completed if required fields are filled
        if student.name and student.branch and student.cgpa is not None:
            student.profile_completed = True

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.profile'))

    return render_template(
        'student/profile.html',
        form=form,
        student=student,
    )


@student_bp.route('/jobs')
@login_required
@role_required('student')
def jobs():
    student = current_user.student_profile

    # Base query: open jobs with company info
    query = (
        db.session.query(JobPosting, Company)
        .join(Company, JobPosting.company_id == Company.id)
        .filter(JobPosting.status == 'open')
    )

    # Search filter
    search = request.args.get('search', '').strip()
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                JobPosting.title.ilike(search_pattern),
                Company.company_name.ilike(search_pattern),
                JobPosting.required_skills.ilike(search_pattern),
            )
        )

    # Branch filter
    branch_filter = request.args.get('branch', '').strip()
    if branch_filter:
        query = query.filter(JobPosting.eligible_branches.ilike(f'%{branch_filter}%'))

    # Minimum salary filter
    min_salary = request.args.get('min_salary', '').strip()
    if min_salary:
        try:
            query = query.filter(JobPosting.salary_lpa >= float(min_salary))
        except ValueError:
            pass

    # Job type filter
    job_type = request.args.get('job_type', '').strip()
    if job_type:
        query = query.filter(JobPosting.job_type == job_type)

    job_results = query.order_by(JobPosting.created_at.desc()).all()

    # Build job list with eligibility and application status
    jobs_data = []
    applied_job_ids = set()
    if student:
        applied_apps = Application.query.filter_by(student_id=student.id).all()
        applied_job_ids = {app.job_id for app in applied_apps}

    for job, company in job_results:
        eligible, reason = check_eligibility(student, job) if student else (False, 'Complete your profile first.')
        already_applied = job.id in applied_job_ids
        jobs_data.append({
            'job': job,
            'company': company,
            'eligible': eligible,
            'reason': reason,
            'already_applied': already_applied,
        })

    return render_template(
        'student/jobs.html',
        jobs_data=jobs_data,
        search=search,
        branch_filter=branch_filter,
        min_salary=min_salary,
        job_type=job_type,
    )


@student_bp.route('/apply/<int:job_id>', methods=['POST'])
@login_required
@role_required('student')
def apply(job_id):
    student = current_user.student_profile
    job = JobPosting.query.get_or_404(job_id)

    # Check profile completion
    if not student or not student.profile_completed:
        flash('Please complete your profile before applying.', 'warning')
        return redirect(url_for('student.profile'))

    # Check if already applied
    existing = Application.query.filter_by(student_id=student.id, job_id=job.id).first()
    if existing:
        flash('You have already applied for this job.', 'info')
        return redirect(url_for('student.jobs'))

    # Check eligibility
    eligible, reason = check_eligibility(student, job)
    if not eligible:
        flash(f'You are not eligible: {reason}', 'danger')
        return redirect(url_for('student.jobs'))

    # Create application
    application = Application(student_id=student.id, job_id=job.id, status='applied')
    db.session.add(application)
    db.session.commit()

    flash(f'Successfully applied for "{job.title}"!', 'success')

    # Notify the company about the new applicant
    company = Company.query.get(job.company_id)
    if company:
        create_notification(
            user_id=company.user_id,
            title='New Application Received',
            message=f'{student.name} has applied for the position "{job.title}".',
            notif_type='info',
            link=url_for('company.applicants', job_id=job.id),
        )

    return redirect(url_for('student.jobs'))


@student_bp.route('/applications')
@login_required
@role_required('student')
def applications():
    student = current_user.student_profile

    if not student:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('student.profile'))

    # Get all applications with job, company, and interview info
    apps_data = (
        db.session.query(Application, JobPosting, Company)
        .join(JobPosting, Application.job_id == JobPosting.id)
        .join(Company, JobPosting.company_id == Company.id)
        .filter(Application.student_id == student.id)
        .order_by(Application.applied_at.desc())
        .all()
    )

    # Attach interview info
    applications_list = []
    for application, job, company in apps_data:
        interview = Interview.query.filter_by(application_id=application.id).first()
        applications_list.append({
            'application': application,
            'job': job,
            'company': company,
            'interview': interview,
        })

    return render_template(
        'student/applications.html',
        applications=applications_list,
    )


@student_bp.route('/recommendations')
@login_required
@role_required('student')
def recommendations():
    student = current_user.student_profile

    if not student:
        flash('Please complete your profile to get recommendations.', 'warning')
        return redirect(url_for('student.profile'))

    open_jobs = JobPosting.query.filter_by(status='open').all()
    recommended = get_recommendations(student, open_jobs, top_n=10)

    # Check applied jobs
    applied_apps = Application.query.filter_by(student_id=student.id).all()
    applied_job_ids = {app.job_id for app in applied_apps}

    recommendations_data = []
    for job, score in recommended:
        company = Company.query.get(job.company_id)
        recommendations_data.append({
            'job': job,
            'company': company,
            'score': score,
            'already_applied': job.id in applied_job_ids,
        })

    return render_template(
        'student/recommendations.html',
        recommendations=recommendations_data,
    )


@student_bp.route('/resume/<filename>')
@login_required
@role_required('student')
def resume(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'static', 'uploads', 'resumes'))
    return send_from_directory(upload_folder, filename)
