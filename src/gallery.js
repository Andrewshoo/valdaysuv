const galleryCards = Array.from(document.querySelectorAll('.gallery-card'));
const galleryFilters = Array.from(document.querySelectorAll('[data-gallery-filter]'));
const galleryDialog = document.getElementById('galleryDialog');
const galleryImage = document.getElementById('lightboxImage');
const galleryCaption = document.getElementById('lightboxCaption');
const galleryPosition = document.getElementById('lightboxCount');
let activeGalleryIndex = 0;
let galleryTrigger = null;
let previousOverflow = '';

function visibleWorks() {
    return galleryCards.filter(card => !card.hidden);
}

function showGalleryWork(index) {
    const works = visibleWorks();
    activeGalleryIndex = (index + works.length) % works.length;
    const card = works[activeGalleryIndex];
    const image = card.querySelector('img');
    galleryImage.src = card.querySelector('a').href;
    galleryImage.alt = image.alt;
    galleryCaption.textContent = card.querySelector('h2').textContent;
    galleryPosition.textContent = `${activeGalleryIndex + 1} / ${works.length}`;
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
        document.getElementById('galleryCount').textContent = `Показано работ: ${visibleWorks().length}`;
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
    galleryTrigger?.focus();
});
