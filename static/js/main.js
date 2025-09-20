// main.js -- handles billing page dynamic behaviours
document.addEventListener('DOMContentLoaded', () => {
  const lang = localStorage.getItem('khata_lang') || 'en';
  // simple translations (expand as needed)
  const i18n = {
    en: { addRow: 'Add row', clear: 'Clear', save: 'Save bill', total: 'Total' },
    hi: { addRow: 'पंक्ति जोड़ें', clear: 'साफ करें', save: 'बिल सेव करें', total: 'कुल' },
    mr: { addRow: 'ओळ जोडा', clear: 'साफ करा', save: 'बिल जतन करा', total: 'एकूण' }
  };

  // Apply translations for buttons if present (basic)
  const applyTrans = (lang) => {
    if(document.getElementById('addRowBtn')) document.getElementById('addRowBtn').innerHTML = `<i class="fa fa-plus"></i> ${i18n[lang].addRow}`;
    if(document.getElementById('clearBtn')) document.getElementById('clearBtn').innerText = i18n[lang].clear;
    if(document.getElementById('saveBillBtn')) document.getElementById('saveBillBtn').innerHTML = `<i class="fa fa-save"></i> ${i18n[lang].save}`;
  };
  applyTrans(lang);

  // Billing page logic:
  const billBody = document.getElementById('billBody');
  const addRowBtn = document.getElementById('addRowBtn');
  const totalAmt = document.getElementById('totalAmt');
  const saveBillBtn = document.getElementById('saveBillBtn');
  const paymentMethod = document.getElementById('paymentMethod');

  let itemsCache = [];

  // fetch items for user inventory
  fetch('/api/items').then(r => r.json()).then(data => {
    itemsCache = data;
    // start with one row
    addRow();
  });

  function currency(v){ 
    try {
      return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(v);
    } catch(e){ return '₹ ' + v.toFixed(2); }
  }

  function addRow(pref = {}) {
    const tr = document.createElement('tr');

    // Item select
    const tdItem = document.createElement('td');
    const sel = document.createElement('select');
    sel.className = 'form-select form-select-sm item-select';
    const defaultOpt = document.createElement('option');
    defaultOpt.value = '';
    defaultOpt.text = '— choose —';
    sel.appendChild(defaultOpt);
    itemsCache.forEach(it => {
      const o = document.createElement('option');
      o.value = it.id;
      o.dataset.name = it.name;
      o.dataset.unit = it.unit;
      o.dataset.price = it.price;
      o.text = `${it.name} (${it.unit}) - ₹${it.price}`;
      sel.appendChild(o);
    });
    // allow custom entry
    const custom = document.createElement('option');
    custom.value = 'custom';
    custom.text = 'Custom item';
    sel.appendChild(custom);
    sel.value = pref.item_id || '';
    tdItem.appendChild(sel);

    const tdUnit = document.createElement('td');
    const unitInput = document.createElement('input');
    unitInput.className = 'form-control form-control-sm unit-input';
    unitInput.readOnly = true;
    unitInput.value = pref.unit || '';
    tdUnit.appendChild(unitInput);

    const tdPrice = document.createElement('td');
    const priceInput = document.createElement('input');
    priceInput.className = 'form-control form-control-sm price-input';
    priceInput.type = 'number';
    priceInput.step = '0.01';
    priceInput.value = pref.price || 0;
    tdPrice.appendChild(priceInput);

    const tdQty = document.createElement('td');
    const qtyInput = document.createElement('input');
    qtyInput.className = 'form-control form-control-sm qty-input';
    qtyInput.type = 'number';
    qtyInput.step = '0.001';
    qtyInput.value = pref.qty || 1;
    tdQty.appendChild(qtyInput);

    const tdSubtotal = document.createElement('td');
    tdSubtotal.className = 'align-middle subtotal-cell';
    tdSubtotal.innerText = currency( (priceInput.value||0) * (qtyInput.value||0) );

    const tdAction = document.createElement('td');
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-sm btn-outline-danger';
    delBtn.innerHTML = '<i class="fa fa-trash"></i>';
    tdAction.appendChild(delBtn);

    tr.appendChild(tdItem);
    tr.appendChild(tdUnit);
    tr.appendChild(tdPrice);
    tr.appendChild(tdQty);
    tr.appendChild(tdSubtotal);
    tr.appendChild(tdAction);

    // listeners
    sel.addEventListener('change', (e)=>{
      const val = sel.value;
      if(val === 'custom'){
        unitInput.readOnly = false;
        unitInput.value = '';
        priceInput.value = 0;
      } else if(val === ''){
        unitInput.value = '';
        priceInput.value = 0;
        unitInput.readOnly = true;
      } else {
        const selected = itemsCache.find(it => String(it.id) === String(val));
        if(selected){
          unitInput.value = selected.unit;
          priceInput.value = selected.price;
          unitInput.readOnly = true;
        }
      }
      recalcRow();
    });

    const recalcRow = () => {
      const p = parseFloat(priceInput.value||0);
      const q = parseFloat(qtyInput.value||0);
      const sub = (p * q) || 0;
      tdSubtotal.innerText = currency(sub);
      recalcTotal();
    };

    priceInput.addEventListener('input', recalcRow);
    qtyInput.addEventListener('input', recalcRow);
    delBtn.addEventListener('click', ()=>{
      tr.remove();
      recalcTotal();
    });

    billBody.appendChild(tr);
    recalcTotal();
  }

  function recalcTotal(){
    let total = 0;
    document.querySelectorAll('.subtotal-cell').forEach(c => {
      const txt = c.innerText.replace(/[^0-9.]/g,'');
      total += parseFloat(txt || 0);
    });
    totalAmt.innerText = currency(total);
  }

  if(addRowBtn) addRowBtn.addEventListener('click', ()=> addRow());
  if(document.getElementById('clearBtn')) document.getElementById('clearBtn').addEventListener('click', ()=>{
    billBody.innerHTML = '';
    addRow();
    recalcTotal();
  });

  if(saveBillBtn) saveBillBtn.addEventListener('click', async ()=>{
    const rows = [];
    const trs = billBody.querySelectorAll('tr');
    trs.forEach(tr => {
      const sel = tr.querySelector('.item-select');
      const price = parseFloat(tr.querySelector('.price-input').value || 0);
      const qty = parseFloat(tr.querySelector('.qty-input').value || 0);
      const unit = tr.querySelector('.unit-input').value || '';
      let name = '';
      if(sel.value === 'custom'){
        name = prompt('Enter custom item name:') || 'Custom';
      } else {
        const selected = itemsCache.find(it => String(it.id) === String(sel.value));
        name = selected ? selected.name : sel.value;
      }
      const subtotal = price * qty;
      if(qty > 0 && price >= 0){
        rows.push({ name, unit, price, qty, subtotal });
      }
    });

    if(rows.length === 0){
      alert('Add items before saving.');
      return;
    }

    // compute total
    const total = rows.reduce((s,r)=> s + r.subtotal, 0);
    const payload = { items: rows, total: total, payment_method: paymentMethod.value };

    const res = await fetch('/save_bill', {
      method:'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const j = await res.json();
    if(j.status === 'ok'){
      alert('Bill saved (id: ' + j.bill_id + ')');
      window.location.href = '/bill/' + j.bill_id;
    } else {
      alert('Error saving bill');
    }
  });

});
