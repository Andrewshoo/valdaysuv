const SITE = document.body.dataset;
const PRODUCTS = Array.from(document.querySelectorAll('[data-product-id]'), card => ({
    id: Number(card.dataset.productId),
    name: card.dataset.productName,
    img: card.dataset.productImage || null,
}));

    let cart = {};
    try {
        const saved = JSON.parse(localStorage.getItem('valday-cart') || '{}');
        for (const p of PRODUCTS) {
            if (Number.isSafeInteger(saved[p.id]) && saved[p.id] > 0) cart[p.id] = saved[p.id];
        }
    } catch (_) {}


    function addToCart(id) {
        cart[id] = (cart[id] || 0) + 1;
        syncBadge();
        const btn = document.getElementById('ba' + id);
        if (!btn) return;
        btn.textContent = '✓ Добавлено';
        btn.classList.add('added');
        setTimeout(() => { btn.textContent = '+ В корзину'; btn.classList.remove('added'); }, 1400);
    }

    function changeQty(id, d) {
        cart[id] = (cart[id] || 0) + d;
        if (cart[id] <= 0) delete cart[id];
        syncBadge();
        renderCartBody();
    }

    function totalQty() { return Object.values(cart).reduce((s, v) => s + v, 0); }

    function syncBadge() {
        try { localStorage.setItem('valday-cart', JSON.stringify(cart)); } catch (_) {}
        const n = totalQty();
        const el = document.getElementById('cartBadge');
        el.textContent = n;
        el.classList.toggle('show', n > 0);
    }

    function renderCartBody() {
        const body = document.getElementById('cartBody');
        const foot = document.getElementById('cartFoot');
        const ids  = Object.keys(cart).map(Number);

        if (!ids.length) {
            body.innerHTML = `<div class="cart-empty"><div class="big">🔔</div><p>Корзина пуста</p><p style="font-size:.85rem;margin-top:5px">Добавьте товары из каталога</p></div>`;
            foot.style.display = 'none';
            return;
        }

        foot.style.display = 'block';
        document.getElementById('cartTotal').textContent = totalQty() + ' шт.';
        body.innerHTML = ids.map(id => {
            const p = PRODUCTS.find(x => x.id === id);
            return `<div class="cart-item">
                <div class="cart-item-name">${p.name}</div>
                <div class="qty">
                    <button class="qty-btn" onclick="changeQty(${id},-1)">−</button>
                    <span class="qty-val">${cart[id]}</span>
                    <button class="qty-btn" onclick="changeQty(${id},1)">+</button>
                </div>
            </div>`;
        }).join('');
    }

    function openCart() {
        document.getElementById('cartOverlay').classList.add('open');
        document.getElementById('cartSidebar').classList.add('open');
        document.body.style.overflow = 'hidden';
        renderCartBody();
    }
    function closeCart() {
        document.getElementById('cartOverlay').classList.remove('open');
        document.getElementById('cartSidebar').classList.remove('open');
        document.body.style.overflow = '';
    }

    function openOrderModal() {
        closeCart();
        document.getElementById('orderWrap').classList.add('open');
        document.body.style.overflow = 'hidden';
    }
    function closeOrderModal() {
        document.getElementById('orderWrap').classList.remove('open');
        document.body.style.overflow = '';
    }

    function setDelivery(type) {
        document.getElementById('dPickup').classList.toggle('sel', type === 'pickup');
        document.getElementById('dSdek').classList.toggle('sel',   type === 'sdek');
        document.getElementById('cityGroup').style.display   = type === 'sdek' ? 'block' : 'none';
        document.getElementById('estimateBox').style.display = 'none';
    }

    function calcDelivery() {
        const sel = document.getElementById('oCity');
        const box = document.getElementById('estimateBox');
        if (!sel.value) { box.style.display = 'none'; return; }
        const [, rate] = sel.value.split('|');
        document.getElementById('estimateCost').textContent = '~' + rate + ' руб.';
        box.style.display = 'block';
    }

    function buildReceipt() {
        const email   = document.getElementById('oEmail').value.trim();
        const consent = document.getElementById('oConsent');
        const delType = document.querySelector('input[name="del"]:checked').value;
        const cityEl  = document.getElementById('oCity');

        if (email && !document.getElementById('oEmail').checkValidity()) { alert('Проверьте email-адрес.'); return; }
        if (email && !consent.checked) {
            alert('Пожалуйста, дайте согласие на обработку персональных данных (чекбокс под полем email).');
            return;
        }
        if (delType === 'sdek' && !cityEl.value) { alert('Пожалуйста, выберите город доставки.'); return; }

        const now = new Date().toLocaleString('ru-RU', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });

        let delStr = '', delCostStr = '';
        if (delType === 'pickup') {
            delStr = 'Самовывоз — ' + SITE.pickupAddress;
        } else {
            const [city, rate] = cityEl.value.split('|');
            delStr     = 'Доставка СДЭК — г. ' + city;
            delCostStr = '\nПримерная стоимость доставки: ~' + rate + ' руб.';
        }

        const emailStr = email ? `\nEmail:     ${email}` : '';

        const lines = Object.keys(cart).map(id => {
            const p = PRODUCTS.find(x => x.id === Number(id));
            return `  • ${p.name} — ${cart[id]} шт.`;
        }).join('\n');

        const text =
