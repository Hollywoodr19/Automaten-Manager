# app/web/products.py
"""
Produkt-Verwaltung für Warenwirtschaft - Mit Mehrfach-Anlage
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from decimal import Decimal
from app import db
from app.models import Product, ProductUnit, ProductCategory, InventoryMovement
from app.web.navigation import render_with_base_new as render_with_base

products_bp = Blueprint('products', __name__, url_prefix='/products')


@products_bp.route('/')
@login_required
def index():
    """Produkt-Übersicht"""
    products = Product.query.filter_by(user_id=current_user.id).all()

    content = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-box"></i> Produkte
        </h2>
        <div>
            <button class="btn btn-outline-light me-2" data-bs-toggle="modal" data-bs-target="#bulkProductModal">
                <i class="bi bi-list-ul"></i> Mehrere Produkte anlegen
            </button>
            <button class="btn btn-light" data-bs-toggle="modal" data-bs-target="#productModal">
                <i class="bi bi-plus-circle"></i> Neues Produkt
            </button>
        </div>
    </div>

    <div class="row">
    """

    if products:
        for product in products:
            stock = product.get_current_stock()
            stock_status = 'success'
            if product.reorder_point and stock <= product.reorder_point:
                stock_status = 'warning'
            if stock <= 0:
                stock_status = 'danger'

            content += f"""
            <div class="col-md-4 mb-3">
                <div class="card">
                    <div class="card-body">
                        <h5>{product.name}</h5>
                        <p class="text-muted">{product.category.value if product.category else 'Keine Kategorie'}</p>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Bestand:</span>
                            <span class="badge bg-{stock_status}">{stock:.1f} {product.unit.value}</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Preis:</span>
                            <span>{product.default_price:.2f} € / {product.unit.value}</span>
                        </div>
                        <div class="btn-group btn-group-sm w-100">
                            <button class="btn btn-outline-primary" onclick="editProduct({product.id})">
                                <i class="bi bi-pencil"></i> Bearbeiten
                            </button>
                            <button class="btn btn-outline-danger" onclick="deleteProduct({product.id}, '{product.name}')">
                                <i class="bi bi-trash"></i> Löschen
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            """
    else:
        content += """
        <div class="col-12">
            <div class="card">
                <div class="card-body text-center py-5">
                    <i class="bi bi-inbox display-1 text-muted"></i>
                    <p class="mt-3">Noch keine Produkte vorhanden</p>
                    <div>
                        <button class="btn btn-outline-primary me-2" data-bs-toggle="modal" data-bs-target="#bulkProductModal">
                            <i class="bi bi-list-ul"></i> Mehrere Produkte anlegen
                        </button>
                        <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#productModal">
                            <i class="bi bi-plus"></i> Erstes Produkt anlegen
                        </button>
                    </div>
                </div>
            </div>
        </div>
        """

    content += """
    </div>

    <!-- Single Product Modal -->
    <div class="modal fade" id="productModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Neues Produkt anlegen</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/products/add">
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Name *</label>
                            <input type="text" name="name" class="form-control" required 
                                   placeholder="z.B. Kaffeebohnen Premium">
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Kategorie</label>
                                    <select name="category" class="form-select">
                                        <option value="kaffee">Kaffee</option>
                                        <option value="becher">Becher</option>
                                        <option value="zucker">Zucker</option>
                                        <option value="milch">Milch</option>
                                        <option value="snacks">Snacks</option>
                                        <option value="getraenke">Getränke</option>  <!-- OHNE Ä im value! -->
                                        <option value="sonstiges">Sonstiges</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Einheit</label>
                                    <select name="unit" class="form-select">
                                        <option value="kg">Kilogramm (kg)</option>
                                        <option value="piece">Stück</option>
                                        <option value="liter">Liter</option>
                                        <option value="pack">Packung</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Standard-Preis (€)</label>
                                    <input type="number" name="default_price" class="form-control" 
                                           step="0.01" placeholder="0.00">
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Nachbestellpunkt</label>
                                    <input type="number" name="reorder_point" class="form-control" 
                                           step="0.1" placeholder="10">
                                </div>
                            </div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Beschreibung</label>
                            <textarea name="description" class="form-control" rows="2"></textarea>
                        </div>
                    </div>

                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save"></i> Produkt speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Bulk Product Modal -->
    <div class="modal fade" id="bulkProductModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Mehrere Produkte anlegen</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/products/bulk-add">
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> Tragen Sie die Produktdaten Zeile für Zeile ein. 
                            Klicken Sie auf "+ Zeile hinzufügen" für weitere Produkte.
                        </div>

                        <div class="table-responsive">
                            <table class="table table-bordered" id="bulkProductTable">
                                <thead>
                                    <tr>
                                        <th width="25%">Name *</th>
                                        <th width="15%">Kategorie</th>
                                        <th width="15%">Einheit</th>
                                        <th width="12%">Preis (€)</th>
                                        <th width="12%">Nachbestell.</th>
                                        <th width="16%">Beschreibung</th>
                                        <th width="5%"></th>
                                    </tr>
                                </thead>
                                <tbody id="productRows">
                                    <tr class="product-row">
                                        <td>
                                            <input type="text" name="names[]" class="form-control form-control-sm" 
                                                   placeholder="Produktname" required>
                                        </td>
                                        <td>
                                            <select name="categories[]" class="form-select form-select-sm">
                                                <option value="kaffee">Kaffee</option>
                                                <option value="becher">Becher</option>
                                                <option value="zucker">Zucker</option>
                                                <option value="milch">Milch</option>
                                                <option value="snacks">Snacks</option>
                                                <option value="getraenke">Getränke</option>
                                                <option value="sonstiges">Sonstiges</option>
                                            </select>
                                        </td>
                                        <td>
                                            <select name="units[]" class="form-select form-select-sm">
                                                <option value="kg">kg</option>
                                                <option value="piece">Stück</option>
                                                <option value="liter">Liter</option>
                                                <option value="pack">Pack</option>
                                            </select>
                                        </td>
                                        <td>
                                            <input type="number" name="prices[]" class="form-control form-control-sm" 
                                                   step="0.01" placeholder="0.00">
                                        </td>
                                        <td>
                                            <input type="number" name="reorder_points[]" class="form-control form-control-sm" 
                                                   step="0.1" placeholder="10">
                                        </td>
                                        <td>
                                            <input type="text" name="descriptions[]" class="form-control form-control-sm" 
                                                   placeholder="Optional">
                                        </td>
                                        <td>
                                            <button type="button" class="btn btn-sm btn-danger" onclick="removeRow(this)" style="display:none;">
                                                <i class="bi bi-trash"></i>
                                            </button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <button type="button" class="btn btn-sm btn-success" onclick="addProductRow()">
                            <i class="bi bi-plus"></i> Zeile hinzufügen
                        </button>
                    </div>

                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save"></i> Alle Produkte speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    """

    extra_scripts = """
    <script>
    function editProduct(id) {
        alert('Bearbeiten-Funktion kommt noch!');
    }

    function deleteProduct(id, name) {
        if (confirm(`Produkt "${name}" wirklich löschen?`)) {
            window.location.href = `/products/delete/${id}`;
        }
    }

    function addProductRow() {
        const tbody = document.getElementById('productRows');
        const newRow = tbody.rows[0].cloneNode(true);

        // Clear values
        newRow.querySelectorAll('input').forEach(input => {
            input.value = '';
            if (input.hasAttribute('required')) {
                input.removeAttribute('required');
                input.setAttribute('required', '');
            }
        });

        // Show delete button
        newRow.querySelector('.btn-danger').style.display = 'inline-block';

        tbody.appendChild(newRow);
    }

    function removeRow(btn) {
        const row = btn.closest('tr');
        const tbody = row.closest('tbody');

        // Don't remove if it's the last row
        if (tbody.rows.length > 1) {
            row.remove();
        }
    }
    </script>
    """

    extra_css = """
    <style>
        .product-row input, .product-row select {
            min-width: 80px;
        }
        #bulkProductTable {
            font-size: 0.9rem;
        }
        .table-responsive {
            max-height: 400px;
            overflow-y: auto;
        }
    </style>
    """

    return render_template_string(
        render_with_base(
            content,
            active_page='products',
            title='Produkte - Automaten Manager',
            extra_scripts=extra_scripts,
            extra_css=extra_css
        )
    )


