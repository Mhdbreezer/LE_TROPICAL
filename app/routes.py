from flask import Blueprint, render_template, url_for, flash, redirect, request
from app import db, bcrypt
from app.models import Utilisateur, Patient, Medecin, RendezVous, DossierMedical, Consultation, Ordonnance, LigneOrdonnance, Medicament, Facture, Interaction, Service, Centre, Assurance
from app.forms import PatientForm, RDVForm, ConsultationForm, OrdonnanceLineForm, MedicamentForm, ServiceForm, MedecinForm, AssuranceForm
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
from app.utils import generate_facture_pdf, generate_ordonnance_pdf, generate_dossier_pdf

main = Blueprint('main', __name__)

@main.route("/", methods=['GET', 'POST'])
@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Utilisateur.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Connexion échouée.', 'danger')
    return render_template('login.html')

@main.route("/dashboard")
@login_required
def dashboard():
    stats = {}
    if current_user.role == 'Administrateur':
        stats['total_patients'] = Patient.query.count()
        stats['total_medecins'] = Medecin.query.count()
        stats['total_services'] = Service.query.count()
        stats['recette_totale'] = db.session.query(db.func.sum(Facture.montant_total)).scalar() or 0
    elif current_user.role == 'Medecin':
        today = datetime.now().date()
        stats['rdv_today'] = RendezVous.query.filter_by(medecin_id=current_user.medecin_id, date_rdv=today, statut='Programmé').count()
        stats['consult_month'] = Consultation.query.join(RendezVous).filter(RendezVous.medecin_id == current_user.medecin_id).count()
        stats['patients_service'] = Patient.query.join(RendezVous).filter(RendezVous.medecin_id == current_user.medecin_id).count()
    elif current_user.role == 'Pharmacien':
        stats['total_meds'] = Medicament.query.count()
        low_stock_count = 0
        for m in Medicament.query.all():
            if sum(lot.qte_restante for lot in m.lots) <= m.seuil_alerte:
                low_stock_count += 1
        stats['low_stock'] = low_stock_count
    elif current_user.role == 'Receptionniste':
        today = datetime.now().date()
        stats['rdv_today'] = RendezVous.query.filter_by(date_rdv=today).count()
        stats['waiting'] = RendezVous.query.filter_by(date_rdv=today, statut='En attente').count()

    if current_user.role == 'Medecin':
        recent_rdvs = RendezVous.query.filter_by(medecin_id=current_user.medecin_id).order_by(RendezVous.date_rdv.desc()).limit(5).all()
    elif current_user.role == 'Patient':
        recent_rdvs = RendezVous.query.filter_by(patient_id=current_user.patient_id).order_by(RendezVous.date_rdv.desc()).limit(5).all()
    else:
        recent_rdvs = RendezVous.query.order_by(RendezVous.date_rdv.desc()).limit(5).all()
    return render_template('dashboard.html', title='Tableau de bord', role=current_user.role, stats=stats, recent_rdvs=recent_rdvs)

# --- PATIENT MGMT ---
@main.route("/patients")
@login_required
def list_patients():
    if current_user.role not in ['Administrateur', 'Receptionniste', 'Medecin']:
        return redirect(url_for('main.dashboard'))
    patients = Patient.query.all()
    return render_template('patients.html', patients=patients)

