import io
import json
import os
import base64
from datetime import datetime
from functools import wraps

import qrcode
import yaml
from flask import (Flask, flash, redirect, render_template, request,
                   session, url_for)

import competenssator as cs
from models import (Class, CrossSkillLink, Enrollment, Group,
                    SkillClaim, User, db, generate_code)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///competenssator.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_qr_base64(text: str) -> str:
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def unique_user_code() -> str:
    """Generate an 8-char code guaranteed not to collide with any existing User.code."""
    while True:
        code = generate_code()
        if not User.query.filter_by(code=code).first():
            return code


def unique_invite_code() -> str:
    """Generate an 8-char invite code guaranteed not to collide with any Group."""
    while True:
        code = generate_code()
        if not Group.query.filter_by(invite_code=code).first():
            return code


def get_level(progress: int):
    if progress >= 66:
        return ('Or 🥇', 'is-warning')
    elif progress >= 33:
        return ('Argent 🥈', 'is-info')
    return ('Bronze 🥉', 'is-danger')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def render_svg_for_class(cls: Class, skill_states=None) -> str:
    try:
        data = yaml.safe_load(cls.yaml_content)
        if cls.skill_order:
            layout = json.loads(cls.skill_order)
            # backward-compat: old format was a plain list
            if isinstance(layout, list):
                layout = {'order': layout, 'rows': None, 'cols': None}
        else:
            layout = cs.compute_best_order(data)
            cls.skill_order = json.dumps(layout)
            db.session.commit()
        return cs.draw_with_states(data, layout, skill_states=skill_states)
    except Exception as e:
        return f'<p class="has-text-danger">Erreur de rendu : {e}</p>'


def _validate_class_form(name, yaml_content):
    if not name:
        return 'Le nom de la classe est requis.'
    if not yaml_content:
        return 'Le contenu YAML est requis.'
    try:
        data = yaml.safe_load(yaml_content)
        if not data or 'skills' not in data:
            raise ValueError('Le YAML doit contenir une clé "skills".')
    except Exception as e:
        return f'YAML invalide : {e}'
    return None


def _get_owned_class(class_id):
    """Return the class if the current user owns it, else abort 403."""
    cls = Class.query.get_or_404(class_id)
    if cls.teacher_id != session['user_id']:
        flash('Accès refusé.', 'danger')
        from flask import abort
        abort(403)
    return cls


def _get_owned_group(class_id, group_id):
    cls = _get_owned_class(class_id)
    group = Group.query.filter_by(id=group_id, class_id=class_id).first_or_404()
    return cls, group


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Veuillez saisir votre nom.', 'danger')
            return render_template('register.html')
        code = unique_user_code()
        user = User(code=code, display_name=name, role='user')
        db.session.add(user)
        db.session.commit()
        qr_data = make_qr_base64(code)
        return render_template('register.html', done=True, code=code,
                               qr_data=qr_data, name=name)
    return render_template('register.html')


# Legacy redirect
@app.route('/register/teacher')
def register_teacher():
    return redirect(url_for('register'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        raw = request.form.get('code', '').strip().upper()
        if len(raw) != 8:
            flash('Le code doit faire exactement 8 caractères.', 'danger')
            return render_template('login.html')
        user = User.query.filter_by(code=raw).first()
        if not user:
            flash('Code invalide. Vérifiez et réessayez.', 'danger')
            return render_template('login.html')
        session['user_id'] = user.id
        session['user_name'] = user.display_name
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Unified dashboard
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])

    # Classes this user owns (teacher side)
    owned = Class.query.filter_by(teacher_id=user.id).order_by(Class.created_at.desc()).all()
    owned_info = []
    for cls in owned:
        pending = SkillClaim.query.filter_by(class_id=cls.id, status='claimed').count()
        students = (Enrollment.query.join(Group)
                    .filter(Group.class_id == cls.id).count())
        owned_info.append({'cls': cls, 'pending': pending, 'students': students})

    # Classes this user is enrolled in (student side)
    seen = {}
    for enrollment in user.enrollments:
        cls = enrollment.group.cls
        if cls.id not in seen:
            try:
                data = yaml.safe_load(cls.yaml_content)
                total = len(cs.get_graph_from_data(data).nodes)
            except Exception:
                total = 0
            validated = SkillClaim.query.filter_by(
                student_id=user.id, class_id=cls.id, status='validated').count()
            progress = int(validated / total * 100) if total > 0 else 0
            seen[cls.id] = {
                'cls': cls,
                'group': enrollment.group.name,
                'total': total,
                'validated': validated,
                'progress': progress,
                'level': get_level(progress),
            }
    enrolled_info = list(seen.values())

    return render_template('dashboard.html', user=user,
                           owned_info=owned_info, enrolled_info=enrolled_info)


