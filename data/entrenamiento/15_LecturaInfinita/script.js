// LecturaInfinita - Animations & 3D
document.addEventListener('DOMContentLoaded', () => {
    AOS.init({ duration: 800, once: true, easing: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)' });

    const form = document.getElementById('contactForm');
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (form.checkValidity()) {
                showToast('Mensaje enviado correctamente.');
                form.reset();
            }
            form.classList.add('was-validated');
        });
    }

    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            e.preventDefault();
            const t = document.querySelector(a.getAttribute('href'));
            if (t) t.scrollIntoView({ behavior: 'smooth' });
        });
    });
});

function showToast(msg) {
    const t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;bottom:2rem;right:2rem;background:#14b8a6;color:white;padding:1rem 2rem;border-radius:16px;z-index:9999;transform:translateY(100px);opacity:0;transition:all 0.4s ease;';
    document.body.appendChild(t);
    requestAnimationFrame(() => { t.style.transform = 'translateY(0)'; t.style.opacity = '1'; });
    setTimeout(() => { t.style.transform = 'translateY(100px)'; t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 3000);
}

// 3D Effect
<div id="orb3d"></div>
<style>
#orb3d{position:fixed;top:50%;left:50%;width:600px;height:600px;transform:translate(-50%,-50%);z-index:0;pointer-events:none;
background:radial-gradient(circle at 30% 30%,'#14b8a6','#0d9488',transparent 70%);
border-radius:50%;filter:blur(60px);opacity:0.3;animation:orbPulse 8s ease-in-out infinite;}
@keyframes orbPulse{0%,100%{transform:translate(-50%,-50%) scale(1);opacity:0.3;}50%{transform:translate(-50%,-50%) scale(1.3);opacity:0.5;}}
</style>