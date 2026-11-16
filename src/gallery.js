const galleryCards = Array.from(document.querySelectorAll('.gallery-card'));
const galleryFilters = Array.from(document.querySelectorAll('[data-gallery-filter]'));
const galleryDialog = document.getElementById('galleryDialog');
const galleryImage = document.getElementById('lightboxImage');
const galleryCaption = document.getElementById('lightboxCaption');
const galleryPosition = document.getElementById('lightboxCount');
const galleryDescription = document.getElementById('lightboxDescription');
const galleryTheme = document.getElementById('lightboxTheme');
const galleryMedia = document.getElementById('lightboxMedia');
const galleryLoadStatus = document.getElementById('lightboxStatus');
let activeGalleryIndex = 0;
let galleryTrigger = null;
let previousOverflow = '';

function visibleWorks() {
    return galleryCards.filter(card => !card.hidden);
}

function showGalleryWork(index) {
    const works = visibleWorks();
    activeGalleryIndex = (index + works.length) % works.length;
    if (!works.length) return;
    const card = works[activeGalleryIndex];
    const image = card.querySelector('img');
    galleryLoadStatus.textContent = 'Загружаем фотографию…';
    galleryLoadStatus.hidden = false;
    galleryImage.classList.add('is-loading');
    galleryImage.hidden = false;
    galleryImage.src = card.querySelector('a').href;
    galleryImage.alt = image.alt;
    galleryCaption.textContent = card.querySelector('h2').textContent;
    galleryDescription.textContent = card.querySelector('figcaption p').textContent;
    galleryTheme.textContent = card.querySelector('.gallery-theme').textContent;
    galleryPosition.textContent = `${activeGalleryIndex + 1} / ${works.length}`;
    document.getElementById('galleryPrev').disabled = works.length < 2;
    document.getElementById('galleryNext').disabled = works.length < 2;
    // Warm only the adjacent originals, not the whole collection.
    if (works.length > 1) {
        const next = new Image();
        next.src = works[(activeGalleryIndex + 1) % works.length].querySelector('a').href;
    }
}

document.querySelector('.gallery-filters').hidden = false;
galleryFilters.forEach(button => {
    button.addEventListener('click', () => {
        const category = button.dataset.galleryFilter;
        galleryCards.forEach(card => {
            card.hidden = category !== 'all' && card.dataset.galleryCategory !== category;
        });
        galleryFilters.forEach(filter => {
            filter.setAttribute('aria-pressed', String(filter === button));
        });
        document.getElementById('galleryCount').textContent = `Работ: ${visibleWorks().length}`;
    });
});

galleryCards.forEach(card => {
    const link = card.querySelector('a');
    link.addEventListener('click', event => {
        // Retain normal image links for new tabs and browsers without dialog support.
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
            typeof galleryDialog.showModal !== 'function') return;
        event.preventDefault();
        galleryTrigger = link;
        showGalleryWork(visibleWorks().indexOf(card));
        previousOverflow = document.body.style.overflow;
        galleryDialog.showModal();
        document.body.style.overflow = 'hidden';
    });
});

galleryDialog.querySelector('.gallery-close').addEventListener('click', () => galleryDialog.close());
document.getElementById('galleryPrev').addEventListener('click', () => showGalleryWork(activeGalleryIndex - 1));
document.getElementById('galleryNext').addEventListener('click', () => showGalleryWork(activeGalleryIndex + 1));
galleryDialog.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        event.preventDefault();
        showGalleryWork(activeGalleryIndex + (event.key === 'ArrowLeft' ? -1 : 1));
    }
});
galleryDialog.addEventListener('click', event => {
    const bounds = galleryDialog.getBoundingClientRect();
    if (event.target === galleryDialog &&
        (event.clientX < bounds.left || event.clientX > bounds.right ||
         event.clientY < bounds.top || event.clientY > bounds.bottom)) galleryDialog.close();
});
galleryDialog.addEventListener('close', () => {
    document.body.style.overflow = previousOverflow;
    galleryTrigger?.focus({ preventScroll: true });
});

// Keep loading failures visible without blocking navigation to the next work.
galleryImage.addEventListener('load', () => {
    galleryLoadStatus.hidden = true;
    galleryImage.classList.remove('is-loading');
});
galleryImage.addEventListener('error', () => {
    galleryImage.hidden = true;
    galleryLoadStatus.textContent = 'Не удалось загрузить фото. Можно перейти к следующей работе.';
    galleryLoadStatus.hidden = false;
});

// Native vertical gestures and pinch zoom remain available; a horizontal swipe changes work.
let swipe = null;
galleryMedia.addEventListener('touchstart', event => {
    if (event.touches.length !== 1) { swipe = null; return; }
    swipe = { x: event.touches[0].clientX, y: event.touches[0].clientY, time: performance.now() };
}, { passive: true });
galleryMedia.addEventListener('touchmove', event => {
    if (event.touches.length !== 1) swipe = null;
}, { passive: true });
galleryMedia.addEventListener('touchcancel', () => { swipe = null; }, { passive: true });
galleryMedia.addEventListener('touchend', event => {
    if (!swipe || event.changedTouches.length !== 1) return;
    const start = swipe;
    swipe = null;
    const dx = event.changedTouches[0].clientX - start.x;
    const dy = event.changedTouches[0].clientY - start.y;
    if (performance.now() - start.time < 900 && Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        showGalleryWork(activeGalleryIndex + (dx < 0 ? 1 : -1));
    }
}, { passive: true });
