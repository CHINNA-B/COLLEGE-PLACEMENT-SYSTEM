import csv
import io
import json
from datetime import datetime, timedelta

from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func, or_

from app.admin import admin_bp
from app.admin.forms import BulkNotificationForm
from app.extensions import db
from app.models import User, Student, Company, JobPosting, Application, Interview
from app.utils import role_required, get_placement_stats, create_notification


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    """Admin dashboard with stats, charts, pending approvals, and recent registrations."""
    stats = get_placement_stats()

    # Recent registrations (last 5 users)
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # Pending company approvals
    pending_companies = Company.query.filter_by(is_approved=False).all()
    pending_count = len(pending_companies)

    # Branch-wise placement stats for Chart.js
    branches = db.session.query(Student.branch, func.count(Student.id)).group_by(Student.branch).all()
    branch_stats = {}
    for branch, total in branches:
        if branch:
            placed = db.session.query(func.count(Application.id)).join(
                Student, Application.student_id == Student.id
            ).filter(
                Student.branch == branch,
                Application.status == 'selected'
            ).scalar() or 0
            branch_stats[branch] = {
                'total': total,
                'placed': placed,
                'rate': round((placed / total) * 100, 1) if total > 0 else 0
            }

    # Placement overview for pie chart
    total_students = Student.query.count()
    placed_students = db.session.query(func.count(func.distinct(Application.student_id))).filter(
        Application.status == 'selected'
    ).scalar() or 0
    unplaced_students = total_students - placed_students

    overview_stats = {
        'placed': placed_students,
        'unplaced': unplaced_students
    }

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_users=recent_users,
        pending_companies=pending_companies,
        pending_count=pending_count,
        branch_stats=branch_stats,
        overview_stats=overview_stats
    )


@admin_bp.route('/students')
@login_required
@role_required('admin')
def students():
    """List all students with search, filter, and pagination."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str).strip()
    branch_filter = request.args.get('branch', '', type=str).strip()
    verified_filter = request.args.get('verified', '', type=str).strip()
    placed_filter = request.args.get('placed', '', type=str).strip()

    query = Student.query.join(User, Student.user_id == User.id)

    # Search by name, branch, or email
    if search:
        query = query.filter(
            or_(
                Student.name.ilike(f'%{search}%'),
                Student.branch.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )

    # Filter by branch
    if branch_filter:
        query = query.filter(Student.branch == branch_filter)

    # Filter by verification status
    if verified_filter == 'yes':
        query = query.filter(Student.profile_verified == True)
    elif verified_filter == 'no':
        query = query.filter(Student.profile_verified == False)

    # Filter by placement status
    if placed_filter == 'yes':
        placed_ids = db.session.query(Application.student_id).filter(
            Application.status == 'selected'
        ).distinct().subquery()
        query = query.filter(Student.id.in_(placed_ids))
    elif placed_filter == 'no':
        placed_ids = db.session.query(Application.student_id).filter(
            Application.status == 'selected'
        ).distinct().subquery()
        query = query.filter(~Student.id.in_(placed_ids))

    # Get distinct branches for the filter dropdown
    all_branches = db.session.query(Student.branch).distinct().order_by(Student.branch).all()
    branches = [b[0] for b in all_branches if b[0]]

    pagination = query.order_by(Student.name).paginate(page=page, per_page=20, error_out=False)

    return render_template(
        'admin/manage_students.html',
        students=pagination.items,
        pagination=pagination,
        search=search,
        branch_filter=branch_filter,
        verified_filter=verified_filter,
        placed_filter=placed_filter,
        branches=branches
    )


@admin_bp.route('/verify-student/<int:student_id>', methods=['POST'])
@login_required
@role_required('admin')
def verify_student(student_id):
    """Toggle student profile verification status."""
    student = Student.query.get_or_404(student_id)
    student.profile_verified = not student.profile_verified
    db.session.commit()

    status_text = 'verified' if student.profile_verified else 'unverified'
    flash(f'Student "{student.name}" has been {status_text}.', 'success')

    create_notification(
        user_id=student.user_id,
        title='Profile Verification Update',
        message=f'Your profile has been {status_text} by the admin.',
        notif_type='success' if student.profile_verified else 'warning'
    )

    return redirect(url_for('admin.students'))


@admin_bp.route('/companies')
@login_required
@role_required('admin')
def companies():
    """List all companies with search, filter, and pagination."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str).strip()
    approved_filter = request.args.get('approved', '', type=str).strip()

    query = Company.query.join(User, Company.user_id == User.id)

    # Search by company name
    if search:
        query = query.filter(Company.company_name.ilike(f'%{search}%'))

    # Filter by approval status
    if approved_filter == 'yes':
        query = query.filter(Company.is_approved == True)
    elif approved_filter == 'no':
        query = query.filter(Company.is_approved == False)

    pagination = query.order_by(Company.company_name).paginate(page=page, per_page=20, error_out=False)

    return render_template(
        'admin/manage_companies.html',
        companies=pagination.items,
        pagination=pagination,
        search=search,
        approved_filter=approved_filter
    )


