(() => {
    const rail = document.querySelector('.inscriptions-grid');
    const toggle = document.getElementById('inscriptionsToggle');
    if (!rail || !toggle) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let paused = reducedMotion.matches;
    let hovering = false;
    let dragging = false;
    let visible = false;
    let resumeAt = 0;
    let direction = 1;
    let position = rail.scrollLeft;
    let frame = 0;
    let previousTime = 0;
    let startX = 0;
    let startScroll = 0;

    rail.classList.add('is-interactive');
    toggle.hidden = false;

    function updateToggle() {
        toggle.textContent = paused ? 'Включить прокрутку' : 'Остановить прокрутку';
        toggle.setAttribute('aria-pressed', String(!paused));
    }

    function canAnimate() {
        return visible && !document.hidden && !paused && !hovering && !dragging &&
            document.activeElement !== rail && !document.body.style.overflow;
    }

    function animate(time) {
        frame = 0;
        if (!canAnimate()) return;
        const elapsed = previousTime ? Math.min(time - previousTime, 50) : 0;
        previousTime = time;
        const end = rail.scrollWidth - rail.clientWidth;
        if (end > 0 && time >= resumeAt) {
            position += direction * elapsed * 0.026;
            if (position >= end) { position = end; direction = -1; }
            if (position <= 0) { position = 0; direction = 1; }
            rail.scrollLeft = position;
        }
        frame = requestAnimationFrame(animate);
    }

    function refresh() {
        if (frame) cancelAnimationFrame(frame);
        frame = 0;
        previousTime = 0;
        position = rail.scrollLeft;
        if (canAnimate()) frame = requestAnimationFrame(animate);
    }

    function manualInteraction() {
        resumeAt = performance.now() + 4000;
        position = rail.scrollLeft;
    }

    toggle.addEventListener('click', () => {
        paused = !paused;
        updateToggle();
        refresh();
    });
    rail.addEventListener('pointerenter', event => {
        if (event.pointerType === 'mouse') { hovering = true; refresh(); }
    });
    rail.addEventListener('pointerleave', event => {
        if (event.pointerType === 'mouse') { hovering = false; refresh(); }
    });
    rail.addEventListener('pointerdown', event => {
        if (event.button !== 0) return;
        dragging = true;
        manualInteraction();
        if (event.pointerType === 'mouse') {
            startX = event.clientX;
            startScroll = rail.scrollLeft;
            rail.setPointerCapture(event.pointerId);
            rail.classList.add('is-dragging');
            event.preventDefault();
        }
        refresh();
    });
    rail.addEventListener('pointermove', event => {
        if (dragging && event.pointerType === 'mouse') {
            rail.scrollLeft = startScroll - (event.clientX - startX);
            position = rail.scrollLeft;
        }
    });
    function endDrag() {
        if (!dragging) return;
        dragging = false;
        rail.classList.remove('is-dragging');
        manualInteraction();
        refresh();
    }
    window.addEventListener('pointerup', endDrag);
    window.addEventListener('pointercancel', endDrag);
    rail.addEventListener('lostpointercapture', endDrag);
    rail.addEventListener('scroll', () => {
        if (Math.abs(rail.scrollLeft - position) > 1) manualInteraction();
    }, { passive: true });
    rail.addEventListener('wheel', manualInteraction, { passive: true });
    rail.addEventListener('focus', refresh);
    rail.addEventListener('blur', refresh);
    document.addEventListener('visibilitychange', refresh);
    // Resume after a modal restores page scrolling, without a global animation loop.
    new MutationObserver(refresh).observe(document.body, { attributes: true, attributeFilter: ['style'] });
    new IntersectionObserver(entries => {
        visible = entries[0].isIntersecting;
        refresh();
    }).observe(rail);
    new ResizeObserver(refresh).observe(rail);
    reducedMotion.addEventListener('change', () => {
        paused = reducedMotion.matches;
        updateToggle();
        refresh();
    });
    updateToggle();
})();
