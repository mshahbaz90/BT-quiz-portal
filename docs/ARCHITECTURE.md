# BreakThru Assessments — Architecture & System Design

## 1. Executive Overview
**BreakThru Assessments** (`assessments.breakthru.pk`) is an enterprise-grade assessment, testing, and certification platform designed for BreakThru's 300+ internal employees with future growth scalability. Built with Python, Django, modern responsive Vanilla CSS, and HTMX/JavaScript, it eliminates reliance on expensive proprietary tools like ClassMarker while providing tailored corporate workflow capabilities.

## 2. High-Level Architecture

```
[ Client Browsers: Desktop / Tablet / Mobile ]
                     │ HTTPS
                     ▼
         [ Reverse Proxy: Nginx / Caddy ]
                     │ Static / Media Cache & Rate Limiting
                     ▼
             [ WSGI: Gunicorn ]
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
[ Django Web App ]         [ Health & Audit ]
  ├── accounts (RBAC/Auth)   ├── AuditLog
  ├── assessments (Builder)  └── SystemMetrics
  ├── exam (Live Session)
  ├── grading (Auto & Queue)
  ├── certificates (PDF)
  └── analytics (Dashboards)
       │                           │
       ▼                           ▼
[ PostgreSQL / SQLite ]     [ Media Storage ]
  - ACID Transactions         - Uploads
  - Comprehensive Indexes     - Generated PDFs
```

## 3. Core Modules & Responsibilities

| App | Purpose | Key Models & Workflows |
|---|---|---|
| `core` | Global foundation | Audit logs, system settings, security middleware, health checks |
| `accounts` | Identity & RBAC | Custom `User`, `Department`, `Team`, bulk import CSV, password policy |
| `assessments` | Quiz/Exam Builder | `Assessment`, `Category`, `Question` (12 question types), `Option` |
| `exam` | Live exam runner | `AssessmentAttempt`, `AttemptResponse`, `AttemptQuestionSnapshot`, server timer, autosave |
| `grading` | Scoring engine | Auto-grading (objective), manual queue (subjective), grade adjustments & audit |
| `certificates` | Credentialing | `Certificate`, PDF generation, public verification endpoint (`/verify/<id>/`) |
| `analytics` | Reporting | Dashboards (Employee, Lead, Admin), CSV/Excel exports, performance stats |

## 4. Concurrency & Performance Strategy (300+ Active Users)
- **Zero-Latency In-Memory Snapshotting**: Questions and choices are snapshot at the time an assessment attempt is started. Changes to a bank question never invalidate an ongoing test.
- **Idempotent Atomic Autosave**: Real-time autosave saves each answer atomically with `select_for_update()` / transactional locks to prevent race conditions or duplicate submissions.
- **Server-Authoritative Clock**: The start timestamp and deadline are computed and stored on the server. The client countdown is purely a visual aid; attempts past deadlines are auto-finalized.
- **Database Optimization**: Targeted B-tree indexes on `(user_id, status)`, `(assessment_id, status)`, `(attempt_id, question_id)` ensure low query latencies under concurrent load.
- **Stateless Session Management**: Authentication tokens and sessions are optimized to minimize connection overhead.
