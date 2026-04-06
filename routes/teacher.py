import json
from datetime import datetime

import yaml
from flask import (flash, jsonify, redirect, render_template,
                   request, session, url_for)

import competenssator as cs
from models import Class, CrossSkillLink, Enrollment, Group, SkillClaim, User, db
from utils import (get_level, get_owned_class, get_owned_group, login_required,
                   make_qr_base64, render_svg_for_class, unique_invite_code,
                   unique_user_code, validate_class_form)


def register(app):

    # -------------------------------------------------------------------------
    # Class management
    # -------------------------------------------------------------------------

    @app.route('/teacher/classes/new', methods=['GET', 'POST'])
    @login_required
    def teacher_class_new():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            yaml_content = request.form.get('yaml_content', '').strip()
            error = validate_class_form(name, yaml_content)
            if error:
                flash(error, 'danger')
                return render_template('teacher/class_form.html', action='new',
                                       name=name, yaml_content=yaml_content)
            cls = Class(name=name, teacher_id=session['user_id'], yaml_content=yaml_content)
            db.session.add(cls)
            db.session.commit()
            flash("Classe créée ! Choisissez une mise en page pour l'arbre.", 'info')
            return redirect(url_for('teacher_class_layouts', class_id=cls.id))
        with open('arbre-5N6.yaml', 'r', encoding='utf-8') as f:
            example = f.read()
        return render_template('teacher/class_form.html', action='new',
                               name='', yaml_content=example)

    @app.route('/teacher/classes/<int:class_id>')
    @login_required
    def teacher_class_detail(class_id):
        cls = get_owned_class(class_id)
        pending_claims = (SkillClaim.query
                          .filter_by(class_id=class_id, status='claimed')
                          .order_by(SkillClaim.claimed_at)
                          .all())

        # Mark all pending claims for this class as teacher-notified
        unread = [c for c in pending_claims if not c.teacher_notified]
        for c in unread:
            c.teacher_notified = True
        if unread:
            db.session.commit()

        svg = render_svg_for_class(cls)
        links_from = CrossSkillLink.query.filter_by(source_class_id=class_id).all()
        links_to = CrossSkillLink.query.filter_by(target_class_id=class_id).all()
        all_classes = Class.query.filter(Class.id != class_id).order_by(Class.name).all()

        try:
            data = yaml.safe_load(cls.yaml_content)
            own_skills = list(cs.get_graph_from_data(data).nodes)
            adjacency_warnings = cs.get_adjacency_warnings(data)
        except Exception:
            own_skills = []
            adjacency_warnings = []

        return render_template('teacher/class_detail.html',
                               cls=cls, pending_claims=pending_claims,
                               new_claims=unread, svg=svg,
                               links_from=links_from, links_to=links_to,
                               all_classes=all_classes, own_skills=own_skills,
                               adjacency_warnings=adjacency_warnings)

    @app.route('/teacher/classes/<int:class_id>/edit', methods=['GET', 'POST'])
    @login_required
    def teacher_class_edit(class_id):
        cls = get_owned_class(class_id)
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            yaml_content = request.form.get('yaml_content', '').strip()
            error = validate_class_form(name, yaml_content)
            if error:
                flash(error, 'danger')
                return render_template('teacher/class_form.html', action='edit',
                                       cls=cls, name=name, yaml_content=yaml_content)
            cls.name = name
            cls.yaml_content = yaml_content
            cls.skill_order = None
            db.session.commit()
            flash('YAML mis à jour ! Choisissez une nouvelle mise en page.', 'info')
            return redirect(url_for('teacher_class_layouts', class_id=cls.id))
        return render_template('teacher/class_form.html', action='edit',
                               cls=cls, name=cls.name, yaml_content=cls.yaml_content)

    @app.route('/teacher/classes/<int:class_id>/layouts')
    @login_required
    def teacher_class_layouts(class_id):
        cls = get_owned_class(class_id)
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
        cls = get_owned_class(class_id)
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

    # -------------------------------------------------------------------------
    # Cross-skill links
    # -------------------------------------------------------------------------

    @app.route('/teacher/classes/<int:class_id>/links', methods=['POST'])
    @login_required
    def teacher_class_link_add(class_id):
        get_owned_class(class_id)
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
        get_owned_class(class_id)
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
        cls = Class.query.get_or_404(class_id)
        try:
            data = yaml.safe_load(cls.yaml_content)
            skills = list(cs.get_graph_from_data(data).nodes)
        except Exception:
            skills = []
        return jsonify(skills)

    # -------------------------------------------------------------------------
    # Group management
    # -------------------------------------------------------------------------

    @app.route('/teacher/classes/<int:class_id>/groups', methods=['POST'])
    @login_required
    def teacher_group_create(class_id):
        get_owned_class(class_id)
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
        cls, group = get_owned_group(class_id, group_id)
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

        # Per-student stats: validated / claimed / total skills
        n_skills = len(cs.get_graph_from_data(yaml.safe_load(cls.yaml_content)).nodes) if cls.yaml_content else 0
        per_student_stats = {}
        for s in students:
            v = SkillClaim.query.filter_by(student_id=s.id, class_id=cls.id, status='validated').count()
            c = SkillClaim.query.filter_by(student_id=s.id, class_id=cls.id, status='claimed').count()
            per_student_stats[s.id] = {'validated': v, 'claimed': c, 'total': n_skills}

        qr_data = make_qr_base64(group.invite_code)
        join_url = url_for('join_register', invite_code=group.invite_code, _external=True)
        return render_template('teacher/group_detail.html',
                               cls=cls, group=group, students=students,
                               qr_data=qr_data, join_url=join_url,
                               svg=svg, skill_stats=skill_stats, total=total,
                               per_student_stats=per_student_stats)

    @app.route('/teacher/classes/<int:class_id>/groups/<int:group_id>/students/bulk',
               methods=['POST'])
    @login_required
    def teacher_group_bulk_add(class_id, group_id):
        cls, group = get_owned_group(class_id, group_id)
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
    def teacher_student_progress(class_id, group_id, student_id):
        cls, group = get_owned_group(class_id, group_id)
        student = User.query.get_or_404(student_id)
        qr_data = make_qr_base64(student.code)

        existing_claims = {c.skill_name: c for c in SkillClaim.query.filter_by(
            student_id=student_id, class_id=class_id).all()}

        try:
            data = yaml.safe_load(cls.yaml_content)
            G = cs.get_graph_from_data(data)
            total = len(G.nodes)
            skill_states = {}
            for node in G.nodes:
                if node in existing_claims:
                    skill_states[node] = existing_claims[node].status
                else:
                    preds = list(G.predecessors(node))
                    all_ok = all(
                        existing_claims.get(p) and existing_claims[p].status == 'validated'
                        for p in preds)
                    skill_states[node] = 'available' if all_ok else 'locked'
            svg = render_svg_for_class(cls, skill_states)
        except Exception as e:
            svg = f'<p class="has-text-danger">Erreur : {e}</p>'
            total = 0
            skill_states = {}

        validated_count = sum(1 for s in skill_states.values() if s == 'validated')
        claimed_count = sum(1 for s in skill_states.values() if s == 'claimed')
        progress = int(validated_count / total * 100) if total > 0 else 0
        claim_list = sorted(existing_claims.values(), key=lambda c: c.claimed_at, reverse=True)

        # Skills the teacher can validate directly (no student claim yet)
        unclaimed_skills = [
            skill for skill, state in skill_states.items()
            if state in ('available', 'locked')
        ]
        unclaimed_skills.sort()

        return render_template('teacher/student_progress.html',
                               cls=cls, group=group, student=student,
                               qr_data=qr_data, svg=svg,
                               skill_states=skill_states,
                               progress=progress, level=get_level(progress),
                               total=total, validated_count=validated_count,
                               claimed_count=claimed_count,
                               claim_list=claim_list,
                               unclaimed_skills=unclaimed_skills)

    @app.route('/teacher/classes/<int:class_id>/groups/<int:group_id>/students/<int:student_id>/code')
    @login_required
    def teacher_student_code(class_id, group_id, student_id):
        return redirect(url_for('teacher_student_progress',
                                class_id=class_id, group_id=group_id, student_id=student_id))

    # -------------------------------------------------------------------------
    # Skill validation
    # -------------------------------------------------------------------------

    @app.route('/teacher/validate', methods=['POST'])
    @login_required
    def teacher_validate():
        claim_id = request.form.get('claim_id', type=int)
        action = request.form.get('action')
        note = request.form.get('note', '').strip()
        next_url = request.form.get('next', '')
        claim = SkillClaim.query.get_or_404(claim_id)
        get_owned_class(claim.class_id)
        claim.status = 'validated' if action == 'validate' else 'rejected'
        claim.validated_at = datetime.utcnow()
        claim.teacher_note = note or None
        claim.student_notified = False
        claim.teacher_notified = True
        db.session.commit()
        verb = 'validée' if action == 'validate' else 'refusée'
        flash(f'Compétence « {claim.skill_name} » {verb} !', 'success')
        if next_url:
            return redirect(next_url)
        return redirect(url_for('teacher_class_detail', class_id=claim.class_id))

    @app.route('/teacher/direct-validate', methods=['POST'])
    @login_required
    def teacher_direct_validate():
        class_id = request.form.get('class_id', type=int)
        student_id = request.form.get('student_id', type=int)
        skill_name = request.form.get('skill_name', '').strip()
        note = request.form.get('note', '').strip()
        next_url = request.form.get('next', '')
        cls = get_owned_class(class_id)

        # Verify skill exists in the class tree
        try:
            data = yaml.safe_load(cls.yaml_content)
            G = cs.get_graph_from_data(data)
            if skill_name not in G.nodes:
                flash('Compétence introuvable.', 'danger')
                return redirect(next_url or url_for('teacher_class_detail', class_id=class_id))
        except Exception:
            flash("Erreur de traitement de l'arbre.", 'danger')
            return redirect(next_url or url_for('teacher_class_detail', class_id=class_id))

        now = datetime.utcnow()
        claim = SkillClaim.query.filter_by(
            student_id=student_id, class_id=class_id, skill_name=skill_name).first()
        if claim:
            claim.status = 'validated'
            claim.validated_at = now
            claim.teacher_note = note or None
            claim.student_notified = False
            claim.teacher_notified = True
        else:
            claim = SkillClaim(
                student_id=student_id,
                class_id=class_id,
                skill_name=skill_name,
                status='validated',
                claimed_at=now,
                validated_at=now,
                teacher_note=note or None,
                student_notified=False,
                teacher_notified=True,
            )
            db.session.add(claim)
        db.session.commit()
        flash(f'« {skill_name} » validée directement !', 'success')
        return redirect(next_url or url_for('teacher_class_detail', class_id=class_id))



    @app.route('/teacher/classes/builder')
    @login_required
    def teacher_class_builder():
        return render_template('teacher/class_builder.html')

    @app.route('/demo')
    def demo():
        import yaml as pyyaml
        data = cs.yaml_from_filepath('arbre-5N6.yaml')
        source = pyyaml.dump(data, allow_unicode=True)
        return render_template('test.html', yaml=source)

    @app.route('/competenssator')
    def compute_skill_tree():
        yaml_str = request.args.get('yaml')
        results = cs.file_to_svgs('arbre-5N6.yaml') if not yaml_str else cs.string_to_svgs(yaml_str)
        return results[0] if results else ''
