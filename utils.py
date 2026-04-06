"""Shared helpers used across route modules."""
import base64
import io
import json
from functools import wraps

import qrcode
import yaml
from flask import abort, flash, redirect, session, url_for

import competenssator as cs
from models import Class, Group, SkillClaim, User, db, generate_code


def make_qr_base64(text: str) -> str:
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def unique_user_code() -> str:
    while True:
        code = generate_code()
        if not User.query.filter_by(code=code).first():
            return code


def unique_invite_code() -> str:
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
            if isinstance(layout, list):
                layout = {'order': layout, 'rows': None, 'cols': None}
        else:
            layout = cs.compute_best_order(data)
            cls.skill_order = json.dumps(layout)
            db.session.commit()
        return cs.draw_with_states(data, layout, skill_states=skill_states)
    except Exception as e:
        return f'<p class="has-text-danger">Erreur de rendu : {e}</p>'


def validate_class_form(name, yaml_content):
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


def get_owned_class(class_id):
    """Return the class if the current user owns it, else abort 403."""
    cls = Class.query.get_or_404(class_id)
    if cls.teacher_id != session['user_id']:
        flash('Accès refusé.', 'danger')
        abort(403)
    return cls


def get_owned_group(class_id, group_id):
    cls = get_owned_class(class_id)
    group = Group.query.filter_by(id=group_id, class_id=class_id).first_or_404()
    return cls, group
