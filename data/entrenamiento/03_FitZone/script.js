// FitZone - Animations & 3D
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
    t.style.cssText = 'position:fixed;bottom:2rem;right:2rem;background:#0ea5e9;color:white;padding:1rem 2rem;border-radius:16px;z-index:9999;transform:translateY(100px);opacity:0;transition:all 0.4s ease;';
    document.body.appendChild(t);
    requestAnimationFrame(() => { t.style.transform = 'translateY(0)'; t.style.opacity = '1'; });
    setTimeout(() => { t.style.transform = 'translateY(100px)'; t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 3000);
}

// 3D Effect
<div id="gridbg"></div>
<style>
#gridbg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;
background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,0.03) 1px,transparent 1px);
background-size:50px 50px;animation:gridMove 20s linear infinite;}
@keyframes gridMove{0%{transform:translate(0,0);}100%{transform:translate(50px,50px);}}
</style>