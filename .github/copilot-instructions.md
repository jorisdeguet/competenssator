# Copilot Instructions

## Running the app

```bash
python3 app.py          # dev server (debug=True)
flask run               # alternative (set FLASK_APP=app.py)
gunicorn app:app        # production
```

The SQLite database (`instance/competenssator.db`) is created automatically on first run via `db.create_all()` at module load time. No migration tool is used — schema changes require manual DB deletion or in-place `ALTER TABLE`.

## Seeding the database

```bash
rm -f instance/competenssator.db
python3 seed.py
```

This drops and recreates the database with 3 teacher accounts, 3 classes (3N5 Kotlin, 4N6 Flutter, 5N6 Flutter multiplateforme), and 50 students with various progressions. It also seeds sample cross-skill links between classes. Prints all login codes on completion.

## Architecture

**competenssator** is a French-language Flask web app for teachers to manage skill trees for their classes. Students self-register and claim skills; teachers validate claims.

### Key files

| File | Role |
|---|---|
| `app.py` | All Flask routes and view helpers |
| `models.py` | SQLAlchemy models + `generate_code()` |
| `competenssator.py` | SVG skill-tree rendering + layout optimisation |
| `seed.py` | DB seed script (50 students, 3 classes, cross-skill links) |
| `Dockerfile` | Production container (gunicorn, python:3.11-slim) |
| `*.yaml` | Example skill-tree definitions |

### Data model

- **User** — unified account (`role='user'` for all new accounts; legacy `'teacher'`/`'student'` values still accepted but not used for routing); authenticated by an 8-char code (plain text, no hashing) so teachers can always recover student codes
- **Class** — belongs to a user (teacher side); stores the skill tree as raw YAML (`yaml_content`) and the cached hex-grid layout as JSON (`skill_order`)
- **Group** — sub-group within a class with a plain-text `invite_code` (8-char); students join via `/join/<invite_code>`
- **Enrollment** — student ↔ group many-to-many
- **SkillClaim** — a student's claim on one skill; status lifecycle: `claimed → validated` or `claimed → rejected`
- **CrossSkillLink** — directed link from a skill in one class to a skill in another class (semantics: source skill is related to / a prerequisite for target skill)

### Auth

Login is code-only (`User.code`, 8 chars). Flask `session` stores `user_id`, `user_name`. One decorator guards all protected routes: `@login_required`. There is no teacher/student role distinction for routing — any user can create classes (teacher side) and be enrolled in classes (student side).

### Routing

- `/` — landing page (redirects to `/dashboard` if logged in)
- `/dashboard` — unified dashboard showing owned classes + enrolled classes
- `/register` — create account (just a name, returns a code + QR)
- `/login` — code-only login
- `/join` and `/join/<invite_code>` — student self-registration via group invite code
- `/teacher/dashboard` and `/student/dashboard` — legacy redirects to `/dashboard`
- `/teacher/classes/...` — class management (create, edit, groups, validation, cross-links)
- `/student/classes/<id>` — skill tree view for enrolled students
- `/student/claim` — POST to claim a skill

### Skill-tree YAML format

```yaml
config:
  blackAndWhite: false
  withTickBox: false

skills:
  - name: "Skill name"
    description: "..."

deps:
  - from: "Skill A"
    to: "Skill B"
```

Skills and deps define a directed graph (via `networkx`). Sections are inferred from graph connectivity and colour-coded in `SECTION_COLORS`.

### Layout & SVG pipeline

1. YAML → `networkx` directed graph (`get_graph_from_data`)
2. Graph nodes placed on a `HexGrid` using pairwise-swap hill-climb (`hill_climb` + `evaluation`)  
   - Score: `+40` per adjacent connected pair, `-12d²` per distant pair, hub-centrality pull, sources-near-top
3. Three grid shape variants (compact / wide / tall) offered via `compute_layout_options()`; teacher picks one, stored as `Class.skill_order` JSON: `{"order": [...], "rows": int, "cols": int}`
4. `draw_with_states(data, layout, skill_states)` — renders student view (per-skill claim state colours)
5. `draw_with_group_stats(data, layout, skill_stats, total_students)` — renders teacher group view with `✓n/total` annotations

Skill state stroke colours are defined in `STATE_STROKES`; section fill colours in `SECTION_COLORS`.

### Progress levels (student)

`get_level(progress_pct)` returns a Bulma CSS class + label:
- ≥ 66 % → Or 🥇 (`is-warning`)
- ≥ 33 % → Argent 🥈 (`is-info`)
- < 33 % → Bronze 🥉 (`is-danger`)

## Key conventions

- **All UI text is in French** — flash messages, labels, error strings.
- **Codes never hashed** — `User.code` and `Group.invite_code` are stored plain text by design.
- **`skill_order` backward compat** — old format was a plain list; `render_svg_for_class` normalises it to `{'order': [...], 'rows': None, 'cols': None}`. Don't break this path.
- **`___` is a grid placeholder** — skill names equal to `"___"` are empty hex cells; `draw_hexagon` skips rendering them.
- **`results/` folder** — `draw_skill_tree` writes SVG files there even when `generate_pdf=False`; the folder is created on demand by `_ensure_results_folder()`. It is git-ignored.
- **B&W Bulma theme** — black navbar (`#111`), white body, minimal color; use `is-dark` buttons (not `is-link`). Skill state colors are the only accent colors.
- **Templates** — split into `templates/teacher/` and `templates/student/` subdirectories; both extend `base.html`. Legacy `teacher/dashboard.html` and `student/dashboard.html` just redirect to `/dashboard`.
- **Registration** — `POST /register` accepts only `name` field; returns a unique 8-char code + QR. No role selection.
