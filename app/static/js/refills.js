// refills.js - JavaScript für Nachfüllungen/Warenwirtschaft

let itemCount = 0;
let uploadedReceipt = null;

// Produkt-Zeile hinzufügen
window.addProductLine = function() {
    itemCount++;
    
    // Hole die Produkt-Optionen aus dem versteckten Select
    const productOptions = document.getElementById('product-template').innerHTML;
    
    const template = `
        <div class="product-row" id="item-${itemCount}">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <label class="form-label small mb-1">Produkt</label>
                    <select class="form-select product-select" name="product_id[]" required onchange="updatePrice(${itemCount})">
                        ${productOptions}
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label small mb-1">Menge</label>
                    <input type="number" class="form-control quantity-input" name="quantity[]" 
                           placeholder="0" step="0.001" required onchange="calculateTotal(${itemCount})">
                </div>
                <div class="col-md-2">
                    <label class="form-label small mb-1">Stückpreis €</label>
                    <input type="number" class="form-control price-input" name="unit_price[]" 
                           placeholder="0.00" step="0.01" required onchange="calculateTotal(${itemCount})">
                </div>
                <div class="col-md-2">
                    <label class="form-label small mb-1">Rabatt €</label>
                    <input type="number" class="form-control discount-input bg-warning bg-opacity-10" 
                           name="line_discount[]" placeholder="0.00" step="0.01" value="0" 
                           onchange="calculateTotal(${itemCount})" title="Rabatt für diese Position">
                </div>
                <div class="col-md-2">
                    <label class="form-label small mb-1">Gesamt €</label>
                    <input type="text" class="form-control total-input fw-bold" name="total_price[]" 
                           placeholder="0.00" readonly>
                </div>
                <div class="col-md-1 text-center">
                    <label class="form-label small mb-1">&nbsp;</label><br>
                    <button type="button" class="btn btn-sm btn-danger" onclick="removeItem(${itemCount})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
            <div class="row mt-1">
                <div class="col-md-11">
                    <input type="text" class="form-control form-control-sm" name="line_discount_reason[]" 
                           placeholder="Rabatt-Grund (optional, z.B. Mengenrabatt, Aktion)">
                </div>
            </div>
        </div>
    `;

    document.getElementById('product-items').insertAdjacentHTML('beforeend', template);
};

// Zeile entfernen
window.removeItem = function(id) {
    document.getElementById(`item-${id}`).remove();
    calculateGrandTotal();
};

// Preis aus Produkt-Auswahl übernehmen
window.updatePrice = function(id) {
    const select = document.querySelector(`#item-${id} .product-select`);
    const priceInput = document.querySelector(`#item-${id} .price-input`);
    const selectedOption = select.options[select.selectedIndex];

    if (selectedOption.dataset.price) {
        priceInput.value = selectedOption.dataset.price;
        calculateTotal(id);
    }
};

// Zeilen-Total berechnen
window.calculateTotal = function(id) {
    const quantity = parseFloat(document.querySelector(`#item-${id} .quantity-input`).value) || 0;
    const price = parseFloat(document.querySelector(`#item-${id} .price-input`).value) || 0;
    const discount = parseFloat(document.querySelector(`#item-${id} .discount-input`).value) || 0;

    // Berechnung: (Menge × Preis) - Rabatt
    const grossTotal = quantity * price;
    const netTotal = grossTotal - discount;

    // Visual feedback wenn Rabatt vorhanden
    const discountInput = document.querySelector(`#item-${id} .discount-input`);
    if (discount > 0) {
        discountInput.classList.add('border-warning');
        // Zeige Ersparnis in Prozent
        if (grossTotal > 0) {
            const savedPercent = ((discount / grossTotal) * 100).toFixed(1);
            discountInput.title = `Ersparnis: ${savedPercent}%`;
        }
    } else {
        discountInput.classList.remove('border-warning');
    }

    document.querySelector(`#item-${id} .total-input`).value = netTotal.toFixed(2);
    calculateGrandTotal();
};

