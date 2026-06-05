from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.company import company_bp
from app.company.forms import CompanyProfileForm, JobPostForm, InterviewForm
from app.extensions import db
from app.models import (
    Company, JobPosting, Application, Student, Interview
)
from app.utils import role_required, create_notification


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@company_bp.route('/dashboard')
@login_required
@role_required('company')
def dashboard():
    """Company dashboard with stats and recent applications."""
    company = Company.query.filter_by(user_id=current_user.id).first()

    if not company:
        flash('Please complete your company profile first.', 'warning')
        return redirect(url_for('company.profile'))

    # Aggregate stats
    total_jobs = company.job_postings.count()
    total_applicants = 0
    total_selected = 0
    job_ids = [j.id for j in company.job_postings.all()]

    if job_ids:
        total_applicants = Application.query.filter(
            Application.job_id.in_(job_ids)
        ).count()
        total_selected = Application.query.filter(
            Application.job_id.in_(job_ids),
            Application.status == 'selected'
        ).count()

    # Recent applications across all company jobs
    recent_applications = []
    if job_ids:
        recent_applications = (
            Application.query
            .filter(Application.job_id.in_(job_ids))
            .order_by(Application.applied_at.desc())
            .limit(10)
            .all()
        )

    return render_template(
        'company/dashboard.html',
        company=company,
        total_jobs=total_jobs,
        total_applicants=total_applicants,
        total_selected=total_selected,
        recent_applications=recent_applications
    )


# ---------------------------------------------------------------------------
# Company Profile
# ---------------------------------------------------------------------------
@company_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('company')
def profile():
    """View and update company profile."""
    company = Company.query.filter_by(user_id=current_user.id).first()

    if not company:
        company = Company(user_id=current_user.id)
        db.session.add(company)
        db.session.commit()

    form = CompanyProfileForm(obj=company)

    if form.validate_on_submit():
        form.populate_obj(company)
        db.session.commit()
        flash('Company profile updated successfully!', 'success')
        return redirect(url_for('company.profile'))

    return render_template('company/profile.html', form=form, company=company)


# ---------------------------------------------------------------------------
# Post a new Job
# ---------------------------------------------------------------------------
@company_bp.route('/post-job', methods=['GET', 'POST'])
@login_required
@role_required('company')
def post_job():
    """Create a new job posting."""
    company = Company.query.filter_by(user_id=current_user.id).first()

    if not company:
        flash('Please complete your company profile first.', 'warning')
        return redirect(url_for('company.profile'))

    if not company.is_approved:
        flash('Your company must be approved by an admin before posting jobs.', 'warning')
        return redirect(url_for('company.dashboard'))

    form = JobPostForm()

    if form.validate_on_submit():
        job = JobPosting(
            company_id=company.id,
            title=form.title.data,
            description=form.description.data,
            min_cgpa=form.min_cgpa.data or 0.0,
            required_skills=form.required_skills.data or '',
            eligible_branches=form.eligible_branches.data or '',
            location=form.location.data or '',
            salary_lpa=form.salary_lpa.data or 0.0,
            job_type=form.job_type.data,
            deadline=datetime.combine(form.deadline.data, datetime.min.time()).replace(
                tzinfo=timezone.utc
            ) if form.deadline.data else None,
            status='open'
        )
        db.session.add(job)
        db.session.commit()

        # Notify eligible students (limit 50)
        _notify_eligible_students(job, company)

        flash('Job posted successfully!', 'success')
        return redirect(url_for('company.jobs'))

    return render_template('company/post_job.html', form=form, company=company)


def _notify_eligible_students(job, company):
    """Send notifications to eligible students for a new job posting."""
    query = Student.query

    # Filter by CGPA
    if job.min_cgpa and job.min_cgpa > 0:
        query = query.filter(Student.cgpa >= job.min_cgpa)

    # Filter by branch
    branches = job.eligible_branches_list
    if branches:
        query = query.filter(Student.branch.in_(branches))

    eligible_students = query.limit(50).all()

    for student in eligible_students:
        create_notification(
            user_id=student.user_id,
            title='New Job Opportunity!',
            message=f'{company.company_name} has posted "{job.title}". Check if you are eligible!',
            notif_type='info',
            link=url_for('student.dashboard')
        )


# ---------------------------------------------------------------------------
# List Jobs
# ---------------------------------------------------------------------------
@company_bp.route('/jobs')
@login_required
@role_required('company')
def jobs():
    """List all jobs posted by this company."""
    company = Company.query.filter_by(user_id=current_user.id).first()

    if not company:
        flash('Please complete your company profile first.', 'warning')
        return redirect(url_for('company.profile'))

    all_jobs = (
        company.job_postings
        .order_by(JobPosting.created_at.desc())
        .all()
    )

    return render_template('company/jobs.html', jobs=all_jobs, company=company)


# ---------------------------------------------------------------------------
# Toggle Job Status (open <-> closed)
# ---------------------------------------------------------------------------
@company_bp.route('/toggle-job/<int:job_id>', methods=['POST'])
@login_required
@role_required('company')
def toggle_job(job_id):
    """Toggle a job posting between open and closed."""
    company = Company.query.filter_by(user_id=current_user.id).first()
    job = JobPosting.query.get_or_404(job_id)

    if job.company_id != company.id:
        abort(403)

    job.status = 'closed' if job.status == 'open' else 'open'
    db.session.commit()

    status_label = 'opened' if job.status == 'open' else 'closed'
    flash(f'Job "{job.title}" has been {status_label}.', 'success')
    return redirect(url_for('company.jobs'))


