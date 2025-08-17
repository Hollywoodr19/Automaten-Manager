    """Test-Route für Nachfüllung - Vollständiges Formular ohne Modal"""
    if request.method == 'POST':
        try:
            from datetime import datetime
            from app.models import ExpenseCategory
            
            # Get form data
            product_id = request.form.get('product_id')
            quantity = request.form.get('quantity', '1')
            unit_price = request.form.get('unit_price', '10')
            
            # Create refill
            refill = Refill(
                date=date.today(),
                invoice_number=f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                supplier_id=request.form.get('supplier_id') or None,
                device_id=request.form.get('device_id') or None,
                subtotal=Decimal(unit_price),
                tax_amount=Decimal(unit_price) * Decimal('0.2'),
                total_amount=Decimal(unit_price) * Decimal('1.2'),
                tax_rate=Decimal('20'),
                prices_include_tax=True,
                user_id=current_user.id
            )
            db.session.add(refill)
            db.session.flush()
            
            # Add item if product selected
            if product_id:
                item = RefillItem(
                    refill_id=refill.id,
                    product_id=int(product_id),
                    quantity=Decimal(quantity),
                    unit_price=Decimal(unit_price),
                    total_price=Decimal(quantity) * Decimal(unit_price)
                )
                db.session.add(item)
            
            db.session.commit()
            flash(f'Test-Nachfüllung #{refill.id} erfolgreich erstellt!', 'success')
            return redirect(url_for('refills.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
            import traceback
            print(traceback.format_exc())
    
    # GET - Show simple form
    products = Product.query.filter_by(user_id=current_user.id).all()
    suppliers = Supplier.query.filter_by(user_id=current_user.id).all()
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
    <div class="container" style="padding: 50px;">
        <h2>Test-Nachfüllung (Einfaches Formular)</h2>
        <form method="POST">
            <div class="mb-3">
                <label>Lieferant:</label>
                <select name="supplier_id" class="form-control">
                    <option value="">-- Kein Lieferant --</option>
    '''
    
    for supplier in suppliers:
        html += f'<option value="{supplier.id}">{supplier.name}</option>'
    
    html += '''
                </select>
            </div>
            <div class="mb-3">
                <label>Gerät:</label>
                <select name="device_id" class="form-control">
                    <option value="">-- Kein Gerät --</option>
    '''
    
    for device in devices:
        html += f'<option value="{device.id}">{device.name}</option>'
    
    html += '''
                </select>
            </div>
            <div class="mb-3">
                <label>Produkt:</label>
                <select name="product_id" class="form-control">
                    <option value="">-- Kein Produkt --</option>
    '''
    
    for product in products:
        html += f'<option value="{product.id}">{product.name}</option>'
    
    html += '''
                </select>
            </div>
            <div class="mb-3">
                <label>Menge:</label>
                <input type="number" name="quantity" class="form-control" value="1" step="0.001">
            </div>
            <div class="mb-3">
                <label>Stückpreis:</label>
                <input type="number" name="unit_price" class="form-control" value="10.00" step="0.01">
            </div>
            <button type="submit" class="btn btn-primary">Test-Nachfüllung anlegen</button>
            <a href="/refills/" class="btn btn-secondary">Zurück</a>
        </form>
    </div>
    </body>
    </html>
    '''
    
    return html


@refills_bp.route('/view/<int:refill_id>')
@login_required
def view_refill(refill_id):
    """Nachfüllung Details anzeigen"""
    refill = Refill.query.filter_by(id=refill_id, user_id=current_user.id).first_or_404()

    content = f"""
    <div class="container">
        <h2 class="text-white mb-4">
            <i class="bi bi-receipt"></i> Nachfüllung vom {refill.date.strftime('%d.%m.%Y')}
        </h2>

        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5>Details</h5>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <tr>
                                <th>Lieferant:</th>
                                <td>{refill.supplier.name if refill.supplier else 'Nicht angegeben'}</td>
                            </tr>
                            <tr>
                                <th>Rechnungsnr:</th>
                                <td>{refill.invoice_number or '—'}</td>
                            </tr>
                            <tr>
                                <th>Netto:</th>
                                <td>{refill.subtotal:.2f} €</td>
                            </tr>
                            <tr>
                                <th>MwSt ({refill.tax_rate}%):</th>
                                <td>{refill.tax_amount:.2f} €</td>
                            </tr>
    """

    if hasattr(refill, 'discount_amount') and refill.discount_amount > 0:
        content += f"""
                            <tr>
                                <th>Zusatz-Rabatt:</th>
                                <td>-{refill.discount_amount:.2f} € ({refill.discount_reason or 'Kein Grund'})</td>
                            </tr>
        """

    if refill.deposit_amount > 0:
        content += f"""
                            <tr>
                                <th>Pfand:</th>
                                <td>{refill.deposit_amount:.2f} €</td>
                            </tr>
        """

    content += f"""
                            <tr>
                                <th>Gesamt:</th>
                                <td><strong>{refill.total_amount:.2f} €</strong></td>
                            </tr>
                        </table>

                        <h6 class="mt-4">Positionen:</h6>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Produkt</th>
                                    <th>Menge</th>
                                    <th>Preis/Einheit</th>
                                    <th>Rabatt</th>
                                    <th>Gesamt</th>
                                </tr>
                            </thead>
                            <tbody>
    """

    total_line_discount = 0
    for item in refill.items:
        line_discount = item.line_discount if hasattr(item, 'line_discount') else 0
        total_line_discount += line_discount

        content += f"""
                                <tr>
                                    <td>{item.product.name}</td>
                                    <td>{item.quantity} {item.product.unit.value}</td>
                                    <td>{item.unit_price:.2f} €</td>
                                    <td>{'—' if line_discount == 0 else f'-{line_discount:.2f} €'}</td>
                                    <td>{item.total_price:.2f} €</td>
                                </tr>
        """

        if hasattr(item, 'line_discount_reason') and item.line_discount_reason:
            content += f"""
                                <tr>
                                    <td colspan="5" class="text-muted small ps-4">
                                        → Rabatt-Grund: {item.line_discount_reason}
                                    </td>
                                </tr>
            """

    if total_line_discount > 0:
        content += f"""
                                <tr class="table-info">
                                    <td colspan="3"><strong>Zeilen-Rabatte gesamt:</strong></td>
                                    <td><strong>-{total_line_discount:.2f} €</strong></td>
                                    <td></td>
                                </tr>
        """

    content += """
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="col-md-4">
    """

    # Kassenbon anzeigen wenn vorhanden
    if hasattr(refill, 'receipt_data') and refill.receipt_data:
        content += f"""
                <div class="card">
                    <div class="card-header">
                        <h5>📸 Kassenbon</h5>
                    </div>
                    <div class="card-body text-center">
        """

        if refill.receipt_data.startswith('data:image'):
            content += f"""
                        <img src="{refill.receipt_data}" class="img-fluid rounded" style="max-width: 100%;">
                        <p class="mt-2"><small>{refill.receipt_filename}</small></p>
            """
        else:
            content += f"""
                        <i class="bi bi-file-pdf display-1 text-danger"></i>
                        <p class="mt-2"><small>{refill.receipt_filename}</small></p>
                        <a href="{refill.receipt_data}" download="{refill.receipt_filename}" 
                           class="btn btn-sm btn-primary">
                            <i class="bi bi-download"></i> Herunterladen
                        </a>
            """

        content += """
                    </div>
                </div>
        """

    content += """
                <a href="/refills" class="btn btn-secondary mt-3">
                    <i class="bi bi-arrow-left"></i> Zurück zur Übersicht
                </a>
            </div>
        </div>
    </div>
    """

    # Use modern template
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title=f'Nachfüllung #{refill.id}',
        active_module='inventory',
        active_submodule='refills',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
            {'text': 'Nachfüllungen', 'url': url_for('refills.index')},
            {'text': f'Details #{refill.id}'}
        ]
    )
