import yaml
from flask import flash, redirect, render_template, request, session, url_for

import competenssator as cs
from models import Class, Enrollment, Group, SkillClaim, User, db
from utils import (get_level, login_required, make_qr_base64,
                   unique_user_code)


def register(app):

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user = User.query.get(session['user_id'])
        if user is None:
            session.clear()
            flash('Session expirée. Veuillez vous reconnecter.', 'warning')
            return redirect(url_for('login'))

        owned = Class.query.filter_by(teacher_id=user.id).order_by(Class.created_at.desc()).all()
        owned_info = []
        for cls in owned:
            pending = SkillClaim.query.filter_by(class_id=cls.id, status='claimed').count()
            unread = SkillClaim.query.filter_by(
                class_id=cls.id, status='claimed', teacher_notified=False).count()
            students = (Enrollment.query.join(Group)
                        .filter(Group.class_id == cls.id).count())
            owned_info.append({'cls': cls, 'pending': pending,
                               'unread': unread, 'students': students})

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

    # Legacy redirects
    @app.route('/teacher/dashboard')
    @login_required
    def teacher_dashboard():
        return redirect(url_for('dashboard'))

    @app.route('/student/dashboard')
    @login_required
    def student_dashboard():
        return redirect(url_for('dashboard'))

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

        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user is None:
                session.clear()
                return redirect(url_for('join_register', invite_code=invite_code))
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
                flash(f'Bienvenue dans le groupe « {group.name} » ! 🎉', 'success')
                return redirect(url_for('dashboard'))

        return render_template('join_register.html', group=group, invite_code=invite_code)
