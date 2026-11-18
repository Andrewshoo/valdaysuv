const SITE = document.body.dataset;
const PRODUCTS = Array.from(document.querySelectorAll('[data-product-id]'), card => ({
    id: Number(card.dataset.productId),
    name: card.dataset.productName,
    image: card.dataset.productImage,
    price: card.dataset.priceKopecks ? BigInt(card.dataset.priceKopecks) : null,
}));
const rubleNumber = new Intl.NumberFormat('ru-RU');

function formatPrice(kopecks) {
    const fraction = kopecks % 100n;
    return rubleNumber.format(kopecks / 100n) +
        (fraction ? ',' + String(fraction).padStart(2, '0') : '') + ' ₽';
}

function cartLines() {
    return Object.entries(cart).map(([id, quantity]) => {
        const product = PRODUCTS.find(item => item.id === Number(id));
        return { ...product, quantity, subtotal: product.price === null ? null : product.price * BigInt(quantity) };
    });
}

function summarizePrices(lines) {
    const priced = lines.filter(line => line.subtotal !== null);
    if (!priced.length) return { label: 'Стоимость изделий', value: 'По запросу' };
    const total = priced.reduce((sum, line) => sum + line.subtotal, 0n);
    return priced.length === lines.length
        ? { label: 'Итого за изделия', value: formatPrice(total) }
        : { label: 'Сумма по известным ценам', value: formatPrice(total) + ' + цена по запросу' };
}

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
        const lines = cartLines();

        if (!lines.length) {
            body.innerHTML = `<div class="cart-empty"><p>Корзина пуста</p><a href="#catalog" onclick="closeCart()">Перейти к каталогу</a></div>`;
            foot.style.display = 'none';
            return;
        }

        foot.style.display = 'block';
        document.getElementById('cartTotal').textContent = totalQty() + ' шт.';
        const summary = summarizePrices(lines);
        document.getElementById('cartSubtotalLabel').textContent = summary.label;
        document.getElementById('cartSubtotal').textContent = summary.value;
        body.innerHTML = lines.map(({ id, image, quantity, price, subtotal }) => {
            const pricing = price === null ? 'Цена по запросу' : formatPrice(price) + ' за шт.';
            return `<div class="cart-item">
                ${image ? '<img class="cart-item-photo" alt="" width="64" height="64">' : ''}
                <div class="cart-item-name"><span class="cart-product-title"></span>
                    <span class="cart-item-price">${pricing}</span>
                </div>
                <div class="qty">
                    <button type="button" class="qty-btn" onclick="changeQty(${id},-1)" aria-label="Уменьшить количество">−</button>
                    <span class="qty-val">${quantity}</span>
                    <button type="button" class="qty-btn" onclick="changeQty(${id},1)" aria-label="Увеличить количество">+</button>
                </div>
                <strong class="cart-item-subtotal">${subtotal === null ? '' : formatPrice(subtotal)}</strong>
            </div>`;
        }).join('');
        body.querySelectorAll('.cart-item').forEach((row, index) => {
            const { name, image } = lines[index];
            row.querySelector('.cart-product-title').textContent = name;
            const photo = row.querySelector('.cart-item-photo');
            if (photo) photo.src = image;
        });
    }

    function openCart() {
        closeOrderModal();
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
        if (!totalQty()) return;
        closeCart();
        document.getElementById('orderWrap').classList.add('open');
        document.body.style.overflow = 'hidden';
        document.getElementById('orderTitle').focus();
    }
    function closeOrderModal() {
        document.getElementById('orderWrap').classList.remove('open');
        document.body.style.overflow = '';
    }

    function setDelivery() {
        const delivery = document.querySelector('input[name="del"]:checked').value === 'delivery';
        const city = document.getElementById('oCity');
        document.getElementById('dPickup').classList.toggle('sel', !delivery);
        document.getElementById('dDelivery').classList.toggle('sel', delivery);
        document.getElementById('cityGroup').hidden = !delivery;
        city.disabled = !delivery;
        city.required = delivery;
        city.setCustomValidity('');
    }

    function buildReceipt(event) {
        event.preventDefault();
        const products = cartLines();
        if (!products.length) return;
        const email   = document.getElementById('oEmail').value.trim();
        const consent = document.getElementById('oConsent');
        const delType = document.querySelector('input[name="del"]:checked').value;
        const cityEl  = document.getElementById('oCity');

        if (email && !consent.checked) {
            alert('Пожалуйста, дайте согласие на обработку персональных данных (чекбокс под полем email).');
            return;
        }
        const city = cityEl.value.trim();
        if (delType === 'delivery' && !city) {
            cityEl.setCustomValidity('Укажите город или населённый пункт.');
            cityEl.reportValidity();
            return;
        }

        const now = new Date().toLocaleString('ru-RU', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });

        const delStr = delType === 'pickup' ? 'Самовывоз — ' + SITE.pickupAddress :
            'Доставка — ' + city + '\nСтоимость доставки уточнит мастерская.';

        const emailStr = email ? `\nEmail для ответа: ${email}` : '';

        const lines = products.map(({ name, quantity, price, subtotal }) => {
            const pricing = price === null ? 'цена по запросу' :
                formatPrice(price) + ' за шт., сумма ' + formatPrice(subtotal);
            return `• ${name} — ${quantity} шт., ${pricing}`;
        }).join('\n');
        const summary = summarizePrices(products);

        const text =
