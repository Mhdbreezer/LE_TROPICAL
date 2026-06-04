from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, SelectField, TextAreaField, IntegerField, TimeField
from wtforms.validators import DataRequired, Email, Optional

class PatientForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired()])
    prenom = StringField('Prénom', validators=[DataRequired()])
    date_naissance = DateField('Date de Naissance', validators=[DataRequired()])
    sexe = SelectField('Sexe', choices=[('M', 'Masculin'), ('F', 'Féminin')], validators=[DataRequired()])
    adresse = StringField('Adresse')
    telephone = StringField('Téléphone', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    assurance_id = SelectField('Assurance', coerce=int, validators=[Optional()])
    centre_id = SelectField('Centre de Santé', coerce=int, validators=[Optional()])
    allergies = TextAreaField('Allergies (Informations critiques)', validators=[Optional()])
    antecedents = TextAreaField('Antécédents majeurs', validators=[Optional()])
    submit = SubmitField('Enregistrer le Patient')

class RDVForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    centre_id = SelectField('Centre', coerce=int, validators=[DataRequired()])
    service_id = SelectField('Service ciblé', coerce=int, validators=[DataRequired()])
    medecin_id = SelectField('Médecin', coerce=int, validators=[DataRequired()])
    date_rdv = DateField('Date du RDV', validators=[DataRequired()])
    heure_rdv = TimeField('Heure du RDV', validators=[DataRequired()])
    type_rdv = SelectField('Type de RDV', choices=[('Présentiel', 'Présentiel'), ('Téléconsultation', 'Téléconsultation')], default='Présentiel')
    priorite = SelectField('Priorité', choices=[(1, 'Basse'), (2, 'Normale'), (3, 'Haute')], coerce=int, default=2)
    degre_urgence = SelectField('Degré d\'Urgence (Triage)', choices=[('Normal', 'Normal'), ('Moyen', 'Moyen'), ('Critique', 'Critique')], default='Normal')
    submit = SubmitField('Planifier le Rendez-vous')

class ConsultationForm(FlaskForm):
    diagnostic = TextAreaField('Diagnostic', validators=[DataRequired()])
    observations = TextAreaField('Observations')
    type_consult = StringField('Type de Consultation', default='Générale')
    submit = SubmitField('Enregistrer la Consultation')

class OrdonnanceLineForm(FlaskForm):
    medicament_id = SelectField('Médicament', coerce=int, validators=[DataRequired()])
    posologie = StringField('Posologie', validators=[DataRequired()])
    duree = StringField('Durée', validators=[DataRequired()])
    quantite = IntegerField('Quantité', validators=[DataRequired()])
    submit = SubmitField('Ajouter au Panier')

class MedicamentForm(FlaskForm):
    nom_medicament = StringField('Nom du Médicament', validators=[DataRequired()])
    forme = StringField('Forme (ex: Comprimé, Sirop)')
    dosage = StringField('Dosage (ex: 500mg)')
    seuil_alerte = IntegerField('Seuil d\'alerte stock', default=10)
    submit = SubmitField('Enregistrer')

class ServiceForm(FlaskForm):
    nom_service = StringField('Nom du Service', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Créer le Service')

class MedecinForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired()])
    prenom = StringField('Prénom', validators=[DataRequired()])
    specialite = StringField('Spécialité', validators=[DataRequired()])
    telephone = StringField('Téléphone')
    service_id = SelectField('Service', coerce=int, validators=[DataRequired()])
    centre_id = SelectField('Centre', coerce=int, validators=[DataRequired()])
    username = StringField('Nom d\'utilisateur (Login)', validators=[DataRequired()])
    password = StringField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Enregistrer le Médecin')

class AssuranceForm(FlaskForm):
    nom_assurance = StringField('Nom de l\'Assurance', validators=[DataRequired()])
    taux_pec = IntegerField('Taux de Prise en Charge (%)', validators=[DataRequired()])
    plafond_annuel = IntegerField('Plafond Annuel (CFA)', validators=[Optional()])
    submit = SubmitField('Enregistrer l\'Assurance')
