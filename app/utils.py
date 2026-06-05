import os
import uuid
from functools import wraps
from flask import abort, current_app
from flask_login import current_user
from app.extensions import db
from app.models import Notification


def role_required(*roles):
    """Decorator to restrict access to specific user roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_eligibility(student, job):
    """Check if a student is eligible for a job posting."""
    # Check CGPA
    if student.cgpa < job.min_cgpa:
        return False, 'CGPA below minimum requirement'

    # Check branch
    eligible_branches = job.eligible_branches_list
    if eligible_branches and student.branch not in eligible_branches:
        return False, 'Branch not eligible for this position'

    # Check if already applied
    from app.models import Application
    existing = Application.query.filter_by(
        student_id=student.id, job_id=job.id
    ).first()
    if existing:
        return False, 'Already applied for this position'

    return True, 'Eligible'


def get_recommendations(student, jobs, top_n=5):
    """Get job recommendations based on skill similarity using TF-IDF."""
    if not student.skills or not jobs:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        job_skills = [job.required_skills or '' for job in jobs]
        all_texts = job_skills + [student.skills]

        vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w[\w+#.-]*\b')
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        student_vector = tfidf_matrix[-1]
        job_vectors = tfidf_matrix[:-1]

        scores = cosine_similarity(student_vector, job_vectors).flatten()
        ranked_indices = scores.argsort()[::-1][:top_n]

        return [(jobs[i], round(float(scores[i]) * 100, 1)) for i in ranked_indices if scores[i] > 0]
    except Exception:
        return []


def create_notification(user_id, title, message, notif_type='info', link=''):
    """Create an in-app notification for a user."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type,
        link=link
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'doc', 'docx'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def save_resume(file):
    """Save uploaded resume with UUID filename. Returns (saved_filename, original_filename)."""
    if file and allowed_file(file.filename):
        from werkzeug.utils import secure_filename
        original = secure_filename(file.filename)
        ext = original.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, unique_name))
        return unique_name, original
    return None, None


def get_placement_stats():
    """Generate aggregate placement statistics."""
    from app.models import Student, Company, JobPosting, Application

    total_students = Student.query.count()
    total_companies = Company.query.filter_by(is_approved=True).count()
    total_jobs = JobPosting.query.filter_by(status='open').count()
    total_applications = Application.query.count()
    total_selected = Application.query.filter_by(status='selected').count()
    total_rejected = Application.query.filter_by(status='rejected').count()

    placement_rate = round((total_selected / total_students * 100), 1) if total_students > 0 else 0

    # Branch-wise stats
    branches = db.session.query(Student.branch).distinct().all()
    branch_stats = []
    for (branch,) in branches:
        if not branch:
            continue
        branch_total = Student.query.filter_by(branch=branch).count()
        branch_placed = db.session.query(Application).join(Student).filter(
            Student.branch == branch,
            Application.status == 'selected'
        ).count()
        branch_stats.append({
            'branch': branch,
            'total': branch_total,
            'placed': branch_placed,
            'rate': round((branch_placed / branch_total * 100), 1) if branch_total > 0 else 0
        })

    # Salary stats
    from sqlalchemy import func
    salary_stats = db.session.query(
        func.min(JobPosting.salary_lpa),
        func.max(JobPosting.salary_lpa),
        func.avg(JobPosting.salary_lpa)
    ).filter(JobPosting.salary_lpa > 0).first()

    return {
        'total_students': total_students,
        'total_companies': total_companies,
        'total_jobs': total_jobs,
        'total_applications': total_applications,
        'total_selected': total_selected,
        'total_rejected': total_rejected,
        'placement_rate': placement_rate,
        'branch_stats': branch_stats,
        'min_salary': round(salary_stats[0] or 0, 2),
        'max_salary': round(salary_stats[1] or 0, 2),
        'avg_salary': round(salary_stats[2] or 0, 2)
    }
