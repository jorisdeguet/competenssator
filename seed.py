"""
Seed script: creates 3 teacher accounts, 3 classes with skill trees,
and 50 students with various progressions.

Usage:
    python seed.py

Prints all login codes at the end.
WARNING: drops and recreates the entire database.
"""

import json
import random
import sys

from app import app
from models import (Class, CrossSkillLink, Enrollment, Group,
                    SkillClaim, User, db, generate_code)
import competenssator as cs
import yaml as pyyaml

# ---------------------------------------------------------------------------
# YAML definitions
# ---------------------------------------------------------------------------

YAML_3N5 = """
config:
  blackAndWhite: false
  withTickBox: false

skills:
  - name: "Kotlin : premiers pas"
    description: "Plan de cours, premiers projets Kotlin"
  - name: "Présentation TP1"
    description: "Projet créé, TP1"
  - name: "Impératif"
    description: "Bases impératives Kotlin"
  - name: "Collections"
    description: "Librairie standard, Collections"
  - name: "Librairies tierces"
    description: "Gradle, dépendances externes"
  - name: "Structurer son code"
    description: "Architecture et organisation"
  - name: "Intégration TP1"
    description: "Remise TP1"
  - name: "Formatif intra"
    description: "Préparation examen"
  - name: "Examen Intra"
    description: "Examen intermédiaire"
  - name: "Intro Android"
    description: "Introduction à Android"
  - name: "Activités et navigation"
    description: "Navigation entre écrans"
  - name: "Listes"
    description: "RecyclerView, LazyColumn"
  - name: "État et i18n"
    description: "State hoisting, internationalisation"
  - name: "Graphique"
    description: "Charts et visualisation"
  - name: "Intégration TP2"
    description: "Remise TP2"
  - name: "Pile d'appels"
    description: "Stack traces et exceptions"
  - name: "Composables"
    description: "Syntaxe Compose avancée"
  - name: "Architecture service"
    description: "Packages et séparation service/UI"
  - name: "Tests"
    description: "Tests unitaires et d'intégration"
  - name: "Tiroir de navigation"
    description: "Navigation Drawer"
  - name: "Copilot et IA"
    description: "Utilisation de l'IA en développement"
  - name: "Intégration TP3"
    description: "Remise TP3"
  - name: "Formatif final"
    description: "Préparation examen final"
  - name: "Examen final"
    description: "Examen de fin de session"

deps:
  - from: "Kotlin : premiers pas"
    to: "Présentation TP1"
  - from: "Présentation TP1"
    to: "Impératif"
  - from: "Impératif"
    to: "Collections"
  - from: "Collections"
    to: "Librairies tierces"
  - from: "Librairies tierces"
    to: "Structurer son code"
  - from: "Structurer son code"
    to: "Intégration TP1"
  - from: "Intégration TP1"
    to: "Formatif intra"
  - from: "Formatif intra"
    to: "Examen Intra"
  - from: "Examen Intra"
    to: "Intro Android"
  - from: "Intro Android"
    to: "Activités et navigation"
  - from: "Activités et navigation"
    to: "Listes"
  - from: "Listes"
    to: "État et i18n"
  - from: "Listes"
    to: "Graphique"
  - from: "État et i18n"
    to: "Intégration TP2"
  - from: "Graphique"
    to: "Intégration TP2"
  - from: "Intégration TP2"
    to: "Pile d'appels"
  - from: "Pile d'appels"
    to: "Composables"
  - from: "Composables"
    to: "Architecture service"
  - from: "Architecture service"
    to: "Tests"
  - from: "Tests"
    to: "Tiroir de navigation"
  - from: "Tiroir de navigation"
    to: "Copilot et IA"
  - from: "Copilot et IA"
    to: "Intégration TP3"
  - from: "Intégration TP3"
    to: "Formatif final"
  - from: "Formatif final"
    to: "Examen final"
"""

