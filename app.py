import os

from flask import session, redirect, request
from flask import Flask

from models import Class, SkillClaim, User, db
from i18n import get_t

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///competenssator.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# ---------------------------------------------------------------------------
# Template context processor: unread notification counts
# ---------------------------------------------------------------------------

@app.context_processor
def inject_notification_counts():
    lang = session.get('lang', 'fr')
    t = get_t(lang)
    user_id = session.get('user_id')
    if not user_id:
        return {
            'unread_count': 0,
            'student_unread_count': 0,
            'teacher_unread_count': 0,
            'student_notifications': [],
            'teacher_notifications': [],
            't': t,
            'lang': lang,
        }

    # Student: validated/rejected claims not yet seen (up to 10 for the drawer)
    student_notifs = (SkillClaim.query
                      .filter_by(student_id=user_id, student_notified=False)
                      .filter(SkillClaim.status.in_(['validated', 'rejected']))
                      .order_by(SkillClaim.validated_at.desc())
                      .limit(10).all())

    # Teacher: new claimed skills across all owned classes (up to 10)
    owned_class_ids = [c.id for c in Class.query.filter_by(teacher_id=user_id).all()]
    teacher_notifs = []
    if owned_class_ids:
        teacher_notifs = (SkillClaim.query
                          .filter(SkillClaim.class_id.in_(owned_class_ids),
                                  SkillClaim.status == 'claimed',
                                  SkillClaim.teacher_notified == False)  # noqa: E712
                          .order_by(SkillClaim.claimed_at.desc())
                          .limit(10).all())

    return {
        'unread_count': len(student_notifs) + len(teacher_notifs),
        'student_unread_count': len(student_notifs),
        'teacher_unread_count': len(teacher_notifs),
        'student_notifications': student_notifs,
        'teacher_notifications': teacher_notifs,
        't': t,
        'lang': lang,
    }


# ---------------------------------------------------------------------------
# Register route modules
# ---------------------------------------------------------------------------

from routes import auth, main, teacher, student  # noqa: E402

auth.register(app)
main.register(app)
teacher.register(app)
student.register(app)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