@admin_bp.route('/approve-company/<int:company_id>', methods=['POST'])
@login_required
@role_required('admin')
def approve_company(company_id):
    """Toggle company approval status."""
    company = Company.query.get_or_404(company_id)
    company.is_approved = not company.is_approved
    db.session.commit()

    status_text = 'approved' if company.is_approved else 'revoked'
    flash(f'Company "{company.company_name}" approval has been {status_text}.', 'success')

    create_notification(
        user_id=company.user_id,
        title='Company Approval Update',
        message=f'Your company has been {status_text} by the admin.',
        notif_type='success' if company.is_approved else 'warning'
    )

    return redirect(url_for('admin.companies'))


@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    """Delete a user account. Cannot delete yourself."""
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(request.referrer or url_for('admin.dashboard'))

    user = User.query.get_or_404(user_id)
    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f'User "{username}" has been deleted successfully.', 'success')
    return redirect(request.referrer or url_for('admin.dashboard'))


@admin_bp.route('/reports')
@login_required
@role_required('admin')
def reports():
    """Reports page with aggregate placement data."""
    stats = get_placement_stats()

    # Branch-wise placement breakdown
    branches = db.session.query(Student.branch, func.count(Student.id)).group_by(Student.branch).all()
    branch_data = []
    for branch, total in branches:
        if branch:
            placed = db.session.query(func.count(func.distinct(Application.student_id))).join(
                Student, Application.student_id == Student.id
            ).filter(
                Student.branch == branch,
                Application.status == 'selected'
            ).scalar() or 0
            branch_data.append({
                'branch': branch,
                'total': total,
                'placed': placed,
                'unplaced': total - placed,
                'rate': round((placed / total) * 100, 1) if total > 0 else 0
            })

    # Salary statistics
    salary_stats = db.session.query(
        func.min(JobPosting.salary_lpa),
        func.max(JobPosting.salary_lpa),
        func.avg(JobPosting.salary_lpa)
    ).join(
        Application, Application.job_id == JobPosting.id
    ).filter(Application.status == 'selected').first()

    salary_data = {
        'min': round(salary_stats[0], 2) if salary_stats[0] else 0,
        'max': round(salary_stats[1], 2) if salary_stats[1] else 0,
        'avg': round(salary_stats[2], 2) if salary_stats[2] else 0
    }

    return render_template(
        'admin/reports.html',
        stats=stats,
        branch_data=branch_data,
        salary_data=salary_data
    )


@admin_bp.route('/reports/download')
@login_required
@role_required('admin')
def download_report():
    """Download placement data as a CSV file."""
    # Fetch all selected applications with related data
    applications = db.session.query(
        Student.name,
        Student.branch,
        Student.cgpa,
        Company.company_name,
        JobPosting.title,
        Application.status,
        JobPosting.salary_lpa
    ).join(
        Application, Application.student_id == Student.id
    ).join(
        JobPosting, Application.job_id == JobPosting.id
    ).join(
        Company, JobPosting.company_id == Company.id
    ).order_by(Student.name).all()

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Branch', 'CGPA', 'Company', 'Job Title', 'Status', 'Salary (LPA)'])

    for app in applications:
        writer.writerow([
            app.name,
            app.branch,
            app.cgpa,
            app.company_name,
            app.title,
            app.status,
            app.salary_lpa
        ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=placement_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        }
    )


