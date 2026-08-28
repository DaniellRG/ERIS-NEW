// Gallery Testgaleria
const images = [
    { src: 'https://picsum.photos/seed/n1/800/600', cat: 'naturaleza', title: 'Naturaleza' },
    { src: 'https://picsum.photos/seed/n2/800/600', cat: 'naturaleza', title: 'Bosque' },
    { src: 'https://picsum.photos/seed/c1/800/600', cat: 'ciudad', title: 'Ciudad' },
    { src: 'https://picsum.photos/seed/c2/800/600', cat: 'ciudad', title: 'Arquitectura' },
    { src: 'https://picsum.photos/seed/a1/800/600', cat: 'arte', title: 'Arte Digital' },
    { src: 'https://picsum.photos/seed/a2/800/600', cat: 'arte', title: 'Escultura' },
    { src: 'https://picsum.photos/seed/n3/800/600', cat: 'naturaleza', title: 'Montañas' },
    { src: 'https://picsum.photos/seed/c3/800/600', cat: 'ciudad', title: 'Noche' },
    { src: 'https://picsum.photos/seed/a3/800/600', cat: 'arte', title: 'Pintura' },
];
let currentFilter = 'all';
function renderGallery() {
    const grid = document.getElementById('galleryGrid');
    const filtered = currentFilter === 'all' ? images : images.filter(i => i.cat === currentFilter);
    grid.innerHTML = filtered.map(img => `
        <div class="col-md-4 gallery-item" onclick="openLightbox('${img.src}')">
            <img src="${img.src}" alt="${img.title}" loading="lazy">
            <div class="overlay"><h5>${img.title}</h5></div>
        </div>
    `).join('');
}
function openLightbox(src) {
    document.getElementById('lightboxImg').src = src;
    document.getElementById('lightbox').classList.add('active');
}
document.querySelectorAll('[data-filter]').forEach(el => {
    el.addEventListener('click', () => {
        document.querySelectorAll('[data-filter]').forEach(e => e.classList.remove('active'));
        el.classList.add('active');
        currentFilter = el.dataset.filter;
        renderGallery();
    });
});
document.addEventListener('DOMContentLoaded', renderGallery);
