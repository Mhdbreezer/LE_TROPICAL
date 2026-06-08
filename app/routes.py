from flask import Blueprint, render_template, url_for, flash, redirect, request
from app import db, bcrypt
from app.models import Utilisateur, Patient, Medecin, RendezVous, DossierMedical, Consultation, Ordonnance, LigneOrdonnance, Medicament, Facture, Interaction, Service, Centre, Assurance, LotMedicament, Notification
from app.forms import PatientForm, RDVForm, ConsultationForm, OrdonnanceLineForm, MedicamentForm, ServiceForm, MedecinForm, AssuranceForm, UrgenceForm, UtilisateurForm
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime, timedelta
from app.utils import generate_facture_pdf, generate_ordonnance_pdf, generate_dossier_pdf, envoyer_notification

main = Blueprint('main', __name__)

@main.route("/admin/db-init")
def db_init_route():
    secret = request.args.get('secret')
    if secret != 'senegal2026':
        return "Accès refusé.", 403
    
    try:
        # 1. Créer les tables si elles n'existent pas
        db.create_all()
        
        # 2. Vérifier si l'admin existe
        admin = Utilisateur.query.filter_by(username='admin').first()
        if not admin:
            # Création de l'admin
            admin_pass = bcrypt.generate_password_hash('admin123').decode('utf-8')
            new_admin = Utilisateur(username='admin', password=admin_pass, role='Administrateur')
            db.session.add(new_admin)
            
            # Création d'un service et d'un centre par défaut
            s1 = Service(nom_service='Généraliste', description='Médecine générale')
            c1 = Centre(nom_centre='Centre Principal', adresse='Dakar', telephone='338000000')
            db.session.add_all([s1, c1])
            
            db.session.commit()
            return "Base Postgres initialisée ! Connectez-vous avec admin / admin123"
        else:
            return "La base est déjà prête. L'utilisateur admin existe déjà."
            
    except Exception as e:
        db.session.rollback()
        return f"Erreur fatale : {str(e)}"

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
            if m.total_stock <= m.seuil_alerte:
                low_stock_count += 1
        stats['low_stock'] = low_stock_count
    elif current_user.role == 'Receptionniste':
        today = datetime.now().date()
        stats['rdv_today'] = RendezVous.query.filter_by(date_rdv=today).count()
        stats['waiting'] = RendezVous.query.filter_by(date_rdv=today, statut='En attente').count()
    elif current_user.role == 'Caissier':
        today = datetime.now().date()
        stats['pending_invoices'] = Facture.query.filter_by(statut='En attente').count()
        stats['partial_invoices'] = Facture.query.filter_by(statut='Partielle').count()
        stats['overdue_invoices'] = Facture.query.filter(Facture.statut != 'Payée', Facture.date_facture < datetime.now() - timedelta(days=2)).count()
        stats['daily_revenue'] = db.session.query(db.func.sum(Facture.montant_paye)).filter(db.func.date(Facture.date_facture) == today).scalar() or 0
        stats['total_billed'] = db.session.query(db.func.sum(Facture.montant_total)).scalar() or 0
        stats['total_paid'] = db.session.query(db.func.sum(Facture.montant_paye)).scalar() or 0

    if current_user.role == 'Medecin':
        recent_rdvs = RendezVous.query.filter_by(medecin_id=current_user.medecin_id).order_by(RendezVous.date_rdv.desc()).limit(5).all()
    elif current_user.role == 'Patient':
        recent_rdvs = RendezVous.query.filter_by(patient_id=current_user.patient_id).order_by(RendezVous.date_rdv.desc()).limit(5).all()
    else:
        recent_rdvs = RendezVous.query.order_by(RendezVous.date_rdv.desc()).limit(5).all()
    return render_template('dashboard.html', title='Tableau de bord', role=current_user.role, stats=stats, recent_rdvs=recent_rdvs)

@main.route("/patients")
@login_required
def list_patients():
    if current_user.role not in ['Administrateur', 'Receptionniste', 'Medecin']:
        return redirect(url_for('main.dashboard'))
    if current_user.role == 'Medecin':
        patients = Patient.query.join(RendezVous).filter(RendezVous.medecin_id == current_user.medecin_id).distinct().all()
    else:
        patients = Patient.query.all()
    return render_template('patients.html', patients=patients)

