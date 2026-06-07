from fpdf import FPDF
from flask import send_file, current_app
import os
import uuid

class PDF(FPDF):
    def header(self):
        # Senegal Flag Colors in Header
        self.set_fill_color(0, 133, 63)  # Green
        self.rect(0, 0, 70, 5, 'F')
        self.set_fill_color(253, 239, 66) # Yellow
        self.rect(70, 0, 70, 5, 'F')
        
        # Star: Geometric drawing (polygon) to avoid Unicode issues
        # Center approx (105, 2.5)
        self.set_fill_color(0, 133, 63) # Star color (Green)
        # Simplified star polygon points (relative to center 105, 2.5)
        # Note: FPDF coordinates are absolute
        cx, cy = 105, 2.5
        star_points = [
            [cx, cy - 2],    # Top
            [cx + 0.5, cy - 0.5], 
            [cx + 2, cy - 0.5],
            [cx + 0.8, cy + 0.5],
            [cx + 1.2, cy + 1.8],
            [cx, cy + 1],
            [cx - 1.2, cy + 1.8],
            [cx - 0.8, cy + 0.5],
            [cx - 2, cy - 0.5],
            [cx - 0.5, cy - 0.5]
        ]
        self.polygon(star_points, style='F')
        
        self.set_fill_color(227, 27, 35)  # Red
        self.rect(140, 0, 70, 5, 'F')
        
        self.set_font('helvetica', 'B', 15)
        self.ln(10)
        self.cell(0, 10, 'REPUBLIQUE DU SENEGAL', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 5, 'Ministère de la Santé et de l\'Action Sociale', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(10)

def generate_facture_pdf(facture):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, f'FACTURE N° {facture.id}', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    
    patient = facture.consultation.rdv.patient
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 10, f'Patient: {patient.prenom} {patient.nom}', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f'Date: {facture.date_facture.strftime("%d/%m/%Y")}', new_x="LMARGIN", new_y="NEXT")
    
    pec_taux = 0
    assurance_nom = "Aucune"
    if patient.assurance:
        pec_taux = patient.assurance.taux_pec
        assurance_nom = patient.assurance.nom_assurance
        pdf.cell(0, 10, f'Assurance: {assurance_nom} (PEC: {pec_taux}%)', new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(10)
    
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(100, 10, 'Description', border=1)
    pdf.cell(0, 10, 'Montant (CFA)', border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('helvetica', '', 12)
    pdf.cell(100, 10, f'Consultation {facture.consultation.type_consult or "Générale"}', border=1)
    pdf.cell(0, 10, f'{facture.montant_total}', border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    pec_montant = (facture.montant_total * pec_taux) / 100
    reste_a_payer = facture.montant_total - pec_montant
    
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(100, 10, 'Total Brut:', align='R')
    pdf.cell(0, 10, f'{facture.montant_total} CFA', align='R', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('helvetica', 'I', 12)
    pdf.cell(100, 10, f'Prise en charge {assurance_nom}:', align='R')
    pdf.cell(0, 10, f'- {pec_montant} CFA', align='R', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(227, 27, 35) # Red for total
    pdf.cell(100, 10, 'NET A PAYER:', align='R')
    pdf.cell(0, 10, f'{reste_a_payer} CFA', align='R', new_x="LMARGIN", new_y="NEXT")
    
    filename = f"facture_{facture.id}_{uuid.uuid4().hex}.pdf"
    filepath = os.path.join(current_app.root_path, 'static', 'exports', filename)
    pdf.output(filepath)
    
    return send_file(filepath, as_attachment=True)

def generate_ordonnance_pdf(ordonnance):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'ORDONNANCE MEDICALE', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(0, 10, f'Date: {ordonnance.date_ordonnance.strftime("%d/%m/%Y")}', new_x="LMARGIN", new_y="NEXT", align='R')
    
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, f'Patient: {ordonnance.consultation.rdv.patient.prenom} {ordonnance.consultation.rdv.patient.nom}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    pdf.set_font('helvetica', 'I', 14)
    pdf.cell(0, 10, 'Prescriptions:', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font('helvetica', '', 12)
    for ligne in ordonnance.lignes:
        pdf.cell(0, 10, f'- {ligne.medicament.nom_medicament} ({ligne.medicament.dosage})', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('helvetica', 'I', 10)
        pdf.cell(0, 5, f'  Posologie: {ligne.posologie} pendant {ligne.duree}', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.set_font('helvetica', '', 12)
        
    pdf.ln(30)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, f'Dr {ordonnance.consultation.rdv.medecin.nom}', align='R', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, 'Cachet et Signature', align='R', new_x="LMARGIN", new_y="NEXT")
    
    filename = f"ordonnance_{ordonnance.id}_{uuid.uuid4().hex}.pdf"
    filepath = os.path.join(current_app.root_path, 'static', 'exports', filename)
    pdf.output(filepath)
    
    return send_file(filepath, as_attachment=True)

def generate_dossier_pdf(patient):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'DOSSIER MEDICAL COMPLET', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)
    
    # Patient Info
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, ' INFORMATIONS DU PATIENT', new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font('helvetica', '', 12)
    pdf.cell(100, 10, f'Nom complet: {patient.prenom} {patient.nom}')
    pdf.cell(0, 10, f'Sexe: {patient.sexe}', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(100, 10, f'Date de naissance: {patient.date_naissance.strftime("%d/%m/%Y")}')
    pdf.cell(0, 10, f'Téléphone: {patient.telephone}', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f'Assurance: {patient.assurance.nom_assurance if patient.assurance else "Aucune"}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Medical Alerts
    pdf.set_fill_color(255, 200, 200)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, ' ALERTES MEDICALES', new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font('helvetica', '', 12)
    
    if patient.dossier:
        allergies = patient.dossier.allergies or "Néant"
        antecedents = patient.dossier.antecedents or "Néant"
    else:
        allergies = "Néant"
        antecedents = "Néant"
        
    pdf.ln(2)
    pdf.multi_cell(0, 10, f'Allergies: {allergies}', new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 10, f'Antecedents: {antecedents}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # History
    pdf.set_fill_color(200, 255, 200)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, ' HISTORIQUE DES CONSULTATIONS', new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    for rdv in patient.rdvs:
        if rdv.consultation:
            pdf.set_font('helvetica', 'B', 11)
            pdf.cell(0, 10, f'Date: {rdv.consultation.date_consultation.strftime("%d/%m/%Y")} - Dr {rdv.medecin.nom}', new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('helvetica', 'I', 11)
            pdf.multi_cell(0, 7, f'Diagnostic: {rdv.consultation.diagnostic or "Aucun"}', new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('helvetica', '', 10)
            pdf.multi_cell(0, 7, f'Observations: {rdv.consultation.observations or "Aucune"}', new_x="LMARGIN", new_y="NEXT")
            
            if rdv.consultation.ordonnance:
                pdf.set_font('helvetica', 'B', 10)
                pdf.cell(0, 7, 'Prescriptions:', new_x="LMARGIN", new_y="NEXT")
                pdf.set_font('helvetica', '', 10)
                for ligne in rdv.consultation.ordonnance.lignes:
                    pdf.cell(0, 5, f'  - {ligne.medicament.nom_medicament} ({ligne.medicament.dosage}): {ligne.posologie}', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
            pdf.cell(0, 0, '', 'T', new_x="LMARGIN", new_y="NEXT") # Divider line
            pdf.ln(2)

    filename = f"dossier_{patient.id}_{uuid.uuid4().hex}.pdf"
    filepath = os.path.join(current_app.root_path, 'static', 'exports', filename)
    pdf.output(filepath)
    
    return send_file(filepath, as_attachment=True)

def envoyer_notification(utilisateur_cible, message):
    """
    Enregistre une notification en base de données pour un utilisateur spécifique.
    `utilisateur_cible` peut être un objet Utilisateur ou un patient/médecin possédant un compte.
    """
    from app.models import Notification, Utilisateur
    from app import db
    
    user = None
    if isinstance(utilisateur_cible, Utilisateur):
        user = utilisateur_cible
    elif hasattr(utilisateur_cible, 'user'):
        u_attr = utilisateur_cible.user
        if isinstance(u_attr, list) and len(u_attr) > 0:
            user = u_attr[0]
        else:
            user = u_attr
    
    if not user:
        # Recherche directe en base si c'est un Medecin ou Patient
        from app.models import Medecin, Patient
        if isinstance(utilisateur_cible, Medecin):
            user = Utilisateur.query.filter_by(medecin_id=utilisateur_cible.id).first()
        elif isinstance(utilisateur_cible, Patient):
            user = Utilisateur.query.filter_by(patient_id=utilisateur_cible.id).first()
    
    if user:
        new_notif = Notification(user_id=user.id, message=message)
        db.session.add(new_notif)
        db.session.commit()
        print(f"NOTIFICATION PERSISTEE [User: {user.username}]: {message}")
    else:
        print(f"ALERTE: Impossible d'envoyer une notification à {utilisateur_cible} (compte utilisateur introuvable).")