# Legacy redirects for old URLs
@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    return redirect(url_for('dashboard'))


@app.route('/student/dashboard')
@login_required
def student_dashboard():
    return redirect(url_for('dashboard'))


# ---------------------------------------------------------------------------
# Student self-registration via group invite code
# ---------------------------------------------------------------------------

@app.route('/join', methods=['GET', 'POST'])
def join():
    if request.method == 'POST':
        invite = request.form.get('invite_code', '').strip().upper()
        group = Group.query.filter_by(invite_code=invite).first()
        if not group:
            flash("Code d'invitation invalide. Vérifie auprès de ton enseignant.", 'danger')
            return render_template('join.html', prefill=invite)
        return redirect(url_for('join_register', invite_code=invite))
    prefill = request.args.get('code', '')
    return render_template('join.html', prefill=prefill)


@app.route('/join/<invite_code>', methods=['GET', 'POST'])
def join_register(invite_code):
    invite_code = invite_code.upper()
    group = Group.query.filter_by(invite_code=invite_code).first_or_404()

    # Already logged in → enroll immediately
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        existing = Enrollment.query.filter_by(
            student_id=user.id, group_id=group.id).first()
        if existing:
            flash(f'Tu es déjà inscrit(e) dans le groupe « {group.name} » !', 'info')
        else:
            db.session.add(Enrollment(student_id=user.id, group_id=group.id))
            db.session.commit()
            flash(f'Tu as rejoint le groupe « {group.name} » ! 🎉', 'success')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'new':
            name = request.form.get('name', '').strip()
            if not name:
                flash('Veuillez saisir votre prénom.', 'danger')
                return render_template('join_register.html', group=group,
                                       invite_code=invite_code)
            personal_code = unique_user_code()
            student = User(code=personal_code, display_name=name, role='user')
            db.session.add(student)
            db.session.flush()
            db.session.add(Enrollment(student_id=student.id, group_id=group.id))
            db.session.commit()
            qr_data = make_qr_base64(personal_code)
            return render_template('join_done.html', student=student,
                                   personal_code=personal_code, qr_data=qr_data,
                                   group=group)

        elif action == 'existing':
            code = request.form.get('personal_code', '').strip().upper()
            student = User.query.filter_by(code=code).first()
            if not student:
                flash('Code personnel invalide. Vérifie et réessaie.', 'danger')
                return render_template('join_register.html', group=group,
                                       invite_code=invite_code)
            existing = Enrollment.query.filter_by(
                student_id=student.id, group_id=group.id).first()
            if not existing:
                db.session.add(Enrollment(student_id=student.id, group_id=group.id))
                db.session.commit()
            session['user_id'] = student.id
            session['user_name'] = student.display_name
            flash(f'Bienvenue dans le groupe « {group.name} » ! ��', 'success')
            return redirect(url_for('dashboard'))

    return render_template('join_register.html', group=group, invite_code=invite_code)


# ---------------------------------------------------------------------------
# Class management (any logged-in user can create/manage their own classes)
# ---------------------------------------------------------------------------

