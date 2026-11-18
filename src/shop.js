(() => {
    const dialog = document.getElementById('productDialog');
    const content = document.getElementById('productDialogContent');
    if (!dialog || typeof dialog.showModal !== 'function') return;
    let trigger = null;
    let previousOverflow = '';
    let scrollLocked = false;

    function releasePage() {
        if (!scrollLocked) return;
        scrollLocked = false;
        document.body.style.overflow = previousOverflow;
        trigger?.focus({ preventScroll: true });
    }
    function closeProduct() {
        dialog.close();
        releasePage();
    }

    document.querySelectorAll('[data-product-details]').forEach(link => {
        if (link instanceof HTMLButtonElement) link.disabled = false;
        link.addEventListener('click', event => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            const template = document.getElementById('product-detail-' + link.dataset.productDetails);
            if (!template) return;
            event.preventDefault();
            content.replaceChildren(template.content.cloneNode(true));
            dialog.setAttribute('aria-labelledby', content.querySelector('.product-dialog-title').id);
            trigger = link;
            previousOverflow = document.body.style.overflow;
            scrollLocked = true;
            dialog.showModal();
            document.body.style.overflow = 'hidden';
        });
    });
    document.getElementById('closeProductDialog').addEventListener('click', closeProduct);
    dialog.addEventListener('close', releasePage);
    content.addEventListener('change', event => {
        if (event.target.name === 'product-variant') {
            content.querySelector('[data-select-product]').disabled =
                !content.querySelector('input[name="product-variant"]:checked');
        }
    });
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom)) closeProduct();
    });
    content.addEventListener('click', event => {
        const customOrder = event.target.closest('.product-custom-link');
        if (customOrder && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
            closeProduct();
            return;
        }
        const photo = event.target.closest('.product-detail-thumb');
        if (photo) {
            const image = content.querySelector('.product-detail-image');
            image.src = photo.dataset.photo;
            image.alt = photo.dataset.caption;
            content.querySelector('.product-detail-image-link').href = photo.dataset.photo;
            content.querySelectorAll('.product-detail-thumb').forEach(button => {
                button.setAttribute('aria-pressed', String(button === photo));
            });
            return;
        }
        const select = event.target.closest('[data-select-product]');
        if (select) {
            const id = Number(select.dataset.selectProduct);
            const variants = content.querySelectorAll('input[name="product-variant"]:checked');
            closeProduct();
            if (variants.length) {
                variants.forEach(variant => addToCart(id, variant.value));
            } else {
                addToCart(id);
            }
            openCart(trigger);
        }
    });
})();
