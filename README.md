# BreakThru Assessments
> *Learn. Prove It. BreakThru.*

An enterprise assessment, quiz, and certification platform designed specifically for **BreakThru (breakthru.pk)**, providing an in-house alternative to ClassMarker with high concurrency (300+ employees), 12 question types, server-authoritative timers, real-time autosave, automatic and manual grading queues, analytics dashboards, and verifiable PDF certificates.

---

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.12+ (or Python 3.14)
- Git

### 2. Setup
```bash
# Clone the repository
git clone <repo-url>
cd quiz-portal

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed initial test data and roles
python manage.py seed_breakthru_data

# Start the development server
python manage.py runserver
```

The portal will be accessible at: `http://localhost:8000`

### Default Demo Credentials
- **Super Administrator**: `admin` / `BreakThru2026!`
- **Trainer**: `trainer.ali` / `BreakThru2026!`
- **Employee**: `emp.zara` / `BreakThru2026!`

---

## Documentation Index
- [Architecture & Design](docs/ARCHITECTURE.md)
- [Feature Inventory](docs/FEATURES.md)
- [Security Controls](docs/SECURITY.md)
- [Production Deployment](docs/DEPLOYMENT.md)
- [Backup & Disaster Recovery](docs/BACKUP_RESTORE.md)
- [Testing & Concurrency](docs/TESTING.md)