@app.route('/teacher/classes/new', methods=['GET', 'POST'])
@login_required
def teacher_class_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        yaml_content = request.form.get('yaml_content', '').strip()
        error = _validate_class_form(name, yaml_content)
        if error:
            flash(error, 'danger')
            return render_template('teacher/class_form.html', action='new',
                                   name=name, yaml_content=yaml_content)
        cls = Class(name=name, teacher_id=session['user_id'], yaml_content=yaml_content)
        db.session.add(cls)
        db.session.commit()
        flash('Classe créée ! Choisissez une mise en page pour l\'arbre.', 'info')
        return redirect(url_for('teacher_class_layouts', class_id=cls.id))
    with open('arbre-5N6.yaml', 'r', encoding='utf-8') as f:
        example = f.read()
    return render_template('teacher/class_form.html', action='new', name='', yaml_content=example)


@app.route('/teacher/classes/<int:class_id>')
@login_required
def teacher_class_detail(class_id):
    cls = _get_owned_class(class_id)
    pending_claims = (SkillClaim.query
                      .filter_by(class_id=class_id, status='claimed')
                      .order_by(SkillClaim.claimed_at)
                      .all())
    svg = render_svg_for_class(cls)

    # Cross-skill links for this class
    links_from = CrossSkillLink.query.filter_by(source_class_id=class_id).all()
    links_to = CrossSkillLink.query.filter_by(target_class_id=class_id).all()

    # All classes (for the link creation form)
    all_classes = Class.query.filter(Class.id != class_id).order_by(Class.name).all()

    # Skills in this class (for the link creation form)
    try:
        data = yaml.safe_load(cls.yaml_content)
        own_skills = list(cs.get_graph_from_data(data).nodes)
    except Exception:
        own_skills = []

    return render_template('teacher/class_detail.html',
                           cls=cls, pending_claims=pending_claims, svg=svg,
                           links_from=links_from, links_to=links_to,
                           all_classes=all_classes, own_skills=own_skills)