# ---------------------------------------------------------------------------
# View Applicants for a Job
# ---------------------------------------------------------------------------
@company_bp.route('/applicants/<int:job_id>')
@login_required
@role_required('company')
def applicants(job_id):
    """View all applicants for a specific job posting."""
    company = Company.query.filter_by(user_id=current_user.id).first()
    job = JobPosting.query.get_or_404(job_id)

    if job.company_id != company.id:
        abort(403)

    # Build query with optional filters
    query = Application.query.filter_by(job_id=job.id)

    status_filter = request.args.get('status', '')
    if status_filter:
        query = query.filter_by(status=status_filter)

    min_cgpa_filter = request.args.get('min_cgpa', '', type=str)
    if min_cgpa_filter:
        try:
            min_cgpa_val = float(min_cgpa_filter)
            query = query.join(Student).filter(Student.cgpa >= min_cgpa_val)
        except (ValueError, TypeError):
            pass

    applications = query.order_by(Application.applied_at.desc()).all()

    return render_template(
        'company/applicants.html',
        job=job,
        applications=applications,
        status_filter=status_filter,
        min_cgpa_filter=min_cgpa_filter,
        company=company
    )


# ---------------------------------------------------------------------------
# Update Application Status
# ---------------------------------------------------------------------------
@company_bp.route('/update-status/<int:app_id>', methods=['POST'])
@login_required
@role_required('company')
def update_status(app_id):
    """Update the status of a student's application."""
    company = Company.query.filter_by(user_id=current_user.id).first()
    application = Application.query.get_or_404(app_id)

    # Verify ownership
    job = JobPosting.query.get_or_404(application.job_id)
    if job.company_id != company.id:
        abort(403)

    new_status = request.form.get('new_status', '')
    valid_statuses = ['shortlisted', 'interviewed', 'selected', 'rejected']

    if new_status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('company.applicants', job_id=job.id))

    application.status = new_status
    db.session.commit()

    # Notify the student
    status_messages = {
        'shortlisted': f'You have been shortlisted for "{job.title}" at {company.company_name}!',
        'interviewed': f'Your interview status for "{job.title}" at {company.company_name} has been updated.',
        'selected': f'Congratulations! You have been selected for "{job.title}" at {company.company_name}!',
        'rejected': f'Your application for "{job.title}" at {company.company_name} was not successful.'
    }
    status_types = {
        'shortlisted': 'info',
        'interviewed': 'info',
        'selected': 'success',
        'rejected': 'danger'
    }

    create_notification(
        user_id=application.student.user_id,
        title=f'Application {new_status.capitalize()}',
        message=status_messages.get(new_status, ''),
        notif_type=status_types.get(new_status, 'info'),
        link=url_for('student.dashboard')
    )

    flash(f'Application status updated to "{new_status}".', 'success')
    return redirect(url_for('company.applicants', job_id=job.id))


# ---------------------------------------------------------------------------
# Schedule Interview
# ---------------------------------------------------------------------------
@company_bp.route('/schedule-interview/<int:app_id>', methods=['GET', 'POST'])
@login_required
@role_required('company')
def schedule_interview(app_id):
    """Schedule an interview for an application."""
    company = Company.query.filter_by(user_id=current_user.id).first()
    application = Application.query.get_or_404(app_id)

    # Verify ownership
    job = JobPosting.query.get_or_404(application.job_id)
    if job.company_id != company.id:
        abort(403)

    student = application.student
    form = InterviewForm()

    if form.validate_on_submit():
        scheduled_at = datetime.combine(
            form.scheduled_date.data,
            form.scheduled_time.data
        ).replace(tzinfo=timezone.utc)

        # Create or update interview record
        interview = application.interview
        if interview:
            interview.scheduled_at = scheduled_at
            interview.mode = form.mode.data
            interview.venue_or_link = form.venue_or_link.data
            interview.status = 'scheduled'
        else:
            interview = Interview(
                application_id=application.id,
                scheduled_at=scheduled_at,
                mode=form.mode.data,
                venue_or_link=form.venue_or_link.data,
                status='scheduled'
            )
            db.session.add(interview)

        # Update application status
        application.status = 'interviewed'
        db.session.commit()

        # Notify the student
        mode_label = 'Online' if form.mode.data == 'online' else 'Offline'
        create_notification(
            user_id=student.user_id,
            title='Interview Scheduled',
            message=(
                f'An interview for "{job.title}" at {company.company_name} has been scheduled '
                f'on {form.scheduled_date.data.strftime("%b %d, %Y")} at '
                f'{form.scheduled_time.data.strftime("%I:%M %p")} ({mode_label}). '
                f'Venue/Link: {form.venue_or_link.data}'
            ),
            notif_type='info',
            link=url_for('student.dashboard')
        )

        flash('Interview scheduled successfully!', 'success')
        return redirect(url_for('company.applicants', job_id=job.id))

    return render_template(
        'company/schedule_interview.html',
        form=form,
        application=application,
        student=student,
        job=job,
        company=company
    )
