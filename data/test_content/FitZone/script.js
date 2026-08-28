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
    t.style.cssText = 'position:fixed;bottom:2rem;right:2rem;background:#7c3aed;color:white;padding:1rem 2rem;border-radius:16px;z-index:9999;transform:translateY(100px);opacity:0;transition:all 0.4s ease;';
    document.body.appendChild(t);
    requestAnimationFrame(() => { t.style.transform = 'translateY(0)'; t.style.opacity = '1'; });
    setTimeout(() => { t.style.transform = 'translateY(100px)'; t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 3000);
}

// 3D Effect
<div id="blobs"></div>
<style>
#blobs{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;overflow:hidden;}
.blob{position:absolute;border-radius:50%;filter:blur(80px);opacity:0.15;animation:blobMove 25s infinite alternate;}
@keyframes blobMove{0%{transform:translate(0,0) scale(1);}100%{transform:translate(200px,-200px) scale(1.5);}}
</style>
<script>(function(){const c=['#7c3aed','#6366f1','#f472b6'];const b=document.getElementById('blobs');
for(let i=0;i<5;i++){const d=document.createElement('div');d.className='blob';
const s=200+Math.random()*400;d.style.width=s+'px';d.style.height=s+'px';
d.style.background=c[i%3];d.style.left=Math.random()*80+'%';d.style.top=Math.random()*80+'%';
d.style.animationDuration=(15+Math.random()*15)+'s';d.style.animationDelay=i*2+'s';
b.appendChild(d);}})();
<\/script>