

@refills_bp.route('/add', methods=['POST'])
@login_required
def add_refill():
    """Neue Nachfüllung hinzufügen - Mit Zeilen-Rabatt"""
    try:
        # Debug-Ausgabe aktivieren
        import sys
        print("\n=== REFILL ADD - FORM RECEIVED ===", file=sys.stderr)
        print(f"User: {current_user.username}", file=sys.stderr)
        print(f"Form Keys: {list(request.form.keys())}", file=sys.stderr)
        print(f"Product IDs: {request.form.getlist('product_id[]')}", file=sys.stderr)
        print(f"Quantities: {request.form.getlist('quantity[]')}", file=sys.stderr)
        print(f"Unit Prices: {request.form.getlist('unit_price[]')}", file=sys.stderr)
        print("========================\n", file=sys.stderr)
        
        # MwSt-Optionen
        tax_rate = Decimal(request.form.get('tax_rate', '20'))
        prices_include_tax = request.form.get('prices_include_tax') == 'on'
        deposit_amount = Decimal(request.form.get('deposit_amount', 0))
        discount_amount = Decimal(request.form.get('discount_amount', 0))
        discount_reason = request.form.get('discount_reason', '')

        # Kassenbon-Daten
        receipt_data = request.form.get('receipt_data')
        receipt_filename = request.form.get('receipt_filename')

        # Eindeutige Rechnungsnummer generieren falls leer
        invoice_number = request.form.get('invoice_number')
        if not invoice_number or invoice_number.strip() == '':
            from datetime import datetime
            import random
            import string
            # Format: REF-YYYYMMDD-XXXXX (z.B. REF-20250816-A3B7K)
            date_str = datetime.now().strftime('%Y%m%d')
            random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            invoice_number = f"REF-{date_str}-{random_code}"

        # Refill erstellen
        refill = Refill(
            date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
            supplier_id=request.form.get('supplier_id') or None,
            device_id=request.form.get('device_id') or None,
            invoice_number=invoice_number,
            delivery_note=request.form.get('delivery_note'),
            shipping_cost=Decimal(request.form.get('shipping_cost', 0)),
            deposit_amount=deposit_amount,
            tax_rate=tax_rate,
            prices_include_tax=prices_include_tax,
            discount_amount=discount_amount,
            discount_reason=discount_reason,
            user_id=current_user.id
        )

        # Kassenbon speichern
        if receipt_data:
            refill.receipt_filename = receipt_filename
            refill.receipt_data = receipt_data

        db.session.add(refill)
        db.session.flush()  # ID generieren

        # Produkte hinzufügen
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        line_discounts = request.form.getlist('line_discount[]')
        line_discount_reasons = request.form.getlist('line_discount_reason[]')

        items_total = Decimal('0')
        total_line_discount = Decimal('0')

        for i in range(len(product_ids)):
            if product_ids[i]:  # Nur wenn Produkt ausgewählt
                quantity = Decimal(quantities[i])
                unit_price = Decimal(unit_prices[i])
                line_discount = Decimal(line_discounts[i] if i < len(line_discounts) and line_discounts[i] else 0)
                line_discount_reason = line_discount_reasons[i] if i < len(line_discount_reasons) else ''

                # Berechnung mit Zeilen-Rabatt
                gross_price = quantity * unit_price
                net_price = gross_price - line_discount

                item = RefillItem(
                    refill_id=refill.id,
                    product_id=int(product_ids[i]),
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=net_price,  # Nach Rabatt
                    line_discount=line_discount,
                    line_discount_reason=line_discount_reason
                )
                db.session.add(item)
                items_total += net_price
                total_line_discount += line_discount

                # Lagerbewegung erstellen
                movement = InventoryMovement(
                    product_id=int(product_ids[i]),
                    device_id=refill.device_id,
                    refill_item_id=item.id,
                    type='IN',
                    quantity=quantity,
                    reason='Nachfüllung',
                    user_id=current_user.id
                )
                db.session.add(movement)

        # Gesamtsummen berechnen (mit allen Rabatten)
        items_total_after_global_discount = items_total - discount_amount

        if prices_include_tax:
            # Preise enthalten MwSt - herausrechnen
            total_with_tax = items_total_after_global_discount
            subtotal = total_with_tax / (1 + tax_rate / 100)
            refill.tax_amount = total_with_tax - subtotal
        else:
            # Nettopreise - MwSt draufrechnen
            subtotal = items_total_after_global_discount
            refill.tax_amount = subtotal * (tax_rate / 100)

        refill.subtotal = subtotal
        refill.total_amount = subtotal + refill.tax_amount + refill.shipping_cost + deposit_amount

        # Als Ausgabe erfassen
        expense = Expense(
            category=ExpenseCategory('nachfuellung'),
            amount=refill.total_amount,
            date=refill.date,
            device_id=refill.device_id,
            description=f"Nachfüllung - {len([p for p in product_ids if p])} Produkte",
            supplier=refill.supplier.name if refill.supplier else None,
            invoice_number=refill.invoice_number,
            user_id=current_user.id
        )
        db.session.add(expense)
        refill.expense_id = expense.id

        db.session.commit()

        # Detaillierte Erfolgsmeldung
        total_savings = total_line_discount + discount_amount
        flash_msg = f'Nachfüllung erfasst! Gesamt: {refill.total_amount:.2f} € '
        flash_msg += f'(Netto: {refill.subtotal:.2f} €, MwSt {tax_rate}%: {refill.tax_amount:.2f} €'
        if total_savings > 0:
            flash_msg += f', Gesamtersparnis: {total_savings:.2f} €'
        if deposit_amount > 0:
            flash_msg += f', Pfand: {deposit_amount:.2f} €'
        if receipt_filename:
            flash_msg += f', Beleg: ✅'
        flash_msg += ')'

        flash(flash_msg, 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern: {str(e)}', 'danger')
        print(f"DEBUG ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())

    return redirect(url_for('refills.index'))


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
