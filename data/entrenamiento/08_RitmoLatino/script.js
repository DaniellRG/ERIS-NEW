// RitmoLatino - Animations & 3D
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
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}<\/script>
<script type="module">
import * as THREE from 'three';
const scene=new THREE.Scene(),cam=new THREE.PerspectiveCamera(75,window.innerWidth/window.innerHeight,0.1,1000);
const ren=new THREE.WebGLRenderer({alpha:true});ren.setSize(window.innerWidth,window.innerHeight);
ren.domElement.style.cssText='position:fixed;top:0;left:0;z-index:0;pointer-events:none;';
document.body.prepend(ren.domElement);
const geo=new THREE.BufferGeometry(),count=2000;
const pos=new Float32Array(count*3);for(let i=0;i<count*3;i++)pos[i]=(Math.random()-0.5)*200;
geo.setAttribute('position',new THREE.BufferAttribute(pos,3));
const mat=new THREE.PointsMaterial({color:'#f59e0b',size:0.3,transparent:true,opacity:0.6});
const pts=new THREE.Points(geo,mat);scene.add(pts);
cam.position.z=50;
function anim(){requestAnimationFrame(anim);pts.rotation.y+=0.0005;pts.rotation.x+=0.0003;ren.render(scene,cam);}
anim();
window.addEventListener('resize',()=>{cam.aspect=window.innerWidth/window.innerHeight;cam.updateProjectionMatrix();ren.setSize(window.innerWidth,window.innerHeight);});
<\/script>