@products_bp.route('/add', methods=['POST'])
@login_required
def add_product():
    """Einzelnes Produkt hinzufügen"""
    try:
        # Kategorie
        category_value = request.form.get('category', 'sonstiges')
        print(f"DEBUG: Category value: '{category_value}'")

        try:
            category = ProductCategory(category_value)
        except ValueError as e:
            flash(f'Ungültige Kategorie: {category_value} - {str(e)}', 'danger')
            return redirect(url_for('products.index'))

        # Unit
        unit_value = request.form.get('unit', 'piece')
        print(f"DEBUG: Unit value: '{unit_value}'")

        try:
            unit = ProductUnit(unit_value)
        except ValueError as e:
            flash(f'Ungültige Einheit: {unit_value} - {str(e)}', 'danger')
            return redirect(url_for('products.index'))

        # Sichere Decimal-Konvertierung
        def safe_decimal(value, default=0):
            """Konvertiert sicher zu Decimal"""
            if value is None or value == '':
                return Decimal(str(default))
            try:
                return Decimal(str(value))
            except:
                return Decimal(str(default))

        # Produkt erstellen
        product = Product(
            name=request.form.get('name'),
            category=category,
            unit=unit,
            default_price=safe_decimal(request.form.get('default_price'), 0),
            reorder_point=safe_decimal(request.form.get('reorder_point'), 0),
            description=request.form.get('description'),
            user_id=current_user.id
        )

        db.session.add(product)
        db.session.commit()

        flash(f'Produkt "{product.name}" wurde angelegt!', 'success')

    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        flash(f'Fehler beim Anlegen: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('products.index'))


@products_bp.route('/bulk-add', methods=['POST'])
@login_required
def bulk_add_products():
    """Mehrere Produkte auf einmal hinzufügen"""
    try:
        # Helper-Funktion
        def safe_decimal(value, default=0):
            if value is None or value == '':
                return Decimal(str(default))
            try:
                return Decimal(str(value))
            except:
                return Decimal(str(default))

        names = request.form.getlist('names[]')
        categories = request.form.getlist('categories[]')
        units = request.form.getlist('units[]')
        prices = request.form.getlist('prices[]')
        reorder_points = request.form.getlist('reorder_points[]')
        descriptions = request.form.getlist('descriptions[]')

        products_added = 0

        for i in range(len(names)):
            if names[i].strip():
                try:
                    category_value = categories[i] if i < len(categories) else 'sonstiges'
                    category = ProductCategory(category_value)

                    product = Product(
                        name=names[i].strip(),
                        category=category,
                        unit=ProductUnit(units[i] if i < len(units) else 'piece'),
                        default_price=safe_decimal(prices[i] if i < len(prices) else None),
                        reorder_point=safe_decimal(reorder_points[i] if i < len(reorder_points) else None),
                        description=descriptions[i] if i < len(descriptions) else '',
                        user_id=current_user.id
                    )

                    db.session.add(product)
                    products_added += 1
                except Exception as e:
                    flash(f'Fehler bei Produkt "{names[i]}": {str(e)}', 'warning')

        if products_added > 0:
            db.session.commit()
            flash(f'{products_added} Produkt(e) wurden erfolgreich angelegt!', 'success')
        else:
            flash('Keine Produkte wurden hinzugefügt.', 'warning')

    except Exception as e:
        flash(f'Fehler beim Anlegen: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('products.index'))


@products_bp.route('/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    """Produkt löschen"""
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()

    try:
        name = product.name
        db.session.delete(product)
        db.session.commit()
        flash(f'Produkt "{name}" wurde gelöscht!', 'warning')
    except Exception as e:
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('products.index'))