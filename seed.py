"""
Seed script: creates 3 teacher accounts, 3 classes with skill trees,
and 50 students with various progressions.

Usage:
    python seed.py

Prints all login codes at the end.
WARNING: drops and recreates the entire database.
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta

from app import app
from models import (Class, CrossSkillLink, Enrollment, Group,
                    SkillClaim, User, db, generate_code)
import competenssator as cs
import yaml as pyyaml

# ---------------------------------------------------------------------------
# YAML definitions — loaded from disk
# ---------------------------------------------------------------------------

_BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_BASE, 'arbre-3N5.yaml'), encoding='utf-8') as _f:
    YAML_3N5 = _f.read()

with open(os.path.join(_BASE, 'arbre-4N6.yaml'), encoding='utf-8') as _f:
    YAML_4N6 = _f.read()

with open(os.path.join(_BASE, 'arbre-5N6.yaml'), encoding='utf-8') as _f:
    YAML_5N6 = _f.read()

# Example teacher notes used randomly when seeding validations
EXAMPLE_NOTES = [
    "Très bonne attention aux détails là-dessus.",
    "Bon travail, la logique est claire.",
    "Solide compréhension du concept.",
    "Quelques imprécisions mais l'essentiel est là.",
    "Excellent ! Dépassé les attentes.",
    None, None, None,  # weighted toward no note
]

STUDENT_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Ethan",
    "Fiona", "Gabriel", "Hannah", "Ivan", "Julia",
    "Kevin", "Laura", "Marco", "Nina", "Oscar",
    "Paula", "Quentin", "Rachel", "Samuel", "Tina",
    "Ugo", "Valerie", "William", "Xena", "Yann",
    "Zara", "Antoine", "Beatrice", "Cedric", "Delphine",
    "Emmanuel", "Florence", "Gregoire", "Helene", "Ines",
    "Jerome", "Katia", "Luc", "Manon", "Nathan",
    "Olivia", "Pierre", "Querida", "Romain", "Sophie",
    "Thomas", "Ursula", "Victor", "Wendy", "Xavier",
]


def unique_code(existing_codes):
    while True:
        code = generate_code()
        if code not in existing_codes:
            existing_codes.add(code)
            return code


def get_ordered_skills(yaml_str):
    """Return skills in topological order (respecting prerequisites)."""
    import networkx as nx
    data = pyyaml.safe_load(yaml_str)
    G = cs.get_graph_from_data(data)
    try:
        return list(nx.topological_sort(G))
    except Exception:
        return list(G.nodes)


def seed_progression(student_id, class_id, skills_ordered, target_count):
    """Create validated SkillClaim records for the first target_count skills."""
    for skill in skills_ordered[:target_count]:
        existing = SkillClaim.query.filter_by(
            student_id=student_id, class_id=class_id, skill_name=skill).first()
        if not existing:
            claim = SkillClaim(
                student_id=student_id,
                class_id=class_id,
                skill_name=skill,
                status='validated',
                teacher_note=random.choice(EXAMPLE_NOTES),
            )
            claim.validated_at = claim.claimed_at
            db.session.add(claim)



def main():
    with app.app_context():
        print("Dropping and recreating all tables...")
        db.drop_all()
        db.create_all()

        used_codes = set()

        # -------------------------------------------------------------------
        # Teachers
        # -------------------------------------------------------------------
        joris_code = unique_code(used_codes)
        joris = User(code=joris_code, display_name='Joris', role='user')
        db.session.add(joris)

        po_code = unique_code(used_codes)
        pierre_olivier = User(code=po_code, display_name='Pierre-Olivier', role='user')
        db.session.add(pierre_olivier)

        marie_code = unique_code(used_codes)
        marie = User(code=marie_code, display_name='Marie', role='user')
        db.session.add(marie)

        db.session.flush()

        # -------------------------------------------------------------------
        # Classes
        # -------------------------------------------------------------------
        cls_3n5 = Class(
            name='3N5 — Développement mobile (Compose/Kotlin)',
            teacher_id=joris.id,
            yaml_content=YAML_3N5.strip(),
        )
        cls_4n6 = Class(
            name='4N6 — Client-serveur mobile',
            teacher_id=joris.id,
            yaml_content=YAML_4N6.strip(),
        )
        cls_5n6 = Class(
            name='5N6 — Flutter multiplateforme',
            teacher_id=pierre_olivier.id,
            yaml_content=YAML_5N6.strip(),
        )
        db.session.add_all([cls_3n5, cls_4n6, cls_5n6])
        db.session.flush()

        # Compute and cache layouts
        for cls in [cls_3n5, cls_4n6, cls_5n6]:
            try:
                data = pyyaml.safe_load(cls.yaml_content)
                layout = cs.compute_best_order(data)
                cls.skill_order = json.dumps(layout)
            except Exception as e:
                print(f"  Warning: could not compute layout for {cls.name}: {e}")

        db.session.flush()

        # -------------------------------------------------------------------
        # Groups
        # -------------------------------------------------------------------
        def make_group(class_id, name):
            code = unique_code(used_codes)
            g = Group(class_id=class_id, name=name, invite_code=code)
            db.session.add(g)
            return g

        grp_3n5 = make_group(cls_3n5.id, 'Groupe A')
        grp_4n6 = make_group(cls_4n6.id, 'Groupe A')
        grp_5n6 = make_group(cls_5n6.id, 'Groupe A')
        db.session.flush()

        # -------------------------------------------------------------------
        # Skills in topological order (for seeding progressions)
        # -------------------------------------------------------------------
        skills_3n5 = get_ordered_skills(YAML_3N5)
        skills_4n6 = get_ordered_skills(YAML_4N6)
        skills_5n6 = get_ordered_skills(YAML_5N6)

        n_3n5 = len(skills_3n5)
        n_4n6 = len(skills_4n6)
        n_5n6 = len(skills_5n6)

        # -------------------------------------------------------------------
        # 50 students with various progressions
        # -------------------------------------------------------------------
        # Distribution across classes:
        #   students 0-19  → 3N5
        #   students 20-39 → 4N6
        #   students 40-49 → 5N6
        # Some students (0-9) are also enrolled in 4N6 (they appear in both)

        student_codes = {}

        for i, name in enumerate(STUDENT_NAMES):
            code = unique_code(used_codes)
            student = User(code=code, display_name=name, role='user')
            db.session.add(student)
            db.session.flush()
            student_codes[name] = code

            # Determine progression fraction based on index within their class
            # We want a spread: some beginners, some advanced

            # Enroll in primary class
            if i < 20:
                # 3N5
                db.session.add(Enrollment(student_id=student.id, group_id=grp_3n5.id))
                frac = (i % 20) / 19.0   # 0.0 → 1.0
                target = int(frac * n_3n5)
                seed_progression(student.id, cls_3n5.id, skills_3n5, target)

                # First 10 also in 4N6 (cross-enrolled)
                if i < 10:
                    db.session.add(Enrollment(student_id=student.id, group_id=grp_4n6.id))
                    frac4 = (i % 10) / 9.0
                    target4 = int(frac4 * n_4n6 * 0.5)  # max 50% in 4N6
                    seed_progression(student.id, cls_4n6.id, skills_4n6, target4)

            elif i < 40:
                # 4N6
                db.session.add(Enrollment(student_id=student.id, group_id=grp_4n6.id))
                frac = (i - 20) / 19.0
                target = int(frac * n_4n6)
                seed_progression(student.id, cls_4n6.id, skills_4n6, target)

            else:
                # 5N6
                db.session.add(Enrollment(student_id=student.id, group_id=grp_5n6.id))
                frac = (i - 40) / 9.0
                target = int(frac * n_5n6)
                seed_progression(student.id, cls_5n6.id, skills_5n6, target)

        db.session.commit()

        # -------------------------------------------------------------------
        # Cross-skill links (example: Flutter Accès réseau → Flutter intro)
        # -------------------------------------------------------------------
        link1 = CrossSkillLink(
            source_class_id=cls_4n6.id,
            source_skill='Accès réseau',
            target_class_id=cls_5n6.id,
            target_skill='Appels HTTP',
            creator_id=joris.id,
        )
        link2 = CrossSkillLink(
            source_class_id=cls_5n6.id,
            source_skill='Navigation',
            target_class_id=cls_4n6.id,
            target_skill='Navigation, listes et i18n',
            creator_id=pierre_olivier.id,
        )
        db.session.add_all([link1, link2])
        db.session.commit()

        # -------------------------------------------------------------------
        # Print summary
        # -------------------------------------------------------------------
        print("\n" + "="*60)
        print("  SEED COMPLETE")
        print("="*60)
        print("\n📚 TEACHERS")
        print(f"  Joris            → code: {joris_code}")
        print(f"  Pierre-Olivier   → code: {po_code}")
        print(f"  Marie            → code: {marie_code}")

        print("\n📖 CLASSES")
        print(f"  {cls_3n5.name}")
        print(f"    Groupe A invite code: {grp_3n5.invite_code}")
        print(f"  {cls_4n6.name}")
        print(f"    Groupe A invite code: {grp_4n6.invite_code}")
        print(f"  {cls_5n6.name}")
        print(f"    Groupe A invite code: {grp_5n6.invite_code}")

        print("\n🎓 STUDENTS (first 10 shown)")
        for name in STUDENT_NAMES[:10]:
            print(f"  {name:<20} → code: {student_codes[name]}")
        print(f"  ... ({len(STUDENT_NAMES) - 10} more students)")

        print("\n✅ Done! Login at http://localhost:5000/login")
        print("="*60)


if __name__ == '__main__':
    main()