@main.route("/patient/dossier/<int:patient_id>")
@login_required
def voir_dossier(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if current_user.role == 'Patient' and current_user.patient_id != patient.id:
        return redirect(url_for('main.dashboard'))
    if current_user.role == 'Medecin':
        assigne = RendezVous.query.filter_by(medecin_id=current_user.medecin_id, patient_id=patient.id).first()
        if not assigne:
            flash("Non autorisé.", "danger")
            return redirect(url_for('main.list_patients'))
    return render_template('patient_dossier_view.html', patient=patient)

@main.route("/patient/<int:patient_id>")
@login_required
def patient_details(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if current_user.role == 'Patient' and current_user.patient_id != patient.id:
        return redirect(url_for('main.dashboard'))
    if current_user.role == 'Medecin':
        assigne = RendezVous.query.filter_by(medecin_id=current_user.medecin_id, patient_id=patient.id).first()
        if not assigne:
            flash("Non autorisé.", "danger")
            return redirect(url_for('main.list_patients'))
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
        # Vérification proactive du nom d'utilisateur
        existing_user = Utilisateur.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash(f"Le nom d'utilisateur '{form.username.data}' est déjà utilisé. Veuillez en choisir un autre.", 'danger')
            return render_template('patient_form.html', form=form, title='Nouveau Patient')

        assur_id = form.assurance_id.data if form.assurance_id.data != 0 else None
        ctr_id = form.centre_id.data if form.centre_id.data != 0 else None
        try:
            # Création du patient
            patient = Patient(nom=form.nom.data, prenom=form.prenom.data, date_naissance=form.date_naissance.data, sexe=form.sexe.data, adresse=form.adresse.data, telephone=form.telephone.data, email=form.email.data, assurance_id=assur_id, centre_id=ctr_id)
            db.session.add(patient)
            db.session.flush() # Génère l'ID du patient sans valider la transaction
            
            # Création du compte utilisateur
            hashed_pass = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            new_user = Utilisateur(username=form.username.data, password=hashed_pass, role='Patient', patient_id=patient.id)
            db.session.add(new_user)
            
            # Création du dossier médical
            db.session.add(DossierMedical(patient_id=patient.id, allergies=form.allergies.data, antecedents=form.antecedents.data))
            
            db.session.commit() # Valide tout en une seule fois
            flash('Patient et compte utilisateur créés avec succès.', 'success')
            return redirect(url_for('main.list_patients'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement : {str(e)}", 'danger')
    return render_template('patient_form.html', form=form, title='Nouveau Patient')

@main.route("/patient/dossier/modifier/<int:patient_id>", methods=['GET', 'POST'])
@login_required
def modifier_dossier(patient_id):
    if current_user.role not in ['Administrateur', 'Medecin']:
        return redirect(url_for('main.dashboard'))
    patient = Patient.query.get_or_404(patient_id)
    if not patient.dossier:
        patient.dossier = DossierMedical(patient_id=patient.id)
        db.session.add(patient.dossier)
        db.session.commit()
    if request.method == 'POST':
        patient.dossier.allergies = request.form.get('allergies')
        patient.dossier.antecedents = request.form.get('antecedents')
        patient.dossier.groupe_sanguin = request.form.get('groupe_sanguin')
        db.session.commit()
        flash('Dossier médical mis à jour.', 'success')
        return redirect(url_for('main.patient_details', patient_id=patient.id))
    return render_template('modifier_dossier.html', patient=patient)

@main.route("/rdvs")
@login_required
def list_rdvs():
    if current_user.role == 'Pharmacien': return redirect(url_for('main.dashboard'))
    today = datetime.now().date()
    query = RendezVous.query.filter(RendezVous.date_rdv == today, RendezVous.statut.notin_(['Terminé', 'Annulé']))
    if current_user.role == 'Patient': rdvs = query.filter_by(patient_id=current_user.patient_id)
    elif current_user.role == 'Medecin': rdvs = query.filter_by(medecin_id=current_user.medecin_id)
    else: rdvs = query
    rdvs = rdvs.order_by(RendezVous.priorite.desc(), RendezVous.heure_rdv.asc()).all()
    return render_template('rdvs.html', rdvs=rdvs, title="Planning du jour")

@main.route("/rdvs/historique")
@login_required
def historique_rdvs():
    if current_user.role == 'Pharmacien': return redirect(url_for('main.dashboard'))
    query = RendezVous.query.filter(RendezVous.statut.in_(['Terminé', 'Annulé']))
    if current_user.role == 'Patient': rdvs = query.filter_by(patient_id=current_user.patient_id)
    elif current_user.role == 'Medecin': rdvs = query.filter_by(medecin_id=current_user.medecin_id)
    else: rdvs = query
    rdvs = rdvs.order_by(RendezVous.date_rdv.desc(), RendezVous.heure_rdv.desc()).all()
    return render_template('rdvs.html', rdvs=rdvs, title="Historique des rendez-vous", is_historique=True)

@main.route("/rdv/valider/<int:rdv_id>", methods=['POST'])
@login_required
def valider_rdv(rdv_id):
    if current_user.role != 'Medecin': return redirect(url_for('main.dashboard'))
    rdv = RendezVous.query.get_or_404(rdv_id)
    rdv.statut = 'Programmé'
    db.session.commit()
    envoyer_notification(rdv.patient, f"RDV confirmé pour le {rdv.date_rdv.strftime('%d/%m/%Y')}.")
    return redirect(url_for('main.list_rdvs'))

@main.route("/rdv/refuser/<int:rdv_id>", methods=['POST'])
@login_required
def refuser_rdv(rdv_id):
    if current_user.role != 'Medecin': return redirect(url_for('main.dashboard'))
    rdv = RendezVous.query.get_or_404(rdv_id)
    rdv.statut = 'Annulé'
    db.session.commit()
    envoyer_notification(rdv.patient, f"Demande refusée.")
    return redirect(url_for('main.list_rdvs'))

@main.route("/rdv/nouveau", methods=['GET', 'POST'])
@login_required
def nouveau_rdv():
    if current_user.role not in ['Administrateur', 'Receptionniste', 'Patient']: return redirect(url_for('main.dashboard'))
    form = RDVForm()
    form.patient_id.choices = [(p.id, f"{p.prenom} {p.nom}") for p in Patient.query.all()]
    form.centre_id.choices = [(0, 'Aucun')] + [(c.id, c.nom_centre) for c in Centre.query.all()]
    form.service_id.choices = [(s.id, s.nom_service) for s in Service.query.all()]
    form.medecin_id.choices = [(m.id, f"Dr {m.prenom} {m.nom}") for m in Medecin.query.all()]
    if form.validate_on_submit():
        today = datetime.now().date()
        existing = RendezVous.query.filter(RendezVous.patient_id == form.patient_id.data, RendezVous.date_rdv == today, RendezVous.statut.notin_(['Terminé', 'Annulé'])).first()
        rdv_statut = 'Urgence' if request.args.get('statut') == 'Urgence' else ('En attente validation' if current_user.role == 'Patient' else 'Programmé')
        ctr_id = form.centre_id.data if form.centre_id.data != 0 else None
        if existing:
            existing.medecin_id, existing.service_id, existing.centre_id, existing.heure_rdv, existing.statut = form.medecin_id.data, form.service_id.data, ctr_id, form.heure_rdv.data, rdv_statut
            target_med = Medecin.query.get(form.medecin_id.data)
            envoyer_notification(target_med, f"Mise à jour du RDV de {existing.patient.prenom} {existing.patient.nom}")
        else:
            new_rdv_obj = RendezVous(patient_id=form.patient_id.data, medecin_id=form.medecin_id.data, service_id=form.service_id.data, centre_id=ctr_id, date_rdv=form.date_rdv.data, heure_rdv=form.heure_rdv.data, type_rdv=form.type_rdv.data, priorite=form.priorite.data, degre_urgence=form.degre_urgence.data, statut=rdv_statut)
            db.session.add(new_rdv_obj)
            db.session.commit()
            target_med = Medecin.query.get(form.medecin_id.data)
            patient_obj = Patient.query.get(form.patient_id.data)
            envoyer_notification(target_med, f"Nouveau RDV assigné : {patient_obj.prenom} {patient_obj.nom}")
        db.session.commit()
        return redirect(url_for('main.list_rdvs'))
    return render_template('rdv_form.html', form=form, title='Nouveau RDV')

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
        db.session.add(med); db.session.commit()
        db.session.add(Utilisateur(username=form.username.data, password=hashed_pass, role='Medecin', medecin_id=med.id))
        db.session.commit()
        return redirect(url_for('main.list_medecins'))
    return render_template('admin/medecin_form.html', form=form, title='Nouveau Médecin')

@main.route("/admin/medecin/modifier/<int:med_id>", methods=['GET', 'POST'])
@login_required
def modifier_medecin(med_id):
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    med = Medecin.query.get_or_404(med_id)
    form = MedecinForm(obj=med)
    form.service_id.choices = [(s.id, s.nom_service) for s in Service.query.all()]
    form.centre_id.choices = [(c.id, c.nom_centre) for c in Centre.query.all()]
    if form.validate_on_submit():
        med.nom, med.prenom, med.specialite, med.service_id, med.centre_id = form.nom.data, form.prenom.data, form.specialite.data, form.service_id.data, form.centre_id.data
        db.session.commit()
        return redirect(url_for('main.list_medecins'))
    return render_template('admin/medecin_form.html', form=form, title='Modifier Médecin')

@main.route("/admin/assurances")
@login_required
def list_assurances():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    return render_template('admin/assurances.html', assurances=Assurance.query.all())

@main.route("/admin/assurance/nouvelle", methods=['GET', 'POST'])
@login_required
def nouvelle_assurance():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    form = AssuranceForm, UrgenceForm()
    if form.validate_on_submit():
        db.session.add(Assurance(nom_assurance=form.nom_assurance.data, taux_pec=form.taux_pec.data, plafond_annuel=form.plafond_annuel.data))
        db.session.commit()
        return redirect(url_for('main.list_assurances'))
    return render_template('admin/assurance_form.html', form=form, title='Nouvelle Assurance')

@main.route("/admin/rapports")
@login_required
def rapports():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    rdv_stats = db.session.query(RendezVous.statut, db.func.count(RendezVous.id)).group_by(RendezVous.statut).all()
    rev_stats = db.session.query(db.func.strftime('%Y-%m', Facture.date_facture), db.func.sum(Facture.montant_total)).group_by(db.func.strftime('%Y-%m', Facture.date_facture)).limit(6).all()
    gender_stats = db.session.query(Patient.sexe, db.func.count(Patient.id)).group_by(Patient.sexe).all()
    return render_template('admin/rapports.html', rdv_labels=[s[0] for s in rdv_stats], rdv_data=[s[1] for s in rdv_stats], rev_labels=[s[0] for s in rev_stats], rev_data=[s[1] for s in rev_stats], gender_labels=[('M' if s[0]=='M' else 'F') for s in gender_stats], gender_data=[s[1] for s in gender_stats])

@main.route("/admin/utilisateurs")
@login_required
def list_utilisateurs():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    users = Utilisateur.query.all()
    return render_template('admin/utilisateurs.html', users=users)

@main.route("/admin/utilisateur/nouveau", methods=['GET', 'POST'])
@login_required
def nouveau_utilisateur():
    if current_user.role != 'Administrateur': return redirect(url_for('main.dashboard'))
    form = UtilisateurForm()
    if form.validate_on_submit():
        # Vérification proactive
        existing_user = Utilisateur.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash(f"Le nom d'utilisateur '{form.username.data}' est déjà pris.", 'danger')
            return render_template('admin/utilisateur_form.html', form=form, title='Nouvel Utilisateur')

        hashed_pass = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = Utilisateur(username=form.username.data, password=hashed_pass, role=form.role.data)
        db.session.add(user)
        try:
            db.session.commit()
            flash('Nouvel utilisateur créé.', 'success')
            return redirect(url_for('main.list_utilisateurs'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", 'danger')
    return render_template('admin/utilisateur_form.html', form=form, title='Nouvel Utilisateur')

@main.route("/consultation/nouvelle/<int:rdv_id>", methods=['GET', 'POST'])
@login_required
def nouvelle_consultation(rdv_id):
    if current_user.role != 'Medecin': return redirect(url_for('main.dashboard'))
    rdv = RendezVous.query.get_or_404(rdv_id)
    form = ConsultationForm()
    if form.validate_on_submit():
        c = Consultation(rdv_id=rdv.id, diagnostic=form.diagnostic.data, observations=form.observations.data)
        rdv.statut = 'Terminé'
        db.session.add(c); db.session.commit()
        db.session.add(Facture(consultation_id=c.id, montant_total=10000.0))
        db.session.commit()
        for caissier in Utilisateur.query.filter_by(role='Caissier').all(): envoyer_notification(caissier, "Facture prête.")
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
    form.medicament_id.choices = [(m.id, f"{m.nom_medicament} ({m.forme})") for m in Medicament.query.all()]
    if form.validate_on_submit():
        med = Medicament.query.get(form.medicament_id.data)
        
        # --- NOUVEAU : Contrôle des Interactions (RG13) ---
        conflit_bloquant = False
        for ligne in ord.lignes:
            interaction = Interaction.query.filter(
                ((Interaction.medicament_a_id == med.id) & (Interaction.medicament_b_id == ligne.medicament_id)) |
                ((Interaction.medicament_a_id == ligne.medicament_id) & (Interaction.medicament_b_id == med.id))
            ).first()
            
            if interaction:
                if interaction.niveau_risque == 'Élevé':
                    flash(f"BLOCAGE DE SÉCURITÉ : {med.nom_medicament} est incompatible avec {ligne.medicament.nom_medicament} (Risque Élevé). {interaction.description}", "danger")
                    conflit_bloquant = True
                    break
                else:
                    flash(f"AVERTISSEMENT : Risque {interaction.niveau_risque} entre {med.nom_medicament} et {ligne.medicament.nom_medicament}. {interaction.description}", "warning")
        
        if conflit_bloquant:
            return redirect(url_for('main.gestion_ordonnance', consult_id=consult_id))
        # --------------------------------------------------

        lots = LotMedicament.query.filter(LotMedicament.medicament_id == med.id, LotMedicament.qte_restante > 0).order_by(LotMedicament.date_expiration.asc()).all()
        if sum(l.qte_restante for l in lots) < form.quantite.data: flash('Stock insuffisant.', 'danger')
        else:
            qte = form.quantite.data
            for lot in lots:
                if qte <= 0: break
                if lot.qte_restante >= qte: lot.qte_restante -= qte; qte = 0
                else: qte -= lot.qte_restante; lot.qte_restante = 0
            db.session.add(LigneOrdonnance(ordonnance_id=ord.id, medicament_id=med.id, posologie=form.posologie.data, duree=form.duree.data, quantite=form.quantite.data))
            db.session.commit()
            for phar in Utilisateur.query.filter_by(role='Pharmacien').all():
                envoyer_notification(phar, f'Nouvelle prescription : {med.nom_medicament}')
                if med.total_stock <= med.seuil_alerte:
                    envoyer_notification(phar, f'ALERTE STOCK : {med.nom_medicament} ({med.total_stock} restants)')
            flash('Ajouté.', 'success')
    return render_template('ordonnance_form.html', form=form, ordonnance=ord, consultation=consult)

@main.route("/pharmacie/inventaire")
@login_required
def pharmacie_inventaire():
    if current_user.role not in ['Pharmacien', 'Administrateur']: return redirect(url_for('main.dashboard'))
    medicaments = Medicament.query.all()
    return render_template('pharmacie.html', medicaments=medicaments, alert_meds=[m.nom_medicament for m in medicaments if m.total_stock <= m.seuil_alerte])

@main.route("/pharmacie/medicament/nouveau", methods=['GET', 'POST'])
@login_required
def nouveau_medicament():
    if current_user.role not in ['Pharmacien', 'Administrateur']: return redirect(url_for('main.dashboard'))
    form = MedicamentForm()
    if form.validate_on_submit():
        nom = form.nom_medicament.data.strip().lower()
        med = Medicament.query.filter(db.func.lower(Medicament.nom_medicament) == nom, db.func.lower(Medicament.forme) == form.forme.data.lower(), db.func.lower(Medicament.dosage) == form.dosage.data.lower()).first()
        if med: med.seuil_alerte = form.seuil_alerte.data
        else:
            med = Medicament(nom_medicament=form.nom_medicament.data.strip(), forme=form.forme.data.strip(), dosage=form.dosage.data.strip(), seuil_alerte=form.seuil_alerte.data)
            db.session.add(med); db.session.commit()
        if form.quantite_a_ajouter.data > 0: db.session.add(LotMedicament(medicament_id=med.id, qte_initiale=form.quantite_a_ajouter.data, qte_restante=form.quantite_a_ajouter.data, date_expiration=datetime.now().date()))
        db.session.commit(); return redirect(url_for('main.pharmacie_inventaire'))
    return render_template('medicament_form.html', form=form, title='Ajouter au Stock')

@main.route("/pharmacie/ordonnances")
@login_required
def pharmacie_ordonnances():
    if current_user.role not in ['Pharmacien', 'Administrateur']: return redirect(url_for('main.dashboard'))
    return render_template('pharmacie/ordonnances_list.html', ordonnances=Ordonnance.query.all())

@main.route("/pdf/dossier/<int:patient_id>")
@login_required
def pdf_dossier(patient_id):
    p = Patient.query.get_or_404(patient_id)
    if current_user.role == 'Receptionniste': return redirect(url_for('main.dashboard'))
    return generate_dossier_pdf(p)

@main.route("/pdf/facture/<int:facture_id>")
@login_required
def pdf_facture(facture_id):
    return generate_facture_pdf(Facture.query.get_or_404(facture_id))

@main.route("/pdf/ordonnance/<int:ordonnance_id>")
@login_required
def pdf_ordonnance(ordonnance_id):
    return generate_ordonnance_pdf(Ordonnance.query.get_or_404(ordonnance_id))

@main.route("/reception/file-attente")
@login_required
def file_attente():
    if current_user.role not in ['Receptionniste', 'Administrateur']: return redirect(url_for('main.dashboard'))
    today = datetime.now().date()
    rdvs = RendezVous.query.filter(RendezVous.date_rdv == today, RendezVous.statut.notin_(['Terminé', 'Annulé'])).order_by(RendezVous.priorite.desc(), RendezVous.heure_rdv).all()
    return render_template('reception/file.html', rdvs=rdvs)

@main.route("/rdv/arriver/<int:rdv_id>")
@login_required
def marquer_arrive(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id); rdv.statut = 'En attente'; db.session.commit(); return redirect(url_for('main.file_attente'))

@main.route("/rdv/annuler/<int:rdv_id>", methods=['POST'])
@login_required
def annuler_rdv(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id); rdv.statut = 'Annulé'; db.session.commit();
    for recep in Utilisateur.query.filter_by(role='Receptionniste').all(): envoyer_notification(recep, f'RDV annulé : {rdv.patient.prenom} {rdv.patient.nom}');
    return redirect(url_for('main.list_rdvs'))

@main.route("/rdv/modifier/<int:rdv_id>", methods=['GET', 'POST'])
@login_required
def modifier_rdv(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id); form = RDVForm(obj=rdv)
    form.patient_id.choices = [(p.id, f"{p.prenom} {p.nom}") for p in Patient.query.all()]
    form.centre_id.choices = [(0, 'Aucun')] + [(c.id, c.nom_centre) for c in Centre.query.all()]
    form.service_id.choices = [(s.id, s.nom_service) for s in Service.query.all()]
    form.medecin_id.choices = [(m.id, f"Dr {m.prenom} {m.nom}") for m in Medecin.query.all()]
    if form.validate_on_submit():
        rdv.patient_id, rdv.medecin_id, rdv.date_rdv, rdv.heure_rdv, rdv.priorite, rdv.type_rdv, rdv.service_id = form.patient_id.data, form.medecin_id.data, form.date_rdv.data, form.heure_rdv.data, form.priorite.data, form.type_rdv.data, form.service_id.data
        rdv.centre_id = form.centre_id.data if form.centre_id.data != 0 else None
        db.session.commit()
        # Notifier le médecin et le patient du changement
        envoyer_notification(rdv.medecin, f"Mise à jour RDV : {rdv.patient.prenom} le {rdv.date_rdv.strftime('%d/%m')}")
        envoyer_notification(rdv.patient, f"Votre RDV a été modifié par la réception.")
        return redirect(url_for('main.file_attente'))
    return render_template('rdv_form.html', form=form, title='Modifier RDV')

@main.route("/caisse/factures")
@login_required
def caisse_factures():
    if current_user.role not in ['Caissier', 'Administrateur']: return redirect(url_for('main.dashboard'))
    return render_template('caisse/factures.html', factures=Facture.query.order_by(Facture.date_facture.desc()).all())

@main.route("/caisse/payer/<int:facture_id>", methods=['POST'])
@login_required
def caisse_payer(facture_id):
    f = Facture.query.get_or_404(facture_id); montant = request.form.get('montant_paye', type=float)
    if montant:
        f.montant_paye = (f.montant_paye or 0) + montant
        f.statut = 'Payée' if f.montant_paye >= f.montant_total else 'Partielle'
        db.session.commit()
    return redirect(url_for('main.caisse_factures'))

@main.route("/caisse/recherche", methods=['GET'])
@login_required
def caisse_recherche():
    fid = request.args.get('facture_id')
    if fid:
        f = Facture.query.get(fid)
        if f: return redirect(url_for('main.caisse_factures') + f'#payModal{f.id}')
        flash('Non trouvée.', 'danger')
    return redirect(url_for('main.caisse_factures'))

@main.route("/notifications/marquer-lu", methods=['POST'])
@login_required
def marquer_notifications_lues():
    for notif in current_user.notifications: notif.lu = True
    db.session.commit(); return redirect(request.referrer or url_for('main.dashboard'))

@main.app_context_processor
def inject_notifications():
    if current_user.is_authenticated: return dict(unread_notifications=[n for n in current_user.notifications if not n.lu])
    return dict(unread_notifications=[])


@main.route("/reception/admission-urgence", methods=['GET', 'POST'])
@login_required
def admission_urgence():
    if current_user.role not in ['Administrateur', 'Receptionniste']:
        return redirect(url_for('main.dashboard'))
        
    form = UrgenceForm()
    form.patient_id.choices = [(0, '-- Choisir un patient existant --')] + [(p.id, f"{p.prenom} {p.nom}") for p in Patient.query.all()]
    form.service_id.choices = [(s.id, s.nom_service) for s in Service.query.all()]
    form.medecin_id.choices = [(m.id, f"Dr {m.prenom} {m.nom}") for m in Medecin.query.all()]

    if form.validate_on_submit():
        patient_id = form.patient_id.data
        if patient_id == 0:
            if not form.nom_nouveau.data or not form.prenom_nouveau.data:
                flash("Saisie incomplete pour nouveau patient.", "danger")
                return render_template('urgence_form.html', form=form)
            new_p = Patient(nom=form.nom_nouveau.data, prenom=form.prenom_nouveau.data, date_naissance=datetime.now().date(), sexe=form.sexe_nouveau.data)
            db.session.add(new_p); db.session.commit()
            patient_id = new_p.id
            db.session.add(DossierMedical(patient_id=patient_id)); db.session.commit()
        
        now = datetime.now()
        rdv = RendezVous(patient_id=patient_id, medecin_id=form.medecin_id.data, service_id=form.service_id.data, date_rdv=now.date(), heure_rdv=now.time(), statut='Urgence', priorite=3, degre_urgence='Critique')
        db.session.add(rdv); db.session.commit()
        envoyer_notification(rdv.medecin, f"ALERTE : Urgence vitale ! ({rdv.patient.nom})")
        flash("URGENCE ENREGISTRÉE.", "danger")
        return redirect(url_for('main.list_rdvs'))
    return render_template('urgence_form.html', form=form, title="Admission d'Urgence")

@main.route("/logout")
def logout():
    logout_user(); return redirect(url_for('main.login'))