// Gesamtsumme berechnen
window.calculateGrandTotal = function() {
    let grandTotal = 0;
    let totalLineDiscounts = 0;

    // Summiere alle Zeilen-Rabatte
    document.querySelectorAll('.discount-input').forEach(input => {
        totalLineDiscounts += parseFloat(input.value) || 0;
    });

    // Summiere alle Zeilen-Totale (bereits mit Rabatt)
    document.querySelectorAll('.total-input').forEach(input => {
        grandTotal += parseFloat(input.value) || 0;
    });

    const taxRate = parseFloat(document.getElementById('taxRate').value) || 20;
    const pricesIncludeTax = document.getElementById('pricesIncludeTax').checked;
    const shipping = parseFloat(document.querySelector('[name="shipping_cost"]').value) || 0;
    const deposit = parseFloat(document.querySelector('[name="deposit_amount"]').value) || 0;
    const globalDiscount = parseFloat(document.querySelector('[name="discount_amount"]').value) || 0;

    // Globaler Rabatt zusätzlich
    grandTotal = grandTotal - globalDiscount;

    let subtotal, tax, total;

    if (pricesIncludeTax) {
        // Preise enthalten bereits MwSt - herausrechnen
        total = grandTotal;
        subtotal = total / (1 + taxRate/100);
        tax = total - subtotal;
    } else {
        // Nettopreise - MwSt draufrechnen
        subtotal = grandTotal;
        tax = subtotal * (taxRate/100);
        total = subtotal + tax;
    }

    // Versand und Pfand hinzufügen
    const finalTotal = total + shipping + deposit;

    // Anzeige aktualisieren
    document.getElementById('subtotal').innerHTML = `
        <small class="text-muted">Warenwert netto:</small><br>
        <strong>${subtotal.toFixed(2)} €</strong>
    `;
    document.getElementById('tax').innerHTML = `
        <small class="text-muted">MwSt (${taxRate}%):</small><br>
        <strong>${tax.toFixed(2)} €</strong>
    `;

    // Zeilen-Rabatte anzeigen
    if (totalLineDiscounts > 0) {
        document.getElementById('line-discounts-row').style.display = 'flex';
        document.getElementById('line-discounts-display').innerHTML = `
            <span class="text-warning">- ${totalLineDiscounts.toFixed(2)} €</span>
        `;
    } else {
        document.getElementById('line-discounts-row').style.display = 'none';
    }

    // Globaler Rabatt
    if (globalDiscount > 0) {
        document.getElementById('discount-row').style.display = 'flex';
        document.getElementById('discount-display').textContent = '- ' + globalDiscount.toFixed(2) + ' €';
    } else {
        document.getElementById('discount-row').style.display = 'none';
    }

    // Versandzeile
    if (shipping > 0) {
        document.getElementById('shipping-row').style.display = 'flex';
        document.getElementById('shipping-amount').textContent = shipping.toFixed(2) + ' €';
    } else {
        document.getElementById('shipping-row').style.display = 'none';
    }

    // Pfandzeile
    if (deposit > 0) {
        document.getElementById('deposit-row').style.display = 'flex';
        document.getElementById('deposit-amount').textContent = deposit.toFixed(2) + ' €';
    } else {
        document.getElementById('deposit-row').style.display = 'none';
    }

    // Gesamtersparnis anzeigen
    const totalSavings = totalLineDiscounts + globalDiscount;
    if (totalSavings > 0) {
        document.getElementById('savings-info').style.display = 'block';
        document.getElementById('total-savings').textContent = totalSavings.toFixed(2);
    } else {
        document.getElementById('savings-info').style.display = 'none';
    }

    document.getElementById('grand-total').innerHTML = `<strong>${finalTotal.toFixed(2)} €</strong>`;
};

