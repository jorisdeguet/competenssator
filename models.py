import random
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Characters used for code generation — excludes confusables (0/O, 1/I/L)
CODE_CHARS = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


def generate_code(length: int = 8) -> str:
    return ''.join(random.choices(CODE_CHARS, k=length))


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    # Stored in plain text so teachers can always recover student codes
    code = db.Column(db.String(8), unique=True, index=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    # 'user' for all new accounts; legacy values 'teacher'/'student' still accepted
    role = db.Column(db.String(10), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    classes_taught = db.relationship('Class', back_populates='teacher',
                                     foreign_keys='Class.teacher_id', lazy=True)
    enrollments = db.relationship('Enrollment', back_populates='student',
                                  foreign_keys='Enrollment.student_id', lazy=True)
    claims = db.relationship('SkillClaim', back_populates='student',
                             foreign_keys='SkillClaim.student_id', lazy=True)


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    yaml_content = db.Column(db.Text, nullable=False)
    skill_order = db.Column(db.Text, nullable=True)   # JSON-encoded cached ordering
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship('User', back_populates='classes_taught',
                              foreign_keys=[teacher_id])
    groups = db.relationship('Group', back_populates='cls',
                             cascade='all, delete-orphan', lazy=True,
                             order_by='Group.name')
    claims = db.relationship('SkillClaim', back_populates='cls',
                             cascade='all, delete-orphan', lazy=True)
    cross_links_from = db.relationship(
        'CrossSkillLink', back_populates='source_class',
        foreign_keys='CrossSkillLink.source_class_id',
        cascade='all, delete-orphan', lazy=True)
    cross_links_to = db.relationship(
        'CrossSkillLink', back_populates='target_class',
        foreign_keys='CrossSkillLink.target_class_id',
        cascade='all, delete-orphan', lazy=True)


class Group(db.Model):
    """A sub-group within a class (e.g. 'Groupe A', 'Groupe B')."""
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    # Plain-text invite code — shared with students so they can self-register.
    # Stored unhashed so the teacher can always retrieve it.
    invite_code = db.Column(db.String(8), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cls = db.relationship('Class', back_populates='groups', foreign_keys=[class_id])
    enrollments = db.relationship('Enrollment', back_populates='group',
                                  cascade='all, delete-orphan', lazy=True)

    __table_args__ = (db.UniqueConstraint('class_id', 'name'),)


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('User', back_populates='enrollments',
                              foreign_keys=[student_id])
    group = db.relationship('Group', back_populates='enrollments',
                            foreign_keys=[group_id])

    __table_args__ = (db.UniqueConstraint('student_id', 'group_id'),)


class SkillClaim(db.Model):
    __tablename__ = 'skill_claims'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    skill_name = db.Column(db.String(200), nullable=False)
    # claimed → awaiting validation, validated → approved, rejected → denied
    status = db.Column(db.String(20), nullable=False, default='claimed')
    claimed_at = db.Column(db.DateTime, default=datetime.utcnow)
    validated_at = db.Column(db.DateTime, nullable=True)
    teacher_note = db.Column(db.Text, nullable=True)
    # False until the student sees the outcome of the validation
    student_notified = db.Column(db.Boolean, nullable=False, default=True)
    # False until the teacher sees the claim (set when student submits)
    teacher_notified = db.Column(db.Boolean, nullable=False, default=True)

    student = db.relationship('User', back_populates='claims',
                              foreign_keys=[student_id])
    cls = db.relationship('Class', back_populates='claims',
                          foreign_keys=[class_id])

    __table_args__ = (db.UniqueConstraint('student_id', 'class_id', 'skill_name'),)


class CrossSkillLink(db.Model):
    """A directed link from a skill in one class to a skill in another class.

    Semantics: completing source_skill in source_class is related to / a
    prerequisite for target_skill in target_class.
    """
    __tablename__ = 'cross_skill_links'
    id = db.Column(db.Integer, primary_key=True)
    source_class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    source_skill = db.Column(db.String(200), nullable=False)
    target_class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    target_skill = db.Column(db.String(200), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    source_class = db.relationship('Class', back_populates='cross_links_from',
                                   foreign_keys=[source_class_id])
    target_class = db.relationship('Class', back_populates='cross_links_to',
                                   foreign_keys=[target_class_id])
    creator = db.relationship('User', foreign_keys=[creator_id])

    __table_args__ = (db.UniqueConstraint('source_class_id', 'source_skill',
                                          'target_class_id', 'target_skill'),)