`Заявка от ${now}${emailStr}
Получение: ${delStr}

Состав заявки (${totalQty()} шт.):
${lines}

${summary.label}: ${summary.value}
Способ оплаты согласуем после подтверждения заявки.

Мастерская: ${SITE.contactEmail}`;

        document.getElementById('receiptBox').textContent = text;
        const enc = encodeURIComponent(text);
        document.getElementById('waBtn').href = 'https://wa.me/' + SITE.contactPhone.replace(/\D/g, '') + '?text=' + enc;
        document.getElementById('maxBtn').href = 'https://max.ru' + '/u/' + 'f9LHodD0cOJ4Vkr' + 'KwCvHQq4xEsapp' + 'WLGc3P_Ogl_ALy' + '_7OXoqaELlh2OGLc';
        document.getElementById('emailBtn').href = 'mailto:' + SITE.contactEmail
            + '?subject=' + encodeURIComponent('Заявка с сайта valdaysuv.ru')
            + '&body=' + encodeURIComponent(text);

        closeOrderModal();
        document.getElementById('copyStatus').textContent = '';
        document.getElementById('receiptWrap').classList.add('open');
        document.body.style.overflow = 'hidden';
        document.getElementById('receiptTitle').focus();
    }

    function closeReceipt() {
        document.getElementById('receiptWrap').classList.remove('open');
        document.body.style.overflow = '';
    }

    async function copyReceipt() {
        const text = document.getElementById('receiptBox').textContent;
        const status = document.getElementById('copyStatus');
        try {
            await navigator.clipboard.writeText(text);
            status.textContent = 'Текст заявки скопирован.';
        } catch (_) {
            status.textContent = 'Не удалось скопировать автоматически. Выделите текст заявки и скопируйте его вручную.';
        }
    }

    document.getElementById('maxBtn').addEventListener('click', copyReceipt);

    document.getElementById('oEmail').addEventListener('input', function () {
        const wrap = document.getElementById('consentWrap');
        wrap.style.display = this.value.trim() ? 'flex' : 'none';
        if (!this.value.trim()) document.getElementById('oConsent').checked = false;
    });
    document.getElementById('orderForm').addEventListener('submit', buildReceipt);
    document.getElementById('oCity').addEventListener('input', event => event.target.setCustomValidity(''));
    setDelivery();

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

// Switch only the selected product photo; product/cart IDs stay unchanged.
document.querySelectorAll('.product-photos').forEach(group => {
    const image = group.querySelector('.product-img');
    group.addEventListener('click', event => {
        const button = event.target.closest('.product-photo-button');
        if (!button || !group.contains(button)) return;
        image.src = button.dataset.photo;
        image.alt = button.dataset.caption;
        const link = image.closest('.product-photo-link');
        if (link) link.href = button.dataset.photo;
        group.querySelectorAll('.product-photo-button').forEach(item => {
            item.setAttribute('aria-pressed', String(item === button));
        });
    });
});
