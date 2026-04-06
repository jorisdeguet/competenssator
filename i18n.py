"""
Simple FR/EN translation dictionary.
Usage in templates:  {{ t('key') }}
Usage in Python:     from i18n import get_t; t = get_t('fr')
"""

TRANSLATIONS = {
    # Navigation
    'nav.home':           {'fr': 'Accueil',              'en': 'Home'},
    'nav.new_class':      {'fr': 'Nouvelle classe',      'en': 'New class'},
    'nav.join':           {'fr': 'Rejoindre un groupe',  'en': 'Join a group'},
    'nav.logout':         {'fr': 'Déconnexion',          'en': 'Sign out'},
    'nav.notifications':  {'fr': 'Notifications',        'en': 'Notifications'},

    # Auth
    'auth.register_title':   {'fr': 'Créer un compte',          'en': 'Create an account'},
    'auth.register_hint':    {'fr': 'Entrez votre nom. Vous recevrez un code unique pour vous connecter.',
                              'en': 'Enter your name. You will receive a unique code to sign in.'},
    'auth.name_label':       {'fr': 'Votre nom',                'en': 'Your name'},
    'auth.name_placeholder': {'fr': 'Ex : Alice Tremblay',      'en': 'E.g. Alice Smith'},
    'auth.create_btn':       {'fr': 'Créer mon compte',         'en': 'Create my account'},
    'auth.login_title':      {'fr': 'Se connecter',             'en': 'Sign in'},
    'auth.code_label':       {'fr': 'Code de connexion',        'en': 'Login code'},
    'auth.code_placeholder': {'fr': 'Ex : ABCD1234',            'en': 'E.g. ABCD1234'},
    'auth.login_btn':        {'fr': 'Se connecter',             'en': 'Sign in'},
    'auth.no_account':       {'fr': 'Pas encore de compte ?',   'en': 'No account yet?'},
    'auth.create_link':      {'fr': 'Créer un compte',          'en': 'Create an account'},
    'auth.have_account':     {'fr': 'Déjà un compte ?',         'en': 'Already have an account?'},
    'auth.login_link':       {'fr': 'Se connecter',             'en': 'Sign in'},

    # Dashboard
    'dash.title':           {'fr': 'Tableau de bord',           'en': 'Dashboard'},
    'dash.my_classes':      {'fr': 'Classes que j\'enseigne',   'en': 'Classes I teach'},
    'dash.my_courses':      {'fr': 'Mes formations',            'en': 'My courses'},
    'dash.new_class':       {'fr': '+ Nouvelle classe',         'en': '+ New class'},
    'dash.no_classes':      {'fr': 'Aucune classe créée.',      'en': 'No classes yet.'},
    'dash.no_courses':      {'fr': 'Pas encore inscrit dans une formation.',
                             'en': 'Not enrolled in any course yet.'},
    'dash.join_btn':        {'fr': 'Rejoindre un groupe',       'en': 'Join a group'},
    'dash.create_class_btn':{'fr': 'Créer une classe',          'en': 'Create a class'},
    'dash.groups':          {'fr': 'groupes',                   'en': 'groups'},
    'dash.students':        {'fr': 'élèves',                    'en': 'students'},
    'dash.edit':            {'fr': 'Modifier',                  'en': 'Edit'},
    'dash.open':            {'fr': 'Ouvrir →',                  'en': 'Open →'},
    'dash.new_claims':      {'fr': 'nouveaux',                  'en': 'new'},
    'dash.progress':        {'fr': 'progression',               'en': 'progress'},

    # Teacher class detail
    'cls.layout':           {'fr': '🗺️ Mise en page',           'en': '🗺️ Layout'},
    'cls.edit_yaml':        {'fr': '✏️ Modifier YAML',          'en': '✏️ Edit YAML'},
    'cls.pending':          {'fr': '⏳ En attente de validation','en': '⏳ Pending validation'},
    'cls.no_pending':       {'fr': 'Aucune compétence en attente.', 'en': 'No skills pending.'},
    'cls.groups':           {'fr': '👥 Groupes',                'en': '👥 Groups'},
    'cls.new_group':        {'fr': 'Créer un groupe',           'en': 'Create a group'},
    'cls.group_name_ph':    {'fr': 'Ex : Groupe A',             'en': 'E.g. Group A'},
    'cls.create':           {'fr': 'Créer',                     'en': 'Create'},
    'cls.no_groups':        {'fr': 'Aucun groupe.',             'en': 'No groups.'},
    'cls.validate':         {'fr': '✓ Valider',                 'en': '✓ Validate'},
    'cls.reject':           {'fr': '✗ Refuser',                 'en': '✗ Reject'},
    'cls.manage':           {'fr': 'Gérer →',                   'en': 'Manage →'},
    'cls.links_title':      {'fr': '🔗 Liens vers d\'autres classes', 'en': '🔗 Links to other classes'},
    'cls.add_link':         {'fr': '+ Ajouter un lien',         'en': '+ Add a link'},
    'cls.source_skill':     {'fr': 'Compétence dans cette classe', 'en': 'Skill in this class'},
    'cls.target_class':     {'fr': 'Classe cible',              'en': 'Target class'},
    'cls.target_skill':     {'fr': 'Compétence cible',          'en': 'Target skill'},
    'cls.create_link':      {'fr': 'Créer le lien',             'en': 'Create link'},
    'cls.choose':           {'fr': '— Choisir —',               'en': '— Choose —'},
    'cls.choose_class_first': {'fr': '— Choisir une classe d\'abord —', 'en': '— Choose a class first —'},
    'cls.loading':          {'fr': 'Chargement…',               'en': 'Loading…'},
    'cls.load_error':       {'fr': 'Erreur de chargement',      'en': 'Load error'},
    'cls.invite_code':      {'fr': 'Code d\'invitation',        'en': 'Invitation code'},
    'cls.bulk_add':         {'fr': '➕ Ajouter des élèves en masse', 'en': '➕ Bulk add students'},
    'cls.bulk_create':      {'fr': 'Créer les comptes',         'en': 'Create accounts'},
    'cls.students':         {'fr': '👤 Élèves',                 'en': '👤 Students'},
    'cls.note_optional':    {'fr': 'Note optionnelle — ex : « Très bonne attention aux détails là-dessus. »',
                             'en': 'Optional note — e.g. "Great attention to detail here."'},
    'cls.submitted':        {'fr': 'Soumis le',                 'en': 'Submitted on'},
    'cls.validated_on':     {'fr': 'Validée le',                'en': 'Validated on'},
    'cls.rejected':         {'fr': '✗ Refusée',                 'en': '✗ Rejected'},
    'cls.skills_preview':   {'fr': 'Aperçu de l\'arbre',        'en': 'Tree preview'},
    'cls.learner':          {'fr': 'apprenant',                 'en': 'learner'},
    'cls.learners':         {'fr': 'apprenants',                'en': 'learners'},
    'cls.code':             {'fr': 'Code',                      'en': 'Code'},
    'cls.name':             {'fr': 'Nom',                       'en': 'Name'},

    # Group detail / student list
    'grp.progress':         {'fr': 'Progression du groupe',     'en': 'Group progress'},
    'grp.choose_layout':    {'fr': 'Choisissez d\'abord une mise en page pour la classe pour voir les statistiques ici.',
                             'en': 'Choose a layout for the class first to see statistics here.'},
    'grp.choose_layout_link': {'fr': 'Choisir →',              'en': 'Choose →'},

    # Student skill tree
    'tree.back':            {'fr': '← Tableau de bord',        'en': '← Dashboard'},
    'tree.validated':       {'fr': 'compétences validées',      'en': 'skills validated'},
    'tree.locked':          {'fr': 'Verrouillée',               'en': 'Locked'},
    'tree.available':       {'fr': 'Disponible',                'en': 'Available'},
    'tree.available_hint':  {'fr': '(clique pour déclarer !)',  'en': '(click to claim!)'},
    'tree.pending':         {'fr': 'En attente',                'en': 'Pending'},
    'tree.validated_tag':   {'fr': '✓ Validée',                 'en': '✓ Validated'},
    'tree.rejected_tag':    {'fr': 'Refusée',                   'en': 'Rejected'},
    'tree.rejected_hint':   {'fr': '(clique pour re-soumettre)','en': '(click to resubmit)'},
    'tree.pending_warn':    {'fr': 'compétence en attente de validation.',
                             'en': 'skill pending validation.'},
    'tree.pending_warn_pl': {'fr': 'compétences en attente de validation.',
                             'en': 'skills pending validation.'},
    'tree.cross_links':     {'fr': '🔗 Compétences liées dans d\'autres classes',
                             'en': '🔗 Skills linked from other classes'},
    'tree.teacher_notes':   {'fr': '📝 Notes de ton enseignant·e', 'en': '📝 Teacher notes'},
    'tree.no_notes':        {'fr': 'Aucune note de ton enseignant·e pour l\'instant.',
                             'en': 'No teacher notes yet.'},
    'tree.new_notif':       {'fr': '🔔 Nouvelles réponses de ton enseignant·e !',
                             'en': '🔔 New responses from your teacher!'},
    'tree.skill':           {'fr': 'Compétence',                'en': 'Skill'},
    'tree.result':          {'fr': 'Résultat',                  'en': 'Result'},
    'tree.note':            {'fr': 'Note',                      'en': 'Note'},
    'tree.date':            {'fr': 'Date',                      'en': 'Date'},

    # Join
    'join.title':           {'fr': 'Rejoindre un groupe',       'en': 'Join a group'},
    'join.code_label':      {'fr': 'Code d\'invitation',        'en': 'Invitation code'},
    'join.code_ph':         {'fr': 'Ex : ABCD1234',             'en': 'E.g. ABCD1234'},
    'join.submit':          {'fr': 'Rejoindre',                 'en': 'Join'},

    # Common
    'common.cancel':        {'fr': 'Annuler',                   'en': 'Cancel'},
    'common.close':         {'fr': 'Fermer',                    'en': 'Close'},
    'common.save':          {'fr': 'Enregistrer',               'en': 'Save'},
    'common.back_dash':     {'fr': '← Tableau de bord',        'en': '← Dashboard'},
    'common.see':           {'fr': 'Voir →',                    'en': 'View →'},
    'common.skills':        {'fr': 'compétences',               'en': 'skills'},
    'common.skill':         {'fr': 'compétence',                'en': 'skill'},
}


def get_t(lang: str = 'fr'):
    """Return a translation function for the given language."""
    def t(key: str) -> str:
        entry = TRANSLATIONS.get(key)
        if entry is None:
            return key
        return entry.get(lang, entry.get('fr', key))
    return t
