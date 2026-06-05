# PlaceHub — College Placement System

A full-stack web application that automates campus recruitment: student registration, company job postings, admin management, eligibility checking, interview scheduling, analytics, and AI-powered skill-based recommendations.

## 🚀 Features

### For Students
- Profile management with resume upload
- Browse and apply for eligible job opportunities
- AI-powered job recommendations (TF-IDF skill matching)
- Track applications and interview schedules
- Real-time notifications

### For Companies
- Company profile and job posting management
- View and filter applicants
- Shortlist candidates and schedule interviews
- Application status management

### For Administrators
- Approve companies and verify student profiles
- Comprehensive analytics dashboard (Chart.js)
- Branch-wise placement reports with CSV export
- Bulk notification system
- Student and company management

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3 · Flask |
| Database | SQLite (SQLAlchemy ORM) |
| Auth | Flask-Login · Werkzeug |
| Frontend | Jinja2 · Vanilla CSS · Chart.js |
| ML | scikit-learn (TF-IDF + Cosine Similarity) |

## 📦 Setup

```bash
# 1. Navigate to project directory
cd college_placement_system

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python run.py
```

The app will start at **http://localhost:5000**

## 🔑 Default Admin Account

| Field | Value |
|---|---|
| Email | admin@college.edu |
| Password | admin123 |

> Change this password immediately after first login.

## 📁 Project Structure

```
college_placement_system/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Configuration
│   ├── extensions.py        # Flask extensions
│   ├── models.py            # Database models
│   ├── utils.py             # Helpers & ML
│   ├── auth/                # Authentication
│   ├── student/             # Student module
│   ├── company/             # Company module
│   ├── admin/               # Admin module
│   ├── notifications/       # Notifications
│   ├── static/              # CSS, JS, uploads
│   └── templates/           # HTML templates
├── run.py                   # Entry point
└── requirements.txt         # Dependencies
```

## 📊 User Workflows

1. **Student**: Register → Complete profile → Browse jobs → Apply → Track status
2. **Company**: Register → Admin approval → Post jobs → Review applicants → Schedule interviews
3. **Admin**: Approve companies → Verify students → View analytics → Generate reports