YAML_4N6 = """
config:
  blackAndWhite: false
  withTickBox: false

skills:
  - name: "Flutter : révisions"
    description: "Plan de cours, révisions Flutter"
  - name: "Mise en page"
    description: "Widgets de mise en page"
  - name: "Navigation, listes et i18n"
    description: "Navigation, listes et multilingue"
  - name: "Scaffold"
    description: "Structure d'écran Scaffold"
  - name: "Portrait/paysage"
    description: "Adaptation orientation"
  - name: "Intégration TP1"
    description: "Remise TP1 (poids 10%)"
  - name: "Accès réseau"
    description: "HTTP, DIO, communication serveur"
  - name: "Formatif intra"
    description: "Préparation examen"
  - name: "Examen Intra"
    description: "Examen machine (8%)"
  - name: "Serveur Spring Boot"
    description: "Introduction Spring Boot"
  - name: "Cookies"
    description: "Session et cookies"
  - name: "Spring Boot Java"
    description: "Développement backend Java"
  - name: "Intégration TP2"
    description: "Remise TP2 (poids 20%)"
  - name: "Débogage"
    description: "Outils de débogage"
  - name: "Erreurs HTTP"
    description: "Gestion erreurs HTTP"
  - name: "Erreurs GUI"
    description: "Gestion erreurs interface"
  - name: "Attente serveur"
    description: "Chargement asynchrone"
  - name: "Cybersec : injections"
    description: "Injections et cryptographie"
  - name: "Cybersec : contrôle d'accès"
    description: "Contrôle d'accès et sécurité"
  - name: "Capture the flag"
    description: "Exercice de sécurité"
  - name: "Déploiement serveur"
    description: "Mise en production"
  - name: "DTO et Cookies avancés"
    description: "Retour sur DTO et Cookies"
  - name: "Formatif final"
    description: "Préparation examen final"
  - name: "Examen final"
    description: "Examen de fin de session (14%)"

deps:
  - from: "Flutter : révisions"
    to: "Mise en page"
  - from: "Mise en page"
    to: "Navigation, listes et i18n"
  - from: "Navigation, listes et i18n"
    to: "Scaffold"
  - from: "Scaffold"
    to: "Portrait/paysage"
  - from: "Portrait/paysage"
    to: "Intégration TP1"
  - from: "Intégration TP1"
    to: "Accès réseau"
  - from: "Accès réseau"
    to: "Formatif intra"
  - from: "Formatif intra"
    to: "Examen Intra"
  - from: "Examen Intra"
    to: "Serveur Spring Boot"
  - from: "Serveur Spring Boot"
    to: "Cookies"
  - from: "Cookies"
    to: "Spring Boot Java"
  - from: "Spring Boot Java"
    to: "Intégration TP2"
  - from: "Intégration TP2"
    to: "Débogage"
  - from: "Débogage"
    to: "Erreurs HTTP"
  - from: "Erreurs HTTP"
    to: "Erreurs GUI"
  - from: "Erreurs GUI"
    to: "Attente serveur"
  - from: "Attente serveur"
    to: "Cybersec : injections"
  - from: "Cybersec : injections"
    to: "Cybersec : contrôle d'accès"
  - from: "Cybersec : contrôle d'accès"
    to: "Capture the flag"
  - from: "Capture the flag"
    to: "Déploiement serveur"
  - from: "Déploiement serveur"
    to: "DTO et Cookies avancés"
  - from: "DTO et Cookies avancés"
    to: "Formatif final"
  - from: "Formatif final"
    to: "Examen final"
"""

YAML_5N6 = """
config:
  blackAndWhite: false
  withTickBox: false

skills:
  - name: "Introduction Flutter"
    description: "Premiers pas, tape le lapin"
  - name: "Mise en page"
    description: "Row, Column, Expanded"
  - name: "Navigation"
    description: "Passer d'une page à l'autre"
  - name: "Listes"
    description: "Lister des éléments"
  - name: "Appels HTTP"
    description: "DIO, appels HTTP"
  - name: "Intégration TP1"
    description: "TP1 complété"
  - name: "Organisation du code"
    description: "Extraire des widgets"
  - name: "Image Picker"
    description: "Sélectionner une image"
  - name: "Images authentifiées"
    description: "Obtenir des images d'un serveur"
  - name: "Affichage d'images"
    description: "Afficher une image"
  - name: "Formatif intra"
    description: "Préparation examen"
  - name: "Examen Intra"
    description: "Examen intermédiaire (20%)"
  - name: "Multilingue"
    description: "Traduire une application"
  - name: "Déploiement Playstore"
    description: "Déployer sur le Playstore"
  - name: "Gestion de l'état"
    description: "Cycle de vie, state"
  - name: "Notifications push"
    description: "Envoyer et recevoir des notifications"
  - name: "Intégration TP2"
    description: "TP2 complété"
  - name: "Authentification Firebase"
    description: "Connexion, création de compte"
  - name: "Firebase Firestore"
    description: "Stocker des données"
  - name: "Contrôle d'accès Firebase"
    description: "Sécuriser et typer les données"
  - name: "Stockage Firebase"
    description: "Stocker des fichiers"
  - name: "Streams Firebase"
    description: "Être avertis de changements"
  - name: "Règles Firebase"
    description: "Règles d'accès pour les services"
  - name: "Transitions Hero"
    description: "Animations entre écrans"
  - name: "Intégration TP3"
    description: "TP3 complété"
  - name: "Examen Final"
    description: "Examen de fin de session (20%)"

deps:
  - from: "Introduction Flutter"
    to: "Mise en page"
  - from: "Mise en page"
    to: "Navigation"
  - from: "Navigation"
    to: "Listes"
  - from: "Listes"
    to: "Appels HTTP"
  - from: "Appels HTTP"
    to: "Intégration TP1"
  - from: "Intégration TP1"
    to: "Organisation du code"
  - from: "Organisation du code"
    to: "Image Picker"
  - from: "Image Picker"
    to: "Images authentifiées"
  - from: "Images authentifiées"
    to: "Affichage d'images"
  - from: "Affichage d'images"
    to: "Formatif intra"
  - from: "Formatif intra"
    to: "Examen Intra"
  - from: "Examen Intra"
    to: "Multilingue"
  - from: "Examen Intra"
    to: "Déploiement Playstore"
  - from: "Multilingue"
    to: "Gestion de l'état"
  - from: "Déploiement Playstore"
    to: "Gestion de l'état"
  - from: "Gestion de l'état"
    to: "Notifications push"
  - from: "Notifications push"
    to: "Intégration TP2"
  - from: "Intégration TP2"
    to: "Authentification Firebase"
  - from: "Authentification Firebase"
    to: "Firebase Firestore"
  - from: "Firebase Firestore"
    to: "Contrôle d'accès Firebase"
  - from: "Contrôle d'accès Firebase"
    to: "Stockage Firebase"
  - from: "Stockage Firebase"
    to: "Streams Firebase"
  - from: "Streams Firebase"
    to: "Règles Firebase"
  - from: "Règles Firebase"
    to: "Transitions Hero"
  - from: "Transitions Hero"
    to: "Intégration TP3"
  - from: "Intégration TP3"
    to: "Examen Final"
"""

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
            name='4N6 — Client-serveur mobile (Flutter)',
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
