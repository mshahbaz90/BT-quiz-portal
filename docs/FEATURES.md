# BreakThru Assessments — Feature Inventory

## 1. Authentication & Role-Based Access Control (RBAC)
- [x] Custom BreakThru User model with Employee ID, Department, Team, Designation, Role.
- [x] 5 Standard Roles: Super Administrator, Assessment Administrator, Trainer / L&D, Team Lead / Supervisor, Employee / Assessment Taker.
- [x] Brute-force protection: Account lockout after 5 consecutive failed attempts.
- [x] Forced password change upon first login with temporary password.
- [x] Internal-only account creation (no public self-registration).
- [x] Bulk CSV/Excel employee import with validation and duplicate checking.

## 2. Assessment & Quiz Engine
- [x] 12 Question Types:
  1. Single-choice (Radio)
  2. Multiple-select (Checkboxes with partial credit / negative marking)
  3. True / False
  4. Yes / No
  5. Short Answer (Auto-graded with text normalization)
  6. Long Answer / Essay (Queued for manual grading)
  7. Fill in the Blank (Exact and tolerant text matching)
  8. Matching (Pairs matching)
  9. Ordering / Sequencing (Sequence order grading)
  10. Numeric (With configurable tolerance ±)
  11. Rich Formatted (Embedded images, markdown, tables)
  12. Questions with explanations and hints
- [x] Question Bank with Category, Difficulty, Tags, and search/filter.
- [x] Random question drawing from pool (e.g. pick 20 random from 50).
- [x] Assessment versions, time limits, pass marks, attempt limits, negative marking.
- [x] Preview mode for administrators before publishing.

## 3. Live Assessment Experience
- [x] Clean, distraction-free corporate interface.
- [x] Server-authoritative countdown timer with automatic submission on expiration.
- [x] Real-time autosave with visual feedback (Saved / Saving / Offline indicator).
- [x] Question flag / bookmark review drawer.
- [x] Idempotent final submission preventing double clicks and duplicate attempts.
- [x] Attempt snapshotting (modifying question bank does not corrupt in-flight attempts).

## 4. Grading & Results Engine
- [x] Instant automatic grading for objective questions.
- [x] Dedicated manual evaluation queue for essay/subjective questions.
- [x] Mark adjustment workflow with mandatory audit reason logging.
- [x] Configurable results release policy (Immediate, After Submission, On Date, or Manual).

## 5. Dashboards, Reports & Certificates
- [x] Employee Dashboard: Assigned tests, pending deadlines, score history, certificates.
- [x] Trainer & Team Lead Dashboard: Team completion rates, average scores, missed questions.
- [x] Super Admin Dashboard: Enterprise metrics, department breakdown, audit logs.
- [x] PDF Certificate generation with unique verification code and QR code.
- [x] Public verification endpoint (`/certificates/verify/<uuid>/`).
- [x] CSV and Excel reporting exports.
