from flask import Blueprint, render_template, url_for, flash, redirect, request
from app import db
from app.models import RendezVous, Service, Medecin
from flask_login import login_required, current_user

transfert_bp = Blueprint('transfert', __name__)

@transfert_bp.route("/rdv/transfert/<int:rdv_id>", methods=['GET', 'POST'])
@login_required
def transfere_rdv(rdv_id):
    if current_user.role not in ['Medecin', 'Administrateur']:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    rdv = RendezVous.query.get_or_404(rdv_id)
    
    if request.method == 'POST':
        new_service_id = request.form.get('service_id')
        new_medecin_id = request.form.get('medecin_id')
        
        rdv.service_id = new_service_id
        rdv.medecin_id = new_medecin_id
        db.session.commit()
        
        flash('Patient transféré avec succès.', 'success')
        return redirect(url_for('main.list_rdvs'))
        
    services = Service.query.all()
    # On devrait charger les médecins dynamiquement en JS, mais pour simplifier ici :
    medecins = Medecin.query.all()
    
    return render_template('transfert.html', rdv=rdv, services=services, medecins=medecins)
