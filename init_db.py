from app import create_app, db, bcrypt
from app.models import Utilisateur, Service, Centre, Medecin, Medicament, Patient, Assurance, LotMedicament, Interaction
from datetime import date

app = create_app()

def init_db():
    with app.app_context():
        db.create_all()
        
        if not Utilisateur.query.filter_by(username='admin').first():
            # ... (admin code remains same or slightly adjusted for clarity)
            admin_pass = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = Utilisateur(username='admin', password=admin_pass, role='Administrateur')
            db.session.add(admin)

            recep_pass = bcrypt.generate_password_hash('recep123').decode('utf-8')
            receptionniste = Utilisateur(username='reception', password=recep_pass, role='Receptionniste')
            db.session.add(receptionniste)
            
            # 1. Add Assurances
            as1 = Assurance(nom_assurance='IPM Dakar', taux_pec=80.0)
            as2 = Assurance(nom_assurance='AXA Santé', taux_pec=70.0)
            db.session.add_all([as1, as2])
            db.session.commit()

            # 2. Add Services & Centre
            s1 = Service(nom_service='Pédiatrie', description='Soins pour enfants')
            s2 = Service(nom_service='Généraliste', description='Médecine générale')
            c1 = Centre(nom_centre='Centre A', adresse='Dakar, Plateau', telephone='338000000')
            db.session.add_all([s1, s2, c1])
            db.session.commit()

            # 3. Add Medecin
            medecin = Medecin(nom='Diop', prenom='Moussa', specialite='Pédiatrie', service_id=s1.id, telephone='770000000', teleconsult_active=True)
            db.session.add(medecin)
            db.session.commit()
            
            doc_pass = bcrypt.generate_password_hash('doc123').decode('utf-8')
            doctor_user = Utilisateur(username='docteur', password=doc_pass, role='Medecin', medecin_id=medecin.id)
            db.session.add(doctor_user)

            # 4. Add Pharmacien
            ph_pass = bcrypt.generate_password_hash('pharma123').decode('utf-8')
            pharmacien = Utilisateur(username='pharmacien', password=ph_pass, role='Pharmacien')
            db.session.add(pharmacien)

            # 5. Add Patient test
            pat = Patient(nom='Sow', prenom='Abdoulaye', date_naissance=date(1995, 5, 20), sexe='M', telephone='771234567', assurance_id=as1.id)
            db.session.add(pat)
            db.session.commit()
            
            pat_pass = bcrypt.generate_password_hash('patient123').decode('utf-8')
            patient_user = Utilisateur(username='patient', password=pat_pass, role='Patient', patient_id=pat.id)
            db.session.add(patient_user)

            # 6. Add Medications & Lots
            m1 = Medicament(nom_medicament='Paracétamol', forme='Comprimé', dosage='500mg', seuil_alerte=50)
            m2 = Medicament(nom_medicament='Amoxicilline', forme='Gélule', dosage='1g', seuil_alerte=20)
            db.session.add_all([m1, m2])
            db.session.commit()

            l1 = LotMedicament(medicament_id=m1.id, date_expiration=date(2027, 12, 31), qte_initiale=100, qte_restante=85)
            l2 = LotMedicament(medicament_id=m2.id, date_expiration=date(2026, 6, 30), qte_initiale=50, qte_restante=5) # Stock bas
            db.session.add_all([l1, l2])

            # 7. Add Interaction for demo
            inter = Interaction(medicament_a_id=m1.id, medicament_b_id=m2.id, niveau_risque='Modéré', description='Risque accru de maux d\'estomac.')
            db.session.add(inter)

            db.session.commit()
            print("Base de données initialisée avec TOUS les rôles (Admin, Medecin, Patient, Pharmacien, Reception).")
        else:
            print("L'utilisateur admin existe déjà.")

if __name__ == '__main__':
    init_db()