@app.route('/teacher/classes/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
def teacher_class_edit(class_id):
    cls = _get_owned_class(class_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        yaml_content = request.form.get('yaml_content', '').strip()
        error = _validate_class_form(name, yaml_content)
        if error:
            flash(error, 'danger')
            return render_template('teacher/class_form.html', action='edit',
                                   cls=cls, name=name, yaml_content=yaml_content)
        cls.name = name
        cls.yaml_content = yaml_content
        cls.skill_order = None   # invalidate cached layout
        db.session.commit()
        flash('YAML mis à jour ! Choisissez une nouvelle mise en page.', 'info')
        return redirect(url_for('teacher_class_layouts', class_id=cls.id))
    return render_template('teacher/class_form.html', action='edit',
                           cls=cls, name=cls.name, yaml_content=cls.yaml_content)


@app.route('/teacher/classes/<int:class_id>/layouts')
@login_required
def teacher_class_layouts(class_id):
    cls = _get_owned_class(class_id)
    try:
        data = yaml.safe_load(cls.yaml_content)
        options = cs.compute_layout_options(data)
    except Exception as e:
        flash(f'Impossible de calculer les mises en page : {e}', 'danger')
        return redirect(url_for('teacher_class_detail', class_id=class_id))
    return render_template('teacher/layouts_preview.html', cls=cls, options=options)


@app.route('/teacher/classes/<int:class_id>/layout', methods=['POST'])
@login_required
def teacher_class_choose_layout(class_id):
    cls = _get_owned_class(class_id)
    order_json = request.form.get('order_json', '')
    rows = request.form.get('rows', type=int)
    cols = request.form.get('cols', type=int)
    try:
        layout = {'order': json.loads(order_json), 'rows': rows, 'cols': cols}
        cls.skill_order = json.dumps(layout)
        db.session.commit()
        flash('Mise en page enregistrée !', 'success')
    except Exception as e:
        flash(f'Erreur : {e}', 'danger')
    return redirect(url_for('teacher_class_detail', class_id=class_id))


# ---------------------------------------------------------------------------
# Cross-skill links
# ---------------------------------------------------------------------------

@app.route('/teacher/classes/<int:class_id>/links', methods=['POST'])
@login_required
def teacher_class_link_add(class_id):
    cls = _get_owned_class(class_id)
    source_skill = request.form.get('source_skill', '').strip()
    target_class_id = request.form.get('target_class_id', type=int)
    target_skill = request.form.get('target_skill', '').strip()

    if not source_skill or not target_class_id or not target_skill:
        flash('Tous les champs sont requis pour créer un lien.', 'danger')
        return redirect(url_for('teacher_class_detail', class_id=class_id))

    existing = CrossSkillLink.query.filter_by(
        source_class_id=class_id, source_skill=source_skill,
        target_class_id=target_class_id, target_skill=target_skill).first()
    if existing:
        flash('Ce lien existe déjà.', 'info')
    else:
        link = CrossSkillLink(
            source_class_id=class_id, source_skill=source_skill,
            target_class_id=target_class_id, target_skill=target_skill,
            creator_id=session['user_id'])
        db.session.add(link)
        db.session.commit()
        flash('Lien créé !', 'success')
    return redirect(url_for('teacher_class_detail', class_id=class_id))


@app.route('/teacher/classes/<int:class_id>/links/<int:link_id>/delete', methods=['POST'])
@login_required
def teacher_class_link_delete(class_id, link_id):
    _get_owned_class(class_id)
    link = CrossSkillLink.query.get_or_404(link_id)
    if link.source_class_id != class_id:
        from flask import abort
        abort(403)
    db.session.delete(link)
    db.session.commit()
    flash('Lien supprimé.', 'success')
    return redirect(url_for('teacher_class_detail', class_id=class_id))


@app.route('/classes/<int:class_id>/skills')
@login_required
def class_skills_json(class_id):
    """Return JSON list of skill names for a class (used in cross-link form)."""
    cls = Class.query.get_or_404(class_id)
    try:
        data = yaml.safe_load(cls.yaml_content)
        skills = list(cs.get_graph_from_data(data).nodes)
    except Exception:
        skills = []
    from flask import jsonify
    return jsonify(skills)


# ---------------------------------------------------------------------------
# Group management
# ---------------------------------------------------------------------------

@app.route('/teacher/classes/<int:class_id>/groups', methods=['POST'])
@login_required
def teacher_group_create(class_id):
    _get_owned_class(class_id)
    group_name = request.form.get('group_name', '').strip()
    if not group_name:
        flash('Le nom du groupe est requis.', 'danger')
        return redirect(url_for('teacher_class_detail', class_id=class_id))
    invite_code = unique_invite_code()
    group = Group(class_id=class_id, name=group_name, invite_code=invite_code)
    db.session.add(group)
    db.session.commit()
    flash(f'Groupe « {group_name} » créé !', 'success')
    return redirect(url_for('teacher_group_detail', class_id=class_id, group_id=group.id))


@app.route('/teacher/classes/<int:class_id>/groups/<int:group_id>')
@login_required
def teacher_group_detail(class_id, group_id):
    cls, group = _get_owned_group(class_id, group_id)
    enrollments = Enrollment.query.filter_by(group_id=group_id).all()
    students = [e.student for e in enrollments]
    total = len(students)
    student_ids = [s.id for s in students]

    skill_stats = {}
    svg = None
    if cls.yaml_content:
        try:
            data = yaml.safe_load(cls.yaml_content)
            G = cs.get_graph_from_data(data)
            for skill in G.nodes:
                if student_ids:
                    validated = SkillClaim.query.filter(
                        SkillClaim.student_id.in_(student_ids),
                        SkillClaim.class_id == cls.id,
                        SkillClaim.skill_name == skill,
                        SkillClaim.status == 'validated'
                    ).count()
                    claimed = SkillClaim.query.filter(
                        SkillClaim.student_id.in_(student_ids),
                        SkillClaim.class_id == cls.id,
                        SkillClaim.skill_name == skill,
                        SkillClaim.status == 'claimed'
                    ).count()
                else:
                    validated, claimed = 0, 0
                skill_stats[skill] = {'validated': validated, 'claimed': claimed}

            layout = json.loads(cls.skill_order) if cls.skill_order else None
            if layout and isinstance(layout, list):
                layout = {'order': layout, 'rows': None, 'cols': None}
            if layout:
                svg = cs.draw_with_group_stats(data, layout, skill_stats, total)
            else:
                svg = render_svg_for_class(cls)
        except Exception as e:
            svg = f'<p class="has-text-danger">Erreur SVG : {e}</p>'

    qr_data = make_qr_base64(group.invite_code)
    join_url = url_for('join_register', invite_code=group.invite_code, _external=True)
    return render_template('teacher/group_detail.html',
                           cls=cls, group=group, students=students,
                           qr_data=qr_data, join_url=join_url,
                           svg=svg, skill_stats=skill_stats, total=total)


@app.route('/teacher/classes/<int:class_id>/groups/<int:group_id>/students/bulk', methods=['POST'])
@login_required
def teacher_group_bulk_add(class_id, group_id):
    cls, group = _get_owned_group(class_id, group_id)
    raw = request.form.get('names', '')
    names = [n.strip() for n in raw.splitlines() if n.strip()]
    if not names:
        flash('Aucun nom fourni.', 'danger')
        return redirect(url_for('teacher_group_detail', class_id=class_id, group_id=group_id))
    created = []
    for name in names:
        code = unique_user_code()
        student = User(code=code, display_name=name, role='user')
        db.session.add(student)
        db.session.flush()
        db.session.add(Enrollment(student_id=student.id, group_id=group_id))
        created.append({'name': name, 'code': code})
    db.session.commit()
    return render_template('teacher/bulk_result.html', cls=cls, group=group, created=created)


@app.route('/teacher/classes/<int:class_id>/groups/<int:group_id>/students/<int:student_id>')
@login_required
def teacher_student_code(class_id, group_id, student_id):
    cls, group = _get_owned_group(class_id, group_id)
    student = User.query.get_or_404(student_id)
    qr_data = make_qr_base64(student.code)
    return render_template('teacher/student_code.html',
                           cls=cls, group=group, student=student, qr_data=qr_data)


@app.route('/teacher/validate', methods=['POST'])
@login_required
def teacher_validate():
    claim_id = request.form.get('claim_id', type=int)
    action = request.form.get('action')
    note = request.form.get('note', '').strip()
    claim = SkillClaim.query.get_or_404(claim_id)
    _get_owned_class(claim.class_id)
    claim.status = 'validated' if action == 'validate' else 'rejected'
    claim.validated_at = datetime.utcnow()
    claim.teacher_note = note or None
    db.session.commit()
    verb = 'validée' if action == 'validate' else 'refusée'
    flash(f'Compétence « {claim.skill_name} » {verb} !', 'success')
    return redirect(url_for('teacher_class_detail', class_id=claim.class_id))


# ---------------------------------------------------------------------------
# Skill tree view (any enrolled user)
# ---------------------------------------------------------------------------

@app.route('/student/classes/<int:class_id>')
@login_required
def student_class_view(class_id):
    user = User.query.get(session['user_id'])
    enrollment = (Enrollment.query
                  .join(Group)
                  .filter(Enrollment.student_id == user.id,
                          Group.class_id == class_id)
                  .first_or_404())
    cls = enrollment.group.cls

    existing_claims = {c.skill_name: c.status
                       for c in SkillClaim.query.filter_by(
                           student_id=user.id, class_id=class_id).all()}
    try:
        data = yaml.safe_load(cls.yaml_content)
        G = cs.get_graph_from_data(data)
        total = len(G.nodes)
        skill_states = {}
        for node in G.nodes:
            if node in existing_claims:
                skill_states[node] = existing_claims[node]
            else:
                preds = list(G.predecessors(node))
                all_ok = all(existing_claims.get(p) == 'validated' for p in preds)
                skill_states[node] = 'available' if all_ok else 'locked'
        svg = render_svg_for_class(cls, skill_states)
    except Exception as e:
        svg = f'<p class="has-text-danger">Erreur : {e}</p>'
        total = 0
        skill_states = {}

    validated_count = sum(1 for s in skill_states.values() if s == 'validated')
    progress = int(validated_count / total * 100) if total > 0 else 0

    # Cross-skill links: links pointing TO this class (what other classes feed into it)
    cross_links_in = CrossSkillLink.query.filter_by(target_class_id=class_id).all()
    # Check which source skills the current user has validated
    cross_link_info = []
    for link in cross_links_in:
        validated_in_source = SkillClaim.query.filter_by(
            student_id=user.id, class_id=link.source_class_id,
            skill_name=link.source_skill, status='validated').first() is not None
        cross_link_info.append({
            'link': link,
            'source_validated': validated_in_source,
        })

    return render_template('student/skill_tree.html',
                           user=user, cls=cls, svg=svg,
                           skill_states=skill_states,
                           progress=progress, level=get_level(progress),
                           total=total, validated_count=validated_count,
                           cross_link_info=cross_link_info)


@app.route('/student/claim', methods=['POST'])
@login_required
def student_claim():
    user = User.query.get(session['user_id'])
    class_id = request.form.get('class_id', type=int)
    skill_name = request.form.get('skill_name', '').strip()

    enrollment = (Enrollment.query
                  .join(Group)
                  .filter(Enrollment.student_id == user.id,
                          Group.class_id == class_id)
                  .first_or_404())
    cls = enrollment.group.cls

    try:
        data = yaml.safe_load(cls.yaml_content)
        G = cs.get_graph_from_data(data)
    except Exception:
        flash("Erreur de traitement de l'arbre.", 'danger')
        return redirect(url_for('student_class_view', class_id=class_id))

    if skill_name not in G.nodes:
        flash('Compétence inconnue.', 'danger')
        return redirect(url_for('student_class_view', class_id=class_id))

    existing_claims = {c.skill_name: c.status
                       for c in SkillClaim.query.filter_by(
                           student_id=user.id, class_id=class_id).all()}
    if not all(existing_claims.get(p) == 'validated' for p in G.predecessors(skill_name)):
        flash('Tu dois valider les compétences prérequises !', 'warning')
        return redirect(url_for('student_class_view', class_id=class_id))

    existing = SkillClaim.query.filter_by(
        student_id=user.id, class_id=class_id, skill_name=skill_name).first()
    if existing:
        if existing.status == 'validated':
            flash('Cette compétence est déjà validée !', 'info')
        elif existing.status == 'claimed':
            flash('Déjà en attente de validation.', 'info')
        elif existing.status == 'rejected':
            existing.status = 'claimed'
            existing.claimed_at = datetime.utcnow()
            existing.teacher_note = None
            db.session.commit()
            flash(f'« {skill_name} » re-soumise. 🎯', 'success')
    else:
        db.session.add(SkillClaim(student_id=user.id, class_id=class_id, skill_name=skill_name))
        db.session.commit()
        flash(f'« {skill_name} » soumise ! En attente de validation. 🎯', 'success')

    return redirect(url_for('student_class_view', class_id=class_id))


# ---------------------------------------------------------------------------
# Visual skill-tree builder
# ---------------------------------------------------------------------------

@app.route('/teacher/classes/builder')
@login_required
def teacher_class_builder():
    return render_template('teacher/class_builder.html')


# ---------------------------------------------------------------------------
# Legacy demo
# ---------------------------------------------------------------------------

@app.route('/demo')
def demo():
    data = cs.yaml_from_filepath('arbre-5N6.yaml')
    import yaml as pyyaml
    source = pyyaml.dump(data, allow_unicode=True)
    return render_template('test.html', yaml=source)


@app.route('/competenssator')
def compute_skill_tree():
    yaml_str = request.args.get('yaml')
    results = cs.file_to_svgs('arbre-5N6.yaml') if not yaml_str else cs.string_to_svgs(yaml_str)
    return results[0] if results else ''


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
