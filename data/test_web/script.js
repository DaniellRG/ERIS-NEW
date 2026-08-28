// PruebaERIS — JavaScript
document.addEventListener('DOMContentLoaded', () => {
    // Particles
    const colors = ['#a78bfa','#60a5fa','#f472b6','#34d399','#fbbf24'];
    for (let i = 0; i < 40; i++) {
        const p = document.createElement('div');
        p.style.cssText = 'position:fixed;width:3px;height:3px;border-radius:50%;pointer-events:none;z-index:0;'
            + 'left:' + Math.random()*100 + '%;top:100%;'
            + 'background:' + colors[Math.floor(Math.random()*colors.length)] + ';'
            + 'animation:float ' + (15+Math.random()*15) + 's linear infinite;'
            + 'animation-delay:' + Math.random()*10 + 's;';
        document.body.appendChild(p);
    }

    // Scroll animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(e => e.isIntersecting && e.target.classList.add('visible'));
    }, { threshold: 0.1 });
    document.querySelectorAll('.feature-card, h2, .card').forEach(el => {
        el.classList.add('fade-in');
        observer.observe(el);
    });

    // Form
    const form = document.getElementById('contactForm');
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (form.checkValidity()) {
                alert('Mensaje enviado correctamente.');
                form.reset();
            }
            form.classList.add('was-validated');
        });
    }

    // Smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            e.preventDefault();
            const t = document.querySelector(a.getAttribute('href'));
            if (t) t.scrollIntoView({ behavior: 'smooth' });
        });
    });
});
