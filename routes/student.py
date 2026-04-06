from datetime import datetime

import yaml
from flask import flash, redirect, render_template, request, session, url_for

import competenssator as cs
from models import CrossSkillLink, Enrollment, Group, SkillClaim, User, db
from utils import get_level, login_required, render_svg_for_class


def register(app):

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

        all_claims = SkillClaim.query.filter_by(
            student_id=user.id, class_id=class_id).all()

        new_notifications = [c for c in all_claims
                             if not c.student_notified
                             and c.status in ('validated', 'rejected')]

        existing_claims = {c.skill_name: c.status for c in all_claims}
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

        # All validated/rejected claims (for permanent history panel)
        history_claims = sorted(
            [c for c in all_claims if c.status in ('validated', 'rejected') and c.validated_at],
            key=lambda c: c.validated_at,
            reverse=True,
        )

        # Mark new notifications as read
        for c in new_notifications:
            c.student_notified = True
        if new_notifications:
            db.session.commit()

        cross_links_in = CrossSkillLink.query.filter_by(target_class_id=class_id).all()
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
                               cross_link_info=cross_link_info,
                               new_notifications=new_notifications,
                               history_claims=history_claims)

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
                existing.teacher_notified = False
                db.session.commit()
                flash(f'« {skill_name} » re-soumise. 🎯', 'success')
        else:
            claim = SkillClaim(student_id=user.id, class_id=class_id,
                               skill_name=skill_name, teacher_notified=False)
            db.session.add(claim)
            db.session.commit()
            flash(f'« {skill_name} » soumise ! En attente de validation. 🎯', 'success')

        return redirect(url_for('student_class_view', class_id=class_id))
