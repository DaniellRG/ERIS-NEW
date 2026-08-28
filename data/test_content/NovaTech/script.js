// NovaTech - Animations & 3D
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
    t.style.cssText = 'position:fixed;bottom:2rem;right:2rem;background:#f59e0b;color:white;padding:1rem 2rem;border-radius:16px;z-index:9999;transform:translateY(100px);opacity:0;transition:all 0.4s ease;';
    document.body.appendChild(t);
    requestAnimationFrame(() => { t.style.transform = 'translateY(0)'; t.style.opacity = '1'; });
    setTimeout(() => { t.style.transform = 'translateY(100px)'; t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 3000);
}

// 3D Effect
<div id="shapes3d"></div>
<style>
#shapes3d{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;overflow:hidden;perspective:800px;}
.shape3d{position:absolute;border-radius:50%;opacity:0.15;animation:shapeFloat 20s infinite ease-in-out;transform-style:preserve-3d;}
@keyframes shapeFloat{0%,100%{transform:translateY(0) rotateX(0deg) rotateY(0deg) scale(1);}25%{transform:translateY(-100px) rotateX(45deg) rotateY(90deg) scale(1.2);}50%{transform:translateY(-50px) rotateX(90deg) rotateY(180deg) scale(0.8);}75%{transform:translateY(-150px) rotateX(135deg) rotateY(270deg) scale(1.1);}}
</style>
<script>
(function(){const colors=['#f59e0b','#f97316','#ef4444'];const shapes=document.getElementById('shapes3d');
for(let i=0;i<12;i++){const d=document.createElement('div');d.className='shape3d';
const s=40+Math.random()*120;d.style.width=s+'px';d.style.height=s+'px';
d.style.left=Math.random()*100+'%';d.style.top=Math.random()*100+'%';
d.style.background=colors[i%3];d.style.animationDelay=i*1.5+'s';
d.style.animationDuration=(15+Math.random()*15)+'s';
const shape=Math.random();if(shape<0.33)d.style.borderRadius='50%';
else if(shape<0.66)d.style.borderRadius='30%';else d.style.clipPath='polygon(50% 0%,100% 50%,50% 100%,0% 50%)';
shapes.appendChild(d);}})();
<\/script>