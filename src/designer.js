const viewport = document.getElementById('bellViewport');
const status = document.getElementById('modelStatus');
const textInput = document.getElementById('bellText');
const sizeInput = document.getElementById('letterSize');
const styleInput = document.getElementById('letterStyle');
const positionInput = document.getElementById('letterPosition');
const saveButton = document.getElementById('saveSketch');

function showError(message) {
    status.hidden = false;
    status.classList.add('is-error');
    status.textContent = message;
}

// The geometry and fixed artwork are created once; only the skirt texture changes.
async function initialize() {
    const THREE = await import('three');
    const { OrbitControls } = await import('./vendor/three/OrbitControls.js');
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.5;
    renderer.domElement.setAttribute('aria-hidden', 'true');
    viewport.append(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.95, 0);
    controls.enablePan = false;
    controls.minDistance = 3.6;
    controls.maxDistance = 9;
    controls.minPolarAngle = 0.2;
    controls.maxPolarAngle = Math.PI * 0.84;
    controls.enableDamping = true;
    controls.dampingFactor = 0.09;
    let dirty = true;
    let visible = true;
    let frame = 0;
    const model = new THREE.Group();
    scene.add(model);

    // A small generated studio environment keeps the demo local and lightweight.
    const studio = document.createElement('canvas');
    studio.width = 1024;
    studio.height = 512;
    const studioContext = studio.getContext('2d');
    const glow = studioContext.createLinearGradient(0, 0, 0, 512);
    glow.addColorStop(0, '#e7e0cb');
    glow.addColorStop(0.45, '#777568');
    glow.addColorStop(1, '#302f28');
    studioContext.fillStyle = glow;
    studioContext.fillRect(0, 0, 1024, 512);
    for (const [x, width, color] of [[60, 100, '#fff9e9'], [470, 48, '#ffffff'], [790, 160, '#b6b9ae']]) {
        studioContext.fillStyle = color;
        studioContext.fillRect(x, 40, width, 350);
    }
    const environment = new THREE.CanvasTexture(studio);
    environment.mapping = THREE.EquirectangularReflectionMapping;
    environment.colorSpace = THREE.SRGBColorSpace;
    const pmrem = new THREE.PMREMGenerator(renderer);
    const environmentTarget = pmrem.fromEquirectangular(environment);
    scene.environment = environmentTarget.texture;
    environment.dispose();
    pmrem.dispose();
    scene.add(new THREE.HemisphereLight(0xfff3d7, 0x534f44, 2));
    const key = new THREE.DirectionalLight(0xfff0d2, 4);
    key.position.set(-3, 5, 4);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xe1edff, 2.5);
    rim.position.set(3, 2, -3);
    scene.add(rim);

    const brass = new THREE.MeshStandardMaterial({ color: 0xb59a59, metalness: 0.91, roughness: 0.34 });
    const darkMetal = new THREE.MeshStandardMaterial({ color: 0x5d5340, metalness: 0.87, roughness: 0.44 });
    // Approximate turned profile from img/gerbvalday.jpg. No real dimensions assumed.
    const profile = [
        [1.035, 0.045], [1.09, 0.005], [1.13, 0.012], [1.145, 0.05],
        [1.128, 0.09], [1.095, 0.14], [1.02, 0.38], [0.975, 0.49],
        [0.958, 0.53], [0.976, 0.56], [0.972, 0.59], [0.933, 0.63],
        [0.904, 0.65], [0.885, 0.69], [0.868, 0.74], [0.845, 0.78],
        [0.823, 0.82], [0.79, 1.02], [0.746, 1.34], [0.71, 1.58],
        [0.695, 1.66], [0.66, 1.72], [0.56, 1.77], [0.34, 1.805], [0, 1.815],
    ];
    function lathe(points, material) {
        const geometry = new THREE.LatheGeometry(points.map(([r, y]) => new THREE.Vector2(r, y)), 128);
        geometry.rotateY(Math.PI);
        const mesh = new THREE.Mesh(geometry, material);
        model.add(mesh);
        return mesh;
    }
    const surface = lathe(profile, darkMetal.clone());
    const uv = surface.geometry.attributes.uv;
    const positions = surface.geometry.attributes.position;
    for (let i = 0; i < uv.count; i++) uv.setY(i, positions.getY(i) / 1.815);
    uv.needsUpdate = true;
    surface.material.side = THREE.DoubleSide;

    // Inner shell and clapper make the bell readable from below, too.
    const interior = lathe([[0, 1.68], [0.57, 1.62], [0.69, 1.25], [0.77, 0.8], [0.92, 0.4], [1.035, 0.045]], darkMetal);
    interior.material.side = THREE.DoubleSide;
    function ring(radius, y, tube = 0.018) {
        const mesh = new THREE.Mesh(new THREE.TorusGeometry(radius, tube, 10, 128), brass);
        mesh.rotation.x = Math.PI / 2;
        mesh.position.y = y;
        model.add(mesh);
    }
    ring(1.127, 0.064, 0.018);
    ring(0.967, 0.57, 0.015);
    ring(0.889, 0.705, 0.014);
    ring(0.696, 1.665, 0.013);
    const attachment = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.125, 0.31, 48), darkMetal);
    attachment.position.y = 1.96;
    model.add(attachment);
    const attachmentCap = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.018, 48), brass);
    attachmentCap.position.y = 2.123;
    model.add(attachmentCap);
    const suspension = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.019, 12, 64), brass);
    suspension.rotation.x = Math.PI / 2;
    suspension.rotation.y = 0.25;
    suspension.position.y = 1.94;
    model.add(suspension);
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.034, 1.15, 16), darkMetal);
    stem.position.y = 0.83;
    model.add(stem);
    const clapper = new THREE.Mesh(new THREE.SphereGeometry(0.105, 24, 16), brass);
    clapper.position.set(0, 0.22, 0);
    model.add(clapper);

    function canvasTexture(canvas) {
        const texture = new THREE.CanvasTexture(canvas);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
        return texture;
    }

    // Draw fixed ornament and a masked fragment of the actual Valday crest photo.
    const fixedCanvas = document.createElement('canvas');
    fixedCanvas.width = 2048;
    fixedCanvas.height = 1024;
    const fixed = fixedCanvas.getContext('2d');
    const pixels = fixed.createImageData(2048, 1024);
    let seed = 72471;
    for (let i = 0; i < pixels.data.length; i += 4) {
        seed = (Math.imul(seed, 1664525) + 1013904223) | 0;
        const grain = ((seed >>> 24) / 255 - 0.5) * 15;
        pixels.data[i] = 68 + grain;
        pixels.data[i + 1] = 60 + grain;
        pixels.data[i + 2] = 43 + grain;
        pixels.data[i + 3] = 255;
    }
    fixed.putImageData(pixels, 0, 0);
    function ornament(y, amplitude, count) {
        fixed.strokeStyle = '#b99c59';
        fixed.lineWidth = 4;
        fixed.beginPath();
        for (let x = 0; x <= 2048; x += 2) {
            const yy = y + Math.sin(x / 2048 * Math.PI * 2 * count) * amplitude;
            if (x === 0) fixed.moveTo(x, yy); else fixed.lineTo(x, yy);
        }
        fixed.stroke();
    }
    ornament(1000, 9, 28);
    ornament(674, 9, 28);
    ornament(652, 5, 28);
    ornament(80, 7, 24);
    const original = await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('Reference image unavailable'));
        img.src = new URL('../img/gerbvalday.jpg', import.meta.url).href;
    });
    const crestCanvas = document.createElement('canvas');
    crestCanvas.width = 400;
    crestCanvas.height = 400;
    const crest = crestCanvas.getContext('2d', { willReadFrequently: true });
    crest.drawImage(original, 260, 228, 270, 235, 0, 0, 400, 400);
    const mask = crest.getImageData(0, 0, 400, 400);
    for (let i = 0; i < mask.data.length; i += 4) {
        const r = mask.data[i], g = mask.data[i + 1], b = mask.data[i + 2];
        const gold = Math.min((r - 80) / 60, (g - b - 4) / 28);
        mask.data[i] = 199;
        mask.data[i + 1] = 170;
        mask.data[i + 2] = 108;
        mask.data[i + 3] = Math.max(0, Math.min(1, gold)) * 255;
    }
    crest.putImageData(mask, 0, 0);
    fixed.drawImage(crestCanvas, 745, 142, 558, 440);
    // Back lettering belongs to the fixed design, independently of the skirt.
    fixed.fillStyle = '#bfa467';
    fixed.textAlign = 'center';
    fixed.font = '52px Georgia';
    fixed.fillText('ДАР', 175, 340);
    fixed.fillText('ВАЛДАЯ', 175, 405);
    surface.material.map = canvasTexture(fixedCanvas);
    surface.material.color.set(0xffffff);
    surface.material.metalness = 0.86;
    surface.material.roughness = 0.41;
    surface.material.needsUpdate = true;

    const letteringCanvas = document.createElement('canvas');
    letteringCanvas.width = 4096;
    letteringCanvas.height = 384;
    const letteringContext = letteringCanvas.getContext('2d');
    const letteringTexture = canvasTexture(letteringCanvas);
    const letteringMaterial = new THREE.MeshStandardMaterial({
        map: letteringTexture, transparent: true, metalness: 0.8, roughness: 0.35,
        depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2,
    });
    const skirt = new THREE.Mesh(new THREE.CylinderGeometry(0.995, 1.115, 0.34, 128, 1, true), letteringMaterial);
    skirt.position.y = 0.29;
    skirt.rotation.y = Math.PI;
    model.add(skirt);

    function updateLettering() {
        const text = textInput.value.replace(/\s+/g, ' ').trim();
        document.getElementById('textCount').textContent = `${textInput.value.length} / 64`;
        letteringContext.clearRect(0, 0, 4096, 384);
        const italic = styleInput.value === 'italic' ? 'italic ' : '';
        let fontSize = Number(sizeInput.value);
        letteringContext.font = `${italic}600 ${fontSize}px 'Cormorant Garamond', Georgia, serif`;
        const width = letteringContext.measureText(text).width;
        if (width > 3500) fontSize *= 3500 / width;
        letteringContext.font = `${italic}600 ${fontSize}px 'Cormorant Garamond', Georgia, serif`;
        letteringContext.fillStyle = '#d8b66c';
        letteringContext.textAlign = 'center';
        letteringContext.textBaseline = 'middle';
        letteringContext.fillText(text, 2048, 192);
        letteringTexture.needsUpdate = true;
        skirt.rotation.y = Math.PI + Number(positionInput.value) * Math.PI / 180;
        viewport.dataset.inscription = text;
        dirty = true;
    }

    function render() {
        frame = 0;
        if (!visible || document.hidden) return;
        if (controls.update()) dirty = true;
        if (dirty) { renderer.render(scene, camera); dirty = false; }
        frame = requestAnimationFrame(render);
    }
    function resume() {
        if (frame) cancelAnimationFrame(frame);
        frame = 0;
        if (visible && !document.hidden) { dirty = true; frame = requestAnimationFrame(render); }
    }
    // Slightly off-axis default view shows the curvature without hiding the crest.
    camera.position.set(0.7, 2.35, 5.6);
    controls.update();
    controls.saveState();
    document.getElementById('resetView').addEventListener('click', () => { controls.reset(); model.rotation.set(0, 0, 0); dirty = true; });
    function turn(amount) { model.rotation.y += amount; dirty = true; }
    document.getElementById('turnLeft').addEventListener('click', () => turn(-Math.PI / 8));
    document.getElementById('turnRight').addEventListener('click', () => turn(Math.PI / 8));
    viewport.addEventListener('keydown', event => {
        if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '-', '='].includes(event.key)) {
            event.preventDefault();
            if (event.key === 'ArrowLeft') turn(-Math.PI / 12);
            else if (event.key === 'ArrowRight') turn(Math.PI / 12);
            else {
                const offset = camera.position.clone().sub(controls.target);
                const zoomIn = ['+', '=', 'ArrowUp'].includes(event.key);
                offset.setLength(THREE.MathUtils.clamp(offset.length() * (zoomIn ? 0.92 : 1.08), controls.minDistance, controls.maxDistance));
                camera.position.copy(controls.target).add(offset);
                dirty = true;
            }
        }
    });
    for (const input of [textInput, sizeInput, styleInput, positionInput]) input.addEventListener('input', updateLettering);
    document.querySelectorAll('[data-phrase]').forEach(button => button.addEventListener('click', () => {
        textInput.value = button.dataset.phrase;
        updateLettering();
    }));
    saveButton.addEventListener('click', () => {
        renderer.render(scene, camera);
        renderer.domElement.toBlob(blob => {
            if (!blob) { showError('Не удалось сохранить эскиз. Попробуйте ещё раз.'); return; }
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'valday-bell-sketch.png';
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        }, 'image/png');
    });
    const resize = new ResizeObserver(() => {
        const { width, height } = viewport.getBoundingClientRect();
        if (!width || !height) return;
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        dirty = true;
    });
    resize.observe(viewport);
    new IntersectionObserver(entries => { visible = entries[0].isIntersecting; resume(); }).observe(viewport);
    document.addEventListener('visibilitychange', resume);
    renderer.domElement.addEventListener('webglcontextlost', event => {
        event.preventDefault();
        visible = false;
        resume();
        saveButton.disabled = true;
        showError('3D-просмотр остановлен браузером. Обновите страницу, чтобы восстановить эскиз.');
    });
    await Promise.allSettled([
        document.fonts.load("600 190px 'Cormorant Garamond'"),
        document.fonts.load("italic 600 190px 'Cormorant Garamond'"),
    ]);
    updateLettering();
    status.hidden = true;
    saveButton.disabled = false;
    viewport.dataset.modelReady = 'true';
    resume();
}

initialize().catch(error => {
    console.error('Bell designer:', error);
    showError('Не удалось открыть 3D-просмотр. Откройте страницу через локальный HTTP-сервер и проверьте поддержку WebGL в браузере.');
});
