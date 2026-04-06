from flask import flash, redirect, render_template, request, session, url_for

from models import Enrollment, Group, User, db
from utils import make_qr_base64, unique_user_code


def register(app):

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

    @app.route('/set-lang/<lang>')
    def set_lang(lang):
        if lang in ('fr', 'en'):
            session['lang'] = lang
        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))