@admin_bp.route('/analytics')
@login_required
@role_required('admin')
def analytics():
    """Analytics page with interactive charts."""
    # Branch-wise placement rates
    branches = db.session.query(Student.branch, func.count(Student.id)).group_by(Student.branch).all()
    branch_rates = {}
    for branch, total in branches:
        if branch:
            placed = db.session.query(func.count(func.distinct(Application.student_id))).join(
                Student, Application.student_id == Student.id
            ).filter(
                Student.branch == branch,
                Application.status == 'selected'
            ).scalar() or 0
            branch_rates[branch] = round((placed / total) * 100, 1) if total > 0 else 0

    # Month-wise application trends (last 12 months)
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    monthly_apps = db.session.query(
        func.strftime('%Y-%m', Application.applied_at),
        func.count(Application.id)
    ).filter(
        Application.applied_at >= twelve_months_ago
    ).group_by(
        func.strftime('%Y-%m', Application.applied_at)
    ).order_by(
        func.strftime('%Y-%m', Application.applied_at)
    ).all()

    month_labels = [m[0] for m in monthly_apps]
    month_values = [m[1] for m in monthly_apps]

    # Top recruiting companies (by number of selections)
    top_companies = db.session.query(
        Company.company_name,
        func.count(Application.id)
    ).join(
        JobPosting, JobPosting.company_id == Company.id
    ).join(
        Application, Application.job_id == JobPosting.id
    ).filter(
        Application.status == 'selected'
    ).group_by(
        Company.company_name
    ).order_by(
        func.count(Application.id).desc()
    ).limit(10).all()

    recruiter_labels = [c[0] for c in top_companies]
    recruiter_values = [c[1] for c in top_companies]

    # Salary distribution
    salary_ranges = [
        ('0-5 LPA', 0, 5),
        ('5-10 LPA', 5, 10),
        ('10-15 LPA', 10, 15),
        ('15-20 LPA', 15, 20),
        ('20+ LPA', 20, 1000)
    ]
    salary_distribution = []
    for label, low, high in salary_ranges:
        count = db.session.query(func.count(Application.id)).join(
            JobPosting, Application.job_id == JobPosting.id
        ).filter(
            Application.status == 'selected',
            JobPosting.salary_lpa >= low,
            JobPosting.salary_lpa < high
        ).scalar() or 0
        salary_distribution.append({'label': label, 'count': count})

    salary_labels = [s['label'] for s in salary_distribution]
    salary_values = [s['count'] for s in salary_distribution]

    return render_template(
        'admin/analytics.html',
        branch_rates=branch_rates,
        month_labels=month_labels,
        month_values=month_values,
        recruiter_labels=recruiter_labels,
        recruiter_values=recruiter_values,
        salary_labels=salary_labels,
        salary_values=salary_values
    )


@admin_bp.route('/notify', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def notify():
    """Send bulk notifications to target audience."""
    form = BulkNotificationForm()

    if form.validate_on_submit():
        target = form.target.data
        title = form.title.data
        message = form.message.data
        notif_type = form.notif_type.data

        # Get target users
        if target == 'students':
            users = User.query.filter_by(role='student').all()
        elif target == 'companies':
            users = User.query.filter_by(role='company').all()
        else:
            users = User.query.filter(User.role.in_(['student', 'company'])).all()

        count = 0
        for user in users:
            create_notification(
                user_id=user.id,
                title=title,
                message=message,
                notif_type=notif_type
            )
            count += 1

        flash(f'Notification sent successfully to {count} user(s).', 'success')
        return redirect(url_for('admin.notify'))

    return render_template('admin/notify.html', form=form)
