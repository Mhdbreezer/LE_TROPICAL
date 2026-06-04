from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))

class Utilisateur(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) # Admin, Medecin, Patient, Pharmacien, Receptionniste
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Link to patient if role is patient
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    patient = db.relationship('Patient', backref='user', uselist=False)
    
    # Link to medecin if role is medecin
    medecin_id = db.Column(db.Integer, db.ForeignKey('medecin.id'), nullable=True)
    medecin = db.relationship('Medecin', backref='user', uselist=False)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_service = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    medecins = db.relationship('Medecin', backref='service', lazy=True)

class Centre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_centre = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200))
    telephone = db.Column(db.String(20))

class Medecin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    specialite = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    teleconsult_active = db.Column(db.Boolean, default=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    centre_id = db.Column(db.Integer, db.ForeignKey('centre.id'), nullable=True)
    
    rdvs = db.relationship('RendezVous', backref='medecin', lazy=True)
    dispos = db.relationship('Disponibilite', backref='medecin', lazy=True)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    date_naissance = db.Column(db.Date, nullable=False)
    sexe = db.Column(db.String(10))
    adresse = db.Column(db.String(200))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    centre_id = db.Column(db.Integer, db.ForeignKey('centre.id'), nullable=True)
    
    assurance_id = db.Column(db.Integer, db.ForeignKey('assurance.id'), nullable=True)
    assurance = db.relationship('Assurance', backref='patients')
    
    dossier = db.relationship('DossierMedical', backref='patient', uselist=False)
    rdvs = db.relationship('RendezVous', backref='patient', lazy=True)
    file_attente = db.relationship('FileAttente', backref='patient', lazy=True)

class DossierMedical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    antecedents = db.Column(db.Text)
    allergies = db.Column(db.Text)
    groupe_sanguin = db.Column(db.String(5))

class RendezVous(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_rdv = db.Column(db.Date, nullable=False)
    heure_rdv = db.Column(db.Time, nullable=False)
    statut = db.Column(db.String(20), default='Programmé') # Programmé, Annulé, Terminé, Urgence
    type_rdv = db.Column(db.String(20), default='Présentiel') # Présentiel, Téléconsultation
    priorite = db.Column(db.Integer, default=1)
    degre_urgence = db.Column(db.String(20), default='Normal') # Normal, Moyen, Critique (Triage)
    
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    medecin_id = db.Column(db.Integer, db.ForeignKey('medecin.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)
    centre_id = db.Column(db.Integer, db.ForeignKey('centre.id'), nullable=True)
    
    consultation = db.relationship('Consultation', backref='rdv', uselist=False)

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rdv_id = db.Column(db.Integer, db.ForeignKey('rendez_vous.id'), nullable=False)
    date_consultation = db.Column(db.DateTime, default=datetime.utcnow)
    diagnostic = db.Column(db.Text)
    observations = db.Column(db.Text)
    type_consult = db.Column(db.String(50))
    
    ordonnance = db.relationship('Ordonnance', backref='consultation', uselist=False)
    facture = db.relationship('Facture', backref='consultation', uselist=False)

class Ordonnance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'), nullable=False)
    date_ordonnance = db.Column(db.DateTime, default=datetime.utcnow)
    validite = db.Column(db.Integer, default=30) # jours
    
    lignes = db.relationship('LigneOrdonnance', backref='ordonnance', lazy=True)

class Medicament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_medicament = db.Column(db.String(100), nullable=False)
    forme = db.Column(db.String(50))
    dosage = db.Column(db.String(50))
    seuil_alerte = db.Column(db.Integer, default=10)
    
    lots = db.relationship('LotMedicament', backref='medicament', lazy=True)

class LigneOrdonnance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ordonnance_id = db.Column(db.Integer, db.ForeignKey('ordonnance.id'), nullable=False)
    medicament_id = db.Column(db.Integer, db.ForeignKey('medicament.id'), nullable=False)
    posologie = db.Column(db.String(200))
    duree = db.Column(db.String(50))
    quantite = db.Column(db.Integer)
    
    medicament = db.relationship('Medicament', backref='lignes_ordonnance_orig')

class Facture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'), nullable=False)
    date_facture = db.Column(db.DateTime, default=datetime.utcnow)
    montant_total = db.Column(db.Float, nullable=False)
    montant_paye = db.Column(db.Float, default=0.0)
    statut = db.Column(db.String(20), default='En attente') # Payée, Partielle, En attente

class Assurance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_assurance = db.Column(db.String(100), nullable=False)
    taux_pec = db.Column(db.Float) # Taux Prise En Charge
    plafond_annuel = db.Column(db.Float)

class FileAttente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)
    priorite = db.Column(db.Integer, default=1)
    statut = db.Column(db.String(20), default='En attente')

class Disponibilite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medecin_id = db.Column(db.Integer, db.ForeignKey('medecin.id'), nullable=False)
    jour = db.Column(db.String(15)) # Lundi, Mardi, etc.
    heure_debut = db.Column(db.Time)
    heure_fin = db.Column(db.Time)

class LotMedicament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicament_id = db.Column(db.Integer, db.ForeignKey('medicament.id'), nullable=False)
    date_expiration = db.Column(db.Date, nullable=False)
    qte_initiale = db.Column(db.Integer)
    qte_restante = db.Column(db.Integer)
    date_reception = db.Column(db.Date, default=datetime.utcnow)

class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicament_a_id = db.Column(db.Integer, db.ForeignKey('medicament.id'), nullable=False)
    medicament_b_id = db.Column(db.Integer, db.ForeignKey('medicament.id'), nullable=False)
    niveau_risque = db.Column(db.String(20)) # Élevé, Modéré, Faible
    description = db.Column(db.Text)
