# app/web/suppliers.py
"""
Lieferanten-Modul für Automaten Manager
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, desc
from app import db
from app.models import Supplier, Refill, RefillItem, Product
suppliers_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')

# Import render_modern_template am Ende der Datei


@suppliers_bp.route('/')
@login_required
def index():
    """Lieferanten-Übersicht"""
    suppliers = Supplier.query.filter_by(user_id=current_user.id).all()

    # Statistiken für jeden Lieferanten berechnen
    supplier_stats = []
    for supplier in suppliers:
        refills = Refill.query.filter_by(
            supplier_id=supplier.id,
            user_id=current_user.id
        ).all()

        total_orders = len(refills)
        total_amount = sum(r.total_amount for r in refills) if refills else 0

        # Letzte Bestellung
        last_order = Refill.query.filter_by(
            supplier_id=supplier.id,
            user_id=current_user.id
        ).order_by(Refill.date.desc()).first()

        # Top-Produkte von diesem Lieferanten
        top_products = db.session.query(
            Product.name,
            func.sum(RefillItem.quantity).label('total_quantity'),
            func.sum(RefillItem.total_price).label('total_spent')
        ).join(
            RefillItem, RefillItem.product_id == Product.id
        ).join(
            Refill, RefillItem.refill_id == Refill.id
        ).filter(
            Refill.supplier_id == supplier.id,
            Refill.user_id == current_user.id
        ).group_by(Product.id, Product.name).order_by(
            desc('total_spent')
        ).limit(3).all()

        supplier_stats.append({
            'supplier': supplier,
            'total_orders': total_orders,
            'total_amount': total_amount,
            'last_order': last_order.date if last_order else None,
            'top_products': top_products
        })

    # JavaScript
    extra_scripts = """
    <script>
    function editSupplier(id, name, contact, email, phone, address, notes) {
        document.getElementById('edit_supplier_id').value = id;
        document.getElementById('edit_name').value = name;
        document.getElementById('edit_contact_person').value = contact || '';
        document.getElementById('edit_email').value = email || '';
        document.getElementById('edit_phone').value = phone || '';
        document.getElementById('edit_address').value = address || '';
        document.getElementById('edit_notes').value = notes || '';

        new bootstrap.Modal(document.getElementById('editSupplierModal')).show();
    }

    function deleteSupplier(id, name) {
        if (confirm(`Möchten Sie den Lieferanten "${name}" wirklich löschen?`)) {
            fetch(`/suppliers/delete/${id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            }).then(response => {
                if (response.ok) {
                    window.location.reload();
                }
            });
        }
    }

    function viewSupplierDetails(id) {
        window.location.href = `/suppliers/details/${id}`;
    }
    </script>
    """

    # CSS
    extra_css = """
    <style>
        .supplier-card {
            transition: transform 0.2s;
            cursor: pointer;
            height: 100%;
        }

        .supplier-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .stat-box {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2c3e50;
        }

        .stat-label {
            color: #6c757d;
            font-size: 0.9rem;
        }

        .top-product {
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 5px;
            margin: 2px 0;
            font-size: 0.85rem;
        }

        .action-buttons {
            position: absolute;
            top: 10px;
            right: 10px;
        }
    </style>
    """

    # HTML
    content = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-truck"></i> Lieferanten
        </h2>
        <button class="btn btn-light" data-bs-toggle="modal" data-bs-target="#addSupplierModal">
            <i class="bi bi-plus-circle"></i> Neuer Lieferant
        </button>
    </div>

    <!-- Übersichtskarten -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <h6>Anzahl Lieferanten</h6>
                    <h3>""" + str(len(suppliers)) + """</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <h6>Gesamt-Umsatz</h6>
                    <h3>""" + f"{sum(s['total_amount'] for s in supplier_stats):.2f} €" + """</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-info text-white">
                <div class="card-body">
                    <h6>Bestellungen gesamt</h6>
                    <h3>""" + str(sum(s['total_orders'] for s in supplier_stats)) + """</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-warning text-white">
                <div class="card-body">
                    <h6>Ø pro Bestellung</h6>
                    <h3>""" + (
        f"{sum(s['total_amount'] for s in supplier_stats) / sum(s['total_orders'] for s in supplier_stats):.2f} €" if sum(
            s['total_orders'] for s in supplier_stats) > 0 else "0.00 €") + """</h3>
                </div>
            </div>
        </div>
    </div>

    <!-- Lieferanten-Karten -->
    <div class="row">
    """

    for stat in supplier_stats:
        supplier = stat['supplier']
        content += f"""
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card supplier-card" onclick="viewSupplierDetails({supplier.id})">
                <div class="card-body position-relative">
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary" 
                                onclick="event.stopPropagation(); editSupplier({supplier.id}, '{supplier.name}', '{supplier.contact_person or ''}', '{supplier.email or ''}', '{supplier.phone or ''}', '{supplier.address or ''}', '{supplier.notes or ''}')"
                                title="Bearbeiten">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" 
                                onclick="event.stopPropagation(); deleteSupplier({supplier.id}, '{supplier.name}')"
                                title="Löschen">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>

                    <h5 class="card-title mb-3">
                        <i class="bi bi-building"></i> {supplier.name}
                    </h5>

                    <div class="row">
                        <div class="col-6">
                            <div class="stat-box text-center">
                                <div class="stat-value">{stat['total_orders']}</div>
                                <div class="stat-label">Bestellungen</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="stat-box text-center">
                                <div class="stat-value">{stat['total_amount']:.0f}€</div>
                                <div class="stat-label">Gesamtumsatz</div>
                            </div>
                        </div>
                    </div>

                    <div class="mt-3">
                        <small class="text-muted">
                            <i class="bi bi-calendar"></i> Letzte Bestellung: 
                            {stat['last_order'].strftime('%d.%m.%Y') if stat['last_order'] else 'Noch keine'}
                        </small>
                    </div>

                    <div class="mt-2">
                        <small class="text-muted">Top-Produkte:</small>
        """

        if stat['top_products']:
            for product in stat['top_products'][:3]:
                content += f"""
                        <div class="top-product">
                            {product.name}: {product.total_quantity:.0f} Stk - {product.total_spent:.2f} €
                        </div>
                """
        else:
            content += '<div class="text-muted small">Noch keine Bestellungen</div>'

        # Kontaktinfos
        if supplier.contact_person or supplier.phone or supplier.email:
            content += '<hr class="my-2">'

        if supplier.contact_person:
            content += f'<small><i class="bi bi-person"></i> {supplier.contact_person}</small><br>'
        if supplier.phone:
            content += f'<small><i class="bi bi-telephone"></i> {supplier.phone}</small><br>'
        if supplier.email:
            content += f'<small><i class="bi bi-envelope"></i> {supplier.email}</small>'

        content += """
                    </div>
                </div>
            </div>
        </div>
        """

    content += """
    </div>

    <!-- Neuer Lieferant Modal -->
    <div class="modal fade" id="addSupplierModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Neuer Lieferant</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/suppliers/add">
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Firmenname *</label>
                            <input type="text" name="name" class="form-control" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Ansprechpartner</label>
                            <input type="text" name="contact_person" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">E-Mail</label>
                            <input type="email" name="email" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Telefon</label>
                            <input type="text" name="phone" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Adresse</label>
                            <textarea name="address" class="form-control" rows="2"></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Notizen</label>
                            <textarea name="notes" class="form-control" rows="2"></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">Speichern</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Bearbeiten Modal -->
    <div class="modal fade" id="editSupplierModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Lieferant bearbeiten</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/suppliers/edit">
                    <input type="hidden" id="edit_supplier_id" name="supplier_id">
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Firmenname *</label>
                            <input type="text" id="edit_name" name="name" class="form-control" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Ansprechpartner</label>
                            <input type="text" id="edit_contact_person" name="contact_person" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">E-Mail</label>
                            <input type="email" id="edit_email" name="email" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Telefon</label>
                            <input type="text" id="edit_phone" name="phone" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Adresse</label>
                            <textarea id="edit_address" name="address" class="form-control" rows="2"></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Notizen</label>
                            <textarea id="edit_notes" name="notes" class="form-control" rows="2"></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">Änderungen speichern</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    """

    from app.web.dashboard_modern import render_modern_template
    
    # Kombiniere Content, Scripts und CSS
    full_content = extra_css + content + extra_scripts
    
    return render_modern_template(
        content=full_content,
        title='Lieferanten',
        active_module='inventory',
        active_submodule='suppliers',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
            {'text': 'Lieferanten'}
        ]
    )


@suppliers_bp.route('/add', methods=['POST'])
@login_required
def add_supplier():
    """Neuen Lieferanten hinzufügen"""
    try:
        supplier = Supplier(
            name=request.form.get('name'),
            contact_person=request.form.get('contact_person'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            notes=request.form.get('notes'),
            user_id=current_user.id
        )
        db.session.add(supplier)
        db.session.commit()
        flash(f'Lieferant "{supplier.name}" wurde angelegt!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/edit', methods=['POST'])
@login_required
def edit_supplier():
    """Lieferant bearbeiten"""
    try:
        supplier = Supplier.query.filter_by(
            id=request.form.get('supplier_id'),
            user_id=current_user.id
        ).first_or_404()

        supplier.name = request.form.get('name')
        supplier.contact_person = request.form.get('contact_person')
        supplier.email = request.form.get('email')
        supplier.phone = request.form.get('phone')
        supplier.address = request.form.get('address')
        supplier.notes = request.form.get('notes')

        db.session.commit()
        flash(f'Lieferant "{supplier.name}" wurde aktualisiert!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/delete/<int:supplier_id>', methods=['POST'])
@login_required
def delete_supplier(supplier_id):
    """Lieferant löschen"""
    try:
        supplier = Supplier.query.filter_by(
            id=supplier_id,
            user_id=current_user.id
        ).first_or_404()

        # Prüfen ob noch Bestellungen existieren
        refills = Refill.query.filter_by(supplier_id=supplier_id).count()
        if refills > 0:
            return jsonify({'error': f'Lieferant kann nicht gelöscht werden - {refills} Bestellungen vorhanden!'}), 400

        db.session.delete(supplier)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@suppliers_bp.route('/details/<int:supplier_id>')
@login_required
def supplier_details(supplier_id):
    """Detailansicht eines Lieferanten"""
    supplier = Supplier.query.filter_by(
        id=supplier_id,
        user_id=current_user.id
    ).first_or_404()

    # Alle Bestellungen von diesem Lieferanten
    refills = Refill.query.filter_by(
        supplier_id=supplier_id,
        user_id=current_user.id
    ).order_by(Refill.date.desc()).all()

    content = f"""
    <div class="container">
        <h2 class="text-white mb-4">
            <i class="bi bi-building"></i> {supplier.name}
        </h2>

        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>Kontaktdaten</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Ansprechpartner:</strong> {supplier.contact_person or '—'}</p>
                        <p><strong>E-Mail:</strong> {supplier.email or '—'}</p>
                        <p><strong>Telefon:</strong> {supplier.phone or '—'}</p>
                        <p><strong>Adresse:</strong><br>{supplier.address or '—'}</p>
                        <p><strong>Notizen:</strong><br>{supplier.notes or '—'}</p>
                    </div>
                </div>
            </div>

            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5>Bestellhistorie</h5>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Datum</th>
                                    <th>Rechnungsnr.</th>
                                    <th>Positionen</th>
                                    <th>Gesamt</th>
                                    <th>Aktionen</th>
                                </tr>
                            </thead>
                            <tbody>
    """

    for refill in refills:
        content += f"""
                                <tr>
                                    <td>{refill.date.strftime('%d.%m.%Y')}</td>
                                    <td>{refill.invoice_number or '—'}</td>
                                    <td>{refill.items.count()}</td>
                                    <td>{refill.total_amount:.2f} €</td>
                                    <td>
                                        <a href="/refills/view/{refill.id}" class="btn btn-sm btn-info">
                                            <i class="bi bi-eye"></i>
                                        </a>
                                    </td>
                                </tr>
        """

    content += """
                            </tbody>
                        </table>
                    </div>
                </div>

                <a href="/suppliers" class="btn btn-secondary mt-3">
                    <i class="bi bi-arrow-left"></i> Zurück zur Übersicht
                </a>
            </div>
        </div>
    </div>
    """

    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title=f'{supplier.name} - Details',
        active_module='inventory',
        active_submodule='suppliers',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
            {'text': 'Lieferanten', 'url': url_for('suppliers.index')},
            {'text': supplier.name}
        ]
    )