@main.route("/patient/<int:patient_id>")
@login_required
def patient_details(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if current_user.role not in ['Administrateur', 'Receptionniste', 'Medecin']:
        if current_user.role == 'Patient' and current_user.patient_id != patient.id:
            return redirect(url_for('main.dashboard'))
    return render_template('patient_details.html', patient=patient, title=f"Dossier: {patient.prenom} {patient.nom}")

@main.route("/patient/nouveau", methods=['GET', 'POST'])
@login_required
def nouveau_patient():
    if current_user.role not in ['Administrateur', 'Receptionniste']:
        return redirect(url_for('main.dashboard'))
    form = PatientForm()
    form.assurance_id.choices = [(0, 'Aucune')] + [(a.id, a.nom_assurance) for a in Assurance.query.all()]
    form.centre_id.choices = [(0, 'Choisir un centre')] + [(c.id, c.nom_centre) for c in Centre.query.all()]
    if form.validate_on_submit():
        assur_id = form.assurance_id.data if form.assurance_id.data != 0 else None
        ctr_id = form.centre_id.data if form.centre_id.data != 0 else None
        patient = Patient(nom=form.nom.data, prenom=form.prenom.data, date_naissance=form.date_naissance.data, sexe=form.sexe.data, adresse=form.adresse.data, telephone=form.telephone.data, email=form.email.data, assurance_id=assur_id, centre_id=ctr_id)
        db.session.add(patient)
        db.session.commit()
        db.session.add(DossierMedical(patient_id=patient.id, allergies=form.allergies.data, antecedents=form.antecedents.data))
        db.session.commit()
        flash('Patient créé.', 'success')
        return redirect(url_for('main.list_patients'))
    return render_template('patient_form.html', form=form, title='Nouveau Patient')

@main.route("/patient/dossier/modifier/<int:patient_id>", methods=['GET', 'POST'])
@login_required
def modifier_dossier(patient_id):
    if current_user.role not in ['Administrateur', 'Medecin']:
        return redirect(url_for('main.dashboard'))
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.dossier.allergies = request.form.get('allergies')
        patient.dossier.antecedents = request.form.get('antecedents')
        patient.dossier.groupe_sanguin = request.form.get('groupe_sanguin')
        db.session.commit()
        flash('Dossier médical mis à jour.', 'success')
        return redirect(url_for('main.patient_details', patient_id=patient.id))
    return render_template('modifier_dossier.html', patient=patient)

# --- RDV MGMT ---
@main.route("/rdvs")
@login_required
def list_rdvs():
    if current_user.role == 'Pharmacien': return redirect(url_for('main.dashboard'))
    if current_user.role == 'Patient': rdvs = RendezVous.query.filter_by(patient_id=current_user.patient_id).all()
    elif current_user.role == 'Medecin': rdvs = RendezVous.query.filter_by(medecin_id=current_user.medecin_id).all()
    else: rdvs = RendezVous.query.all()
    return render_template('rdvs.html', rdvs=rdvs)

@main.route("/rdv/nouveau", methods=['GET', 'POST'])
@login_required
def nouveau_rdv():
    if current_user.role not in ['Administrateur', 'Receptionniste', 'Patient']: return redirect(url_for('main.dashboard'))
    form = RDVForm()
    if current_user.role == 'Patient':
        form.patient_id.choices = [(current_user.patient_id, f"{current_user.patient.prenom} {current_user.patient.nom}")]
    else:
        form.patient_id.choices = [(p.id, f"{p.prenom} {p.nom}") for p in Patient.query.all()]
    form.centre_id.choices = [(c.id, c.nom_centre) for c in Centre.query.all()]
    form.service_id.choices = [(s.id, s.nom_service) for s in Service.query.all()]
    form.medecin_id.choices = [(m.id, f"Dr {m.prenom} {m.nom} ({m.service.nom_service} - {m.centre.nom_centre if m.centre else 'N/A'})") for m in Medecin.query.all()]
    
    # Pre-fill for Triage
    is_urgence = request.args.get('statut') == 'Urgence'
    if is_urgence:
        form.degre_urgence.data = 'Critique'
        form.priorite.data = 3

    if form.validate_on_submit():
        existing = RendezVous.query.filter_by(medecin_id=form.medecin_id.data, date_rdv=form.date_rdv.data, heure_rdv=form.heure_rdv.data).first()
        if existing and not is_urgence: # Allow over-booking for emergencies
            flash('Créneau occupé.', 'danger')
        else:
            rdv_statut = 'Urgence' if is_urgence else 'Programmé'
            rdv = RendezVous(patient_id=form.patient_id.data, medecin_id=form.medecin_id.data, service_id=form.service_id.data, centre_id=form.centre_id.data, date_rdv=form.date_rdv.data, heure_rdv=form.heure_rdv.data, type_rdv=form.type_rdv.data, priorite=form.priorite.data, degre_urgence=form.degre_urgence.data, statut=rdv_statut)
            db.session.add(rdv)
            db.session.commit()
            flash('RDV planifié.', 'success')
            return redirect(url_for('main.list_rdvs'))
    return render_template('rdv_form.html', form=form, title='Nouveau RDV')

# --- ADMIN CRUD ---
@main.route("/admin/services")
@login_required
def list_services():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    return render_template('admin/services.html', services=Service.query.all())

@main.route("/admin/service/nouveau", methods=['GET', 'POST'])
@login_required
def nouveau_service():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    form = ServiceForm()
    if form.validate_on_submit():
        db.session.add(Service(nom_service=form.nom_service.data, description=form.description.data))
        db.session.commit()
        return redirect(url_for('main.list_services'))
    return render_template('admin/service_form.html', form=form, title='Nouveau Service')

@main.route("/admin/medecins")
@login_required
def list_medecins():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    return render_template('admin/medecins.html', medecins=Medecin.query.all())

@main.route("/admin/medecin/nouveau", methods=['GET', 'POST'])
@login_required
def nouveau_medecin():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    form = MedecinForm()
    form.service_id.choices = [(s.id, s.nom_service) for s in Service.query.all()]
    form.centre_id.choices = [(c.id, c.nom_centre) for c in Centre.query.all()]
    if form.validate_on_submit():
        hashed_pass = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        med = Medecin(nom=form.nom.data, prenom=form.prenom.data, specialite=form.specialite.data, telephone=form.telephone.data, service_id=form.service_id.data, centre_id=form.centre_id.data)
        db.session.add(med)
        db.session.commit()
        db.session.add(Utilisateur(username=form.username.data, password=hashed_pass, role='Medecin', medecin_id=med.id))
        db.session.commit()
        flash('Médecin créé.', 'success')
        return redirect(url_for('main.list_medecins'))
    return render_template('admin/medecin_form.html', form=form, title='Nouveau Médecin')

# --- PHARMA & DOCTOR ---
@main.route("/consultation/nouvelle/<int:rdv_id>", methods=['GET', 'POST'])
@login_required
def nouvelle_consultation(rdv_id):
    if current_user.role != 'Medecin': return redirect(url_for('main.dashboard'))
    rdv = RendezVous.query.get_or_404(rdv_id)
    form = ConsultationForm()
    if form.validate_on_submit():
        c = Consultation(rdv_id=rdv.id, diagnostic=form.diagnostic.data, observations=form.observations.data)
        rdv.statut = 'Terminé'
        db.session.add(c)
        db.session.commit()
        db.session.add(Facture(consultation_id=c.id, montant_total=10000.0))
        db.session.commit()
        return redirect(url_for('main.gestion_ordonnance', consult_id=c.id))
    return render_template('consultation_form.html', form=form, rdv=rdv, title='Consultation')

@main.route("/consultation/ordonnance/<int:consult_id>", methods=['GET', 'POST'])
@login_required
def gestion_ordonnance(consult_id):
    if current_user.role != 'Medecin': return redirect(url_for('main.dashboard'))
    consult = Consultation.query.get_or_404(consult_id)
    ord = Ordonnance.query.filter_by(consultation_id=consult_id).first() or Ordonnance(consultation_id=consult_id)
    if not ord.id: db.session.add(ord); db.session.commit()
    form = OrdonnanceLineForm()
    form.medicament_id.choices = [(m.id, m.nom_medicament) for m in Medicament.query.all()]
    if form.validate_on_submit():
        db.session.add(LigneOrdonnance(ordonnance_id=ord.id, medicament_id=form.medicament_id.data, posologie=form.posologie.data, duree=form.duree.data, quantite=form.quantite.data))
        db.session.commit()
    return render_template('ordonnance_form.html', form=form, ordonnance=ord, consultation=consult)

@main.route("/pharmacie/inventaire")
@login_required
def pharmacie_inventaire():
    if current_user.role not in ['Pharmacien', 'Administrateur']: return redirect(url_for('main.dashboard'))
    return render_template('pharmacie.html', medicaments=Medicament.query.all())

@main.route("/pharmacie/medicament/nouveau", methods=['GET', 'POST'])
@login_required
def nouveau_medicament():
    if current_user.role not in ['Pharmacien', 'Administrateur']: return redirect(url_for('main.dashboard'))
    form = MedicamentForm()
    if form.validate_on_submit():
        db.session.add(Medicament(nom_medicament=form.nom_medicament.data, forme=form.forme.data, dosage=form.dosage.data, seuil_alerte=form.seuil_alerte.data))
        db.session.commit()
        flash('Médicament ajouté.', 'success')
        return redirect(url_for('main.pharmacie_inventaire'))
    return render_template('medicament_form.html', form=form, title='Nouveau Médicament')

@main.route("/pharmacie/ordonnances")
@login_required
def pharmacie_ordonnances():
    if current_user.role not in ['Pharmacien', 'Administrateur']: return redirect(url_for('main.dashboard'))
    return render_template('pharmacie/ordonnances_list.html', ordonnances=Ordonnance.query.all())

@main.route("/pdf/dossier/<int:patient_id>")
@login_required
def pdf_dossier(patient_id):
    p = Patient.query.get_or_404(patient_id)
    if current_user.role == 'Patient' and p.id != current_user.patient_id:
        return redirect(url_for('main.dashboard'))
    return generate_dossier_pdf(p)

@main.route("/pdf/facture/<int:facture_id>")
@login_required
def pdf_facture(facture_id):
    f = Facture.query.get_or_404(facture_id)
    if current_user.role == 'Patient' and f.consultation.rdv.patient_id != current_user.patient_id: return redirect(url_for('main.dashboard'))
    return generate_facture_pdf(f)

@main.route("/pdf/ordonnance/<int:ordonnance_id>")
@login_required
def pdf_ordonnance(ordonnance_id):
    o = Ordonnance.query.get_or_404(ordonnance_id)
    if current_user.role == 'Patient' and o.consultation.rdv.patient_id != current_user.patient_id: return redirect(url_for('main.dashboard'))
    return generate_ordonnance_pdf(o)

@main.route("/reception/file-attente")
@login_required
def file_attente():
    if current_user.role not in ['Receptionniste', 'Administrateur']:
        return redirect(url_for('main.dashboard'))
    today = datetime.now().date()
    rdvs = RendezVous.query.filter_by(date_rdv=today).order_by(RendezVous.heure_rdv).all()
    return render_template('reception/file.html', rdvs=rdvs)

@main.route("/rdv/arriver/<int:rdv_id>")
@login_required
def marquer_arrive(rdv_id):
    if current_user.role not in ['Receptionniste', 'Administrateur']:
        return redirect(url_for('main.dashboard'))
    rdv = RendezVous.query.get_or_404(rdv_id)
    rdv.statut = 'En attente' 
    db.session.commit()
    flash('Patient marqué comme présent.', 'success')
    return redirect(url_for('main.file_attente'))

# --- ADMIN: TRANSFER DOCTOR ---
@main.route("/admin/medecin/modifier/<int:med_id>", methods=['GET', 'POST'])
@login_required
def modifier_medecin(med_id):
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    med = Medecin.query.get_or_404(med_id)
    form = MedecinForm(obj=med)
    form.service_id.choices = [(s.id, s.nom_service) for s in Service.query.all()]
    if form.validate_on_submit():
        med.nom = form.nom.data
        med.prenom = form.prenom.data
        med.specialite = form.specialite.data
        med.service_id = form.service_id.data
        db.session.commit()
        flash('Médecin mis à jour.', 'success')
        return redirect(url_for('main.list_medecins'))
    return render_template('admin/medecin_form.html', form=form, title='Modifier Médecin')


# --- RECEPTION: EDIT RDV (PRIORITY) ---
@main.route("/rdv/modifier/<int:rdv_id>", methods=['GET', 'POST'])
@login_required
def modifier_rdv(rdv_id):
    if current_user.role not in ['Receptionniste', 'Administrateur']: return redirect(url_for('main.dashboard'))
    rdv = RendezVous.query.get_or_404(rdv_id)
    form = RDVForm(obj=rdv)
    form.patient_id.choices = [(p.id, f"{p.prenom} {p.nom}") for p in Patient.query.all()]
    form.service_id.choices = [(s.id, s.nom_service) for s in Service.query.all()]
    form.medecin_id.choices = [(m.id, f"Dr {m.prenom} {m.nom}") for m in Medecin.query.all()]
    if form.validate_on_submit():
        rdv.priorite = form.priorite.data
        rdv.type_rdv = form.type_rdv.data
        rdv.service_id = form.service_id.data
        db.session.commit()
        flash('RDV mis à jour.', 'success')
        return redirect(url_for('main.file_attente'))
    return render_template('rdv_form.html', form=form, title='Modifier RDV')


# --- ASSURANCE MGMT ---
@main.route("/admin/assurances")
@login_required
def list_assurances():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    return render_template('admin/assurances.html', assurances=Assurance.query.all())

@main.route("/admin/assurance/nouvelle", methods=['GET', 'POST'])
@login_required
def nouvelle_assurance():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    form = AssuranceForm()
    if form.validate_on_submit():
        a = Assurance(nom_assurance=form.nom_assurance.data, taux_pec=form.taux_pec.data, plafond_annuel=form.plafond_annuel.data)
        db.session.add(a)
        db.session.commit()
        flash('Assurance ajoutée.', 'success')
        return redirect(url_for('main.list_assurances'))
    return render_template('admin/assurance_form.html', form=form, title='Nouvelle Assurance')

@main.route("/admin/rapports")
@login_required
def rapports():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    
    # 1. Appointments per status
    rdv_stats = db.session.query(RendezVous.statut, db.func.count(RendezVous.id)).group_by(RendezVous.statut).all()
    rdv_labels = [s[0] for s in rdv_stats]
    rdv_data = [s[1] for s in rdv_stats]
    
    # 2. Revenue per month (Last 6 months)
    revenue_stats = db.session.query(
        db.func.strftime('%Y-%m', Facture.date_facture), 
        db.func.sum(Facture.montant_total)
    ).group_by(db.func.strftime('%Y-%m', Facture.date_facture)).order_by(Facture.date_facture).limit(6).all()
    rev_labels = [s[0] for s in revenue_stats]
    rev_data = [s[1] for s in revenue_stats]

    # 3. Patients by gender
    gender_stats = db.session.query(Patient.sexe, db.func.count(Patient.id)).group_by(Patient.sexe).all()
    gender_labels = ['Masculin' if s[0]=='M' else 'Féminin' for s in gender_stats]
    gender_data = [s[1] for s in gender_stats]

    return render_template('admin/rapports.html', 
                           rdv_labels=rdv_labels, rdv_data=rdv_data,
                           rev_labels=rev_labels, rev_data=rev_data,
                           gender_labels=gender_labels, gender_data=gender_data)

# --- LOGOUT ---
@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.login'))
