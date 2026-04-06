"""
empty_db.py — wipes all data from the database without dropping the schema.

Usage:
    python3 empty_db.py          # asks for confirmation
    python3 empty_db.py --yes    # skips confirmation
"""

import sys
from app import app
from models import CrossSkillLink, Enrollment, Group, SkillClaim, Class, User, db


def main():
    confirm = '--yes' in sys.argv
    if not confirm:
        answer = input('This will delete ALL users, classes, and claims. Continue? [y/N] ')
        if answer.strip().lower() not in ('y', 'yes'):
            print('Cancelled.')
            return

    with app.app_context():
        CrossSkillLink.query.delete()
        SkillClaim.query.delete()
        Enrollment.query.delete()
        Group.query.delete()
        Class.query.delete()
        User.query.delete()
        db.session.commit()
        print('Database emptied. Schema intact.')


if __name__ == '__main__':
    main()
