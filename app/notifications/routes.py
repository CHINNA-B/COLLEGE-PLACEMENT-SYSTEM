from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.notifications import notifications_bp
from app.models import Notification
from app.extensions import db, csrf


@notifications_bp.route('/')
@login_required
def list_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).all()
    return render_template('notifications/list.html', notifications=notifications)


@notifications_bp.route('/mark-read/<int:id>', methods=['POST'])
@login_required
def mark_read(id):
    notification = Notification.query.get_or_404(id)

    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('notifications.list_notifications'))

    notification.is_read = True
    db.session.commit()
    flash('Notification marked as read.', 'success')

    return redirect(request.referrer or url_for('notifications.list_notifications'))


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False) \
        .update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications.list_notifications'))


@notifications_bp.route('/api/unread-count')
@csrf.exempt
@login_required
def unread_count():
    count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    return jsonify({'count': count})
