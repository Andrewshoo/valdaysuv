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

    document.querySelectorAll('[data-product-details]').forEach(button => {
        button.hidden = false;
        button.addEventListener('click', () => {
            const template = document.getElementById('product-detail-' + button.dataset.productDetails);
            if (!template) return;
            content.replaceChildren(template.content.cloneNode(true));
            dialog.setAttribute('aria-labelledby', content.querySelector('.product-dialog-title').id);
            trigger = button;
            previousOverflow = document.body.style.overflow;
            scrollLocked = true;
            dialog.showModal();
            document.body.style.overflow = 'hidden';
        });
    });
    document.getElementById('closeProductDialog').addEventListener('click', closeProduct);
    dialog.addEventListener('close', releasePage);
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom)) closeProduct();
    });
    content.addEventListener('click', event => {
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
            closeProduct();
            addToCart(id);
            openCart();
        }
    });
})();