`ЗАКАЗ от ${now}
================================${emailStr}
Получение: ${delStr}${delCostStr}

Состав заказа (${totalQty()} шт.):
${lines}

================================
📧 ${SITE.contactEmail}`;

        document.getElementById('receiptBox').textContent = text;
        const enc = encodeURIComponent(text);
        document.getElementById('tgBtn').href = 'https://t.me/' + atob('YW5kcmV3c2hvbw==');
        document.getElementById('waBtn').href = 'https://wa.me/' + SITE.contactPhone.replace(/\D/g, '') + '?text=' + enc;
        document.getElementById('maxBtn').href = 'https://max.ru' + '/u/' + 'f9LHodD0cOJ4Vkr' + 'KwCvHQq4xEsapp' + 'WLGc3P_Ogl_ALy' + '_7OXoqaELlh2OGLc';
        document.getElementById('emailBtn').href = 'mailto:' + SITE.contactEmail
            + '?subject=' + encodeURIComponent('Заказ с сайта valdaysuv.ru')
            + '&body=' + encodeURIComponent(text);

        closeOrderModal();
        document.getElementById('receiptWrap').classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closeReceipt() {
        document.getElementById('receiptWrap').classList.remove('open');
        document.body.style.overflow = '';
    }

    function copyReceipt() {
        const text = document.getElementById('receiptBox').textContent;
        navigator.clipboard.writeText(text).then(() => {
            const btn = document.querySelector('.btn-copy');
            const orig = btn.textContent;
            btn.textContent = '✓ Скопировано!';
            setTimeout(() => { btn.textContent = orig; }, 2000);
        });
    }

    ['tgBtn', 'maxBtn'].forEach(id => {
        document.getElementById(id).addEventListener('click', function () {
            navigator.clipboard.writeText(document.getElementById('receiptBox').textContent).catch(() => {});
        });
    });

    document.getElementById('oEmail').addEventListener('input', function () {
        const wrap = document.getElementById('consentWrap');
        wrap.style.display = this.value.trim() ? 'flex' : 'none';
        if (!this.value.trim()) document.getElementById('oConsent').checked = false;
    });

    ['orderWrap', 'receiptWrap'].forEach(id => {
        document.getElementById(id).addEventListener('click', function(e) {
            if (e.target === this) this.id === 'receiptWrap' ? closeReceipt() : closeOrderModal();
        });
    });

    document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        closeCart(); closeOrderModal(); closeReceipt();
    });

    document.querySelectorAll('.btn-add').forEach(button => { button.hidden = false; });
    syncBadge();
    renderCartBody();

// Sort within categories; static HTML keeps every category readable without JS.
const catalogSort = document.getElementById('catalogSort');
const modelNameOrder = new Intl.Collator('ru', { numeric: true });
document.getElementById('catalogSortControl').hidden = false;
catalogSort.addEventListener('change', () => {
    document.querySelectorAll('.catalog-group-grid').forEach(grid => {
        const cards = Array.from(grid.querySelectorAll('[data-product-id]'));
        cards.sort((a, b) => {
            const byName = modelNameOrder.compare(a.dataset.productName, b.dataset.productName);
            if (catalogSort.value === 'name') return byName;
            const byNumber = Number(a.dataset.sizeNumber) - Number(b.dataset.sizeNumber);
            return (catalogSort.value === 'number-desc' ? -byNumber : byNumber) || byName;
        });
        grid.append(...cards);
    });
});