// Drag & Drop für Kassenbon
window.setupDragDrop = function() {
    const dropZone = document.getElementById('receipt-drop-zone');
    const fileInput = document.getElementById('receipt-file');
    const preview = document.getElementById('receipt-preview');

    if (!dropZone) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-over');
        }, false);
    });

    dropZone.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFileSelect, false);

    function handleDrop(e) {
        const files = e.dataTransfer.files;
        handleFiles(files);
    }

    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type.match('image.*') || file.type === 'application/pdf') {
                const reader = new FileReader();
                reader.onload = function(e) {
                    uploadedReceipt = {
                        name: file.name,
                        type: file.type,
                        data: e.target.result
                    };
                    showPreview(file, e.target.result);
                };
                reader.readAsDataURL(file);
            } else {
                alert('Bitte nur Bilder oder PDFs hochladen!');
            }
        }
    }

    function showPreview(file, dataUrl) {
        preview.innerHTML = '';
        if (file.type.match('image.*')) {
            preview.innerHTML = `
                <div class="receipt-preview-container">
                    <img src="${dataUrl}" class="img-fluid rounded" style="max-height: 200px;">
                    <p class="mt-2 mb-0"><small>${file.name}</small></p>
                    <button type="button" class="btn btn-sm btn-danger mt-2" onclick="removeReceipt()">
                        <i class="bi bi-trash"></i> Entfernen
                    </button>
                </div>
            `;
        } else {
            preview.innerHTML = `
                <div class="receipt-preview-container">
                    <i class="bi bi-file-pdf display-1 text-danger"></i>
                    <p class="mt-2 mb-0"><small>${file.name}</small></p>
                    <button type="button" class="btn btn-sm btn-danger mt-2" onclick="removeReceipt()">
                        <i class="bi bi-trash"></i> Entfernen
                    </button>
                </div>
            `;
        }

        // Hidden fields für Form Submit
        if (!document.getElementById('receipt_data')) {
            const hiddenData = document.createElement('input');
            hiddenData.type = 'hidden';
            hiddenData.id = 'receipt_data';
            hiddenData.name = 'receipt_data';
            hiddenData.value = dataUrl;
            document.getElementById('refillForm').appendChild(hiddenData);

            const hiddenName = document.createElement('input');
            hiddenName.type = 'hidden';
            hiddenName.id = 'receipt_filename';
            hiddenName.name = 'receipt_filename';
            hiddenName.value = file.name;
            document.getElementById('refillForm').appendChild(hiddenName);
        } else {
            document.getElementById('receipt_data').value = dataUrl;
            document.getElementById('receipt_filename').value = file.name;
        }
    }
};

// Kassenbon entfernen
window.removeReceipt = function() {
    uploadedReceipt = null;
    document.getElementById('receipt-preview').innerHTML = '';
    document.getElementById('receipt-file').value = '';
    if (document.getElementById('receipt_data')) {
        document.getElementById('receipt_data').remove();
        document.getElementById('receipt_filename').remove();
    }
};

// Nachfüllung anzeigen
window.viewRefill = function(id) {
    window.location.href = `/refills/view/${id}`;
};

// Nachfüllung bearbeiten
window.editRefill = function(id) {
    window.location.href = `/refills/edit/${id}`;
};

// Nachfüllung löschen
window.deleteRefill = function(id) {
    if (confirm('Wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden!')) {
        // Form erstellen für POST request
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/refills/delete/${id}`;
        document.body.appendChild(form);
        form.submit();
    }
};

// Event Listener beim DOM-Load
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== REFILLS MODULE LOADED ===');
    
    const taxRateInput = document.getElementById('taxRate');
    const pricesIncludeTaxCheckbox = document.getElementById('pricesIncludeTax');
    const shippingInput = document.querySelector('[name="shipping_cost"]');
    const depositInput = document.querySelector('[name="deposit_amount"]');
    const discountInput = document.querySelector('[name="discount_amount"]');

    if (taxRateInput) taxRateInput.addEventListener('change', calculateGrandTotal);
    if (pricesIncludeTaxCheckbox) pricesIncludeTaxCheckbox.addEventListener('change', calculateGrandTotal);
    if (shippingInput) shippingInput.addEventListener('input', calculateGrandTotal);
    if (depositInput) depositInput.addEventListener('input', calculateGrandTotal);
    if (discountInput) discountInput.addEventListener('input', calculateGrandTotal);

    // Setup Drag & Drop
    setupDragDrop();

    // Click handler für Drop Zone
    const dropZone = document.getElementById('receipt-drop-zone');
    if (dropZone) {
        dropZone.addEventListener('click', function() {
            document.getElementById('receipt-file').click();
        });
    }

    // Modal Event Handler
    const refillModal = document.getElementById('refillModal');
    if (refillModal) {
        refillModal.addEventListener('shown.bs.modal', function () {
            console.log('Modal opened!');
            if (document.getElementById('product-items').children.length === 0) {
                console.log('Adding first product line...');
                addProductLine();
            }
        });
    }

    console.log('Refills JavaScript ready!');
});
