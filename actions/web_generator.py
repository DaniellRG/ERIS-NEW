"""
actions/web_generator.py — Generador de paginas web unicas con IA de diseno.
Cada pagina es diferente: colores, fuentes, layouts, animaciones, 3D.
Aprende de lo que genera y guarda en memoria para no repetirse.
"""
import json
import os
import random
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_FILE = _BASE_DIR / "data" / "web_generator_memory.json"

# ── Color Palettes ──────────────────────────────────────────────────────────
PALETTES = [
    {"primary": "#7c3aed", "secondary": "#6366f1", "accent": "#f472b6", "bg": "#0a0a0f", "card": "rgba(255,255,255,0.03)", "text": "#e0e0e0", "name": "purple-cosmic"},
    {"primary": "#06b6d4", "secondary": "#0891b2", "accent": "#2dd4bf", "bg": "#0f172a", "card": "rgba(255,255,255,0.03)", "text": "#e2e8f0", "name": "cyan-deep"},
    {"primary": "#f59e0b", "secondary": "#f97316", "accent": "#ef4444", "bg": "#1c1917", "card": "rgba(255,255,255,0.03)", "text": "#fafafa", "name": "amber-warm"},
    {"primary": "#10b981", "secondary": "#059669", "accent": "#34d399", "bg": "#0f1a14", "card": "rgba(255,255,255,0.03)", "text": "#d1fae5", "name": "emerald-forest"},
    {"primary": "#ec4899", "secondary": "#db2777", "accent": "#f43f5e", "bg": "#130a0f", "card": "rgba(255,255,255,0.03)", "text": "#fce7f3", "name": "pink-rose"},
    {"primary": "#3b82f6", "secondary": "#2563eb", "accent": "#60a5fa", "bg": "#0a0f1a", "card": "rgba(255,255,255,0.03)", "text": "#dbeafe", "name": "blue-ocean"},
    {"primary": "#a855f7", "secondary": "#d946ef", "accent": "#e879f9", "bg": "#0f0a1a", "card": "rgba(255,255,255,0.03)", "text": "#f3e8ff", "name": "violet-neon"},
    {"primary": "#f97316", "secondary": "#dc2626", "accent": "#fbbf24", "bg": "#1a0f0a", "card": "rgba(255,255,255,0.03)", "text": "#fff7ed", "name": "sunset"},
    {"primary": "#14b8a6", "secondary": "#0d9488", "accent": "#5eead4", "bg": "#0a1412", "card": "rgba(255,255,255,0.03)", "text": "#ccfbf1", "name": "teal-aurora"},
    {"primary": "#8b5cf6", "secondary": "#a78bfa", "accent": "#c4b5fd", "bg": "#0a0a14", "card": "rgba(255,255,255,0.03)", "text": "#ede9fe", "name": "indigo-twilight"},
    {"primary": "#e11d48", "secondary": "#be123c", "accent": "#fb7185", "bg": "#140a0c", "card": "rgba(255,255,255,0.03)", "text": "#ffe4e6", "name": "ruby"},
    {"primary": "#0ea5e9", "secondary": "#0284c7", "accent": "#7dd3fc", "bg": "#0a121a", "card": "rgba(255,255,255,0.03)", "text": "#e0f2fe", "name": "sky"},
    {"primary": "#84cc16", "secondary": "#65a30d", "accent": "#a3e635", "bg": "#0e130a", "card": "rgba(255,255,255,0.03)", "text": "#ecfccb", "name": "lime"},
    {"primary": "#d946ef", "secondary": "#c026d3", "accent": "#f0abfc", "bg": "#100a12", "card": "rgba(255,255,255,0.03)", "text": "#fae8ff", "name": "magenta"},
    {"primary": "#f43f5e", "secondary": "#e11d48", "accent": "#fb7185", "bg": "#120a0b", "card": "rgba(255,255,255,0.03)", "text": "#ffe4e6", "name": "crimson"},
]

# ── Google Fonts pairs ──────────────────────────────────────────────────────
FONTS = [
    ("Inter", "Inter:ital,opsz,wght@0,14..32,100..900"),
    ("Poppins", "Poppins:wght@300;400;600;700;800"),
    ("Space+Grotesk", "Space+Grotesk:wght@300;400;500;700"),
    ("Outfit", "Outfit:wght@200;300;400;600;700;800"),
    ("DM+Sans", "DM+Sans:ital,opsz,wght@0,9..40,100..1000"),
    ("Plus+Jakarta+Sans", "Plus+Jakarta+Sans:wght@200;300;400;500;600;700;800"),
    ("Sora", "Sora:wght@100;200;300;400;600;700;800"),
    ("Clash+Grotesk", "Clash+Grotesk:wght@200;300;400;500;600;700"),
    ("Cabinet+Grotesk", "Cabinet+Grotesk:wght@100;200;300;400;500;700;800"),
    ("Syne", "Syne:wght@400;500;600;700;800"),
    ("Epilogue", "Epilogue:ital,wght@0,100..900"),
    ("Be+Vietnam+Pro", "Be+Vietnam+Pro:wght@100;200;300;400;500;600;700;800"),
    ("Archivo", "Archivo:ital,wght@0,100..900"),
    ("Figtree", "Figtree:ital,wght@0,300..900"),
    ("Manrope", "Manrope:wght@200;300;400;500;600;700;800"),
]

# ── Hero layouts ────────────────────────────────────────────────────────────
HERO_LAYOUTS = ["center", "left", "gradient_radial", "split", "minimal"]

# ── 3D effects ──────────────────────────────────────────────────────────────
THREE_EFFECTS = [
    """<div id="orb3d"></div><style>#orb3d{position:fixed;top:50%;left:50%;width:600px;height:600px;transform:translate(-50%,-50%);z-index:0;pointer-events:none;background:radial-gradient(circle at 30% 30%,PRI_COLOR,SEC_COLOR,transparent 70%);border-radius:50%;filter:blur(60px);opacity:0.3;animation:orbPulse 8s ease-in-out infinite;}@keyframes orbPulse{0%,100%{transform:translate(-50%,-50%) scale(1);opacity:0.3;}50%{transform:translate(-50%,-50%) scale(1.3);opacity:0.5;}}</style>""",
    """<div id="gridbg"></div><style>#gridbg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.03) 1px,transparent 1px);background-size:50px 50px;animation:gridMove 20s linear infinite;}@keyframes gridMove{0%{transform:translate(0,0);}100%{transform:translate(50px,50px);}}</style>""",
    """<div id="blobs"></div><style>#blobs{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;overflow:hidden;}.blob{position:absolute;border-radius:50%;filter:blur(80px);opacity:0.15;animation:blobMove 25s infinite alternate;}@keyframes blobMove{0%{transform:translate(0,0) scale(1);}100%{transform:translate(200px,-200px) scale(1.5);}}</style><script>(function(){var c=['PRI_COLOR','SEC_COLOR','ACC_COLOR'];var b=document.getElementById('blobs');for(var i=0;i<5;i++){var d=document.createElement('div');d.className='blob';var s=200+Math.random()*400;d.style.width=s+'px';d.style.height=s+'px';d.style.background=c[i%3];d.style.left=Math.random()*80+'%';d.style.top=Math.random()*80+'%';d.style.animationDuration=(15+Math.random()*15)+'s';d.style.animationDelay=i*2+'s';b.appendChild(d);}})();</script>""",
    """<div id="shapes3d"></div><style>#shapes3d{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;overflow:hidden;perspective:800px;}.shape3d{position:absolute;border-radius:50%;opacity:0.10;animation:shapeFloat 25s infinite ease-in-out;transform-style:preserve-3d;}@keyframes shapeFloat{0%,100%{transform:translateY(0) rotateX(0deg) rotateY(0deg) scale(1);}25%{transform:translateY(-100px) rotateX(45deg) rotateY(90deg) scale(1.2);}50%{transform:translateY(-50px) rotateX(90deg) rotateY(180deg) scale(0.8);}75%{transform:translateY(-150px) rotateX(135deg) rotateY(270deg) scale(1.1);}}</style><script>(function(){var cs=['PRI_COLOR','SEC_COLOR','ACC_COLOR'];var s=document.getElementById('shapes3d');for(var i=0;i<8;i++){var d=document.createElement('div');d.className='shape3d';var sz=40+Math.random()*120;d.style.width=sz+'px';d.style.height=sz+'px';d.style.left=Math.random()*100+'%';d.style.top=Math.random()*100+'%';d.style.background=cs[i%3];d.style.animationDelay=i*2+'s';d.style.animationDuration=(15+Math.random()*15)+'s';if(Math.random()<0.33)d.style.borderRadius='50%';else d.style.borderRadius='30%';s.appendChild(d);}})();</script>""",
    """<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}</script><script type="module">import * as THREE from 'three';const scene=new THREE.Scene(),cam=new THREE.PerspectiveCamera(75,window.innerWidth/window.innerHeight,0.1,1000);const ren=new THREE.WebGLRenderer({alpha:true});ren.setSize(window.innerWidth,window.innerHeight);ren.domElement.style.cssText='position:fixed;top:0;left:0;z-index:0;pointer-events:none;';document.body.prepend(ren.domElement);const geo=new THREE.BufferGeometry(),count=1500;const pos=new Float32Array(count*3);for(let i=0;i<count*3;i++)pos[i]=(Math.random()-0.5)*200;geo.setAttribute('position',new THREE.BufferAttribute(pos,3));const mat=new THREE.PointsMaterial({color:'PRI_COLOR',size:0.3,transparent:true,opacity:0.6});const pts=new THREE.Points(geo,mat);scene.add(pts);cam.position.z=50;function anim(){requestAnimationFrame(anim);pts.rotation.y+=0.0005;pts.rotation.x+=0.0003;ren.render(scene,cam);}anim();window.addEventListener('resize',()=>{cam.aspect=window.innerWidth/window.innerHeight;cam.updateProjectionMatrix();ren.setSize(window.innerWidth,window.innerHeight);});</script>""",
]

# ── Content bundles ─────────────────────────────────────────────────────────
_CONTENT = {
    "tech": {
        "kw": ["tech","ai","software","digital","app","startup","innovation","nova","inteligencia","artificial","transformacion","datos","cloud","blockchain","ia","robot"],
        "feat": [("Rendimiento Extremo","Optimizado con algoritmos de ultima generacion para maxima velocidad y eficiencia."),("Seguridad Total","Encriptacion militar y protocolos avanzados. Tus datos siempre protegidos."),("Escalabilidad Ilimitada","Infraestructura cloud que crece contigo sin limites ni cuellos de botella."),("IA Avanzada","Modelos de machine learning entrenados con millones de datos para predicciones precisas."),("Integracion Total","Conecta con mas de 500 APIs y servicios populares en minutos."),("Analitica en Vivo","Dashboard interactivo con metricas en tiempo real para decisiones informadas.")],
        "test": [("Transformaron nuestra infraestructura por completo. Resultados impresionantes en tiempo record.","Laura M., CTO TechCorp"),("Nuestra productividad aumento 300% desde que implementamos sus soluciones.","Carlos R., CEO InnovaTech"),("El soporte es increible. Siempre disponibles y resolutivos. Altamente recomendados.","Ana G., Directora Digital"),("Implementacion en tiempo record. En dos semanas ya estabamos operativos al 100%.","Pedro S., Lead Developer")],
        "tag": ["Innovacion que transforma el mundo", "Tecnologia con proposito y futuro", "El poder de la inteligencia artificial"],
    },
    "food": {
        "kw": ["food","restaurant","cocina","chef","gastronomy","sabor","cafe","coffee","comida","gourmet","culinario","parrilla","tradicional","colombiana","cocinar","menu","plato","ingrediente"],
        "feat": [("Recetas Originales","Mas de 50 recetas tradicionales con un toque innovador. Cada plato cuenta una historia unica."),("Ingredientes Frescos","Seleccionamos los mejores ingredientes locales y organicos. Del campo a tu mesa."),("Chef Estrella","Nuestros chefs con reconocimiento internacional crean experiencias culinarias inolvidables."),("Maridaje Perfecto","Carta de vinos seleccionada por sommeliers para complementar cada plato."),("Cocina Saludable","Opciones nutritivas y deliciosas. Porque comer bien no esta reñido con disfrutar."),("Ambiente Unico","Espacios disenados para disfrutar cada momento con elegancia y confort.")],
        "test": [("La mejor experiencia gastronomica de mi vida. Cada plato es una obra de arte culinario.","Sofia R., Critica Gastronomica"),("Volvemos cada semana. La calidad y el servicio son siempre excepcionales.","Andres M., Cliente Fiel"),("Celebramos nuestro evento aqui. El menu y el ambiente fueron perfectos.","Carolina y Felipe")],
        "tag": ["Sabor que enamora el paladar", "Arte culinario en cada bocado", "De la tradicion a tu mesa con amor"],
    },
    "fitness": {
        "kw": ["fit","gym","entrenamiento","training","nutrition","fuerza","body","ejercicio","salud","wellness","deporte","atleta","musculo","cardio","yoga"],
        "feat": [("Entrenamiento Personal","Coaches certificados que disenan planes a tu medida para alcanzar tus metas."),("Salud Integral","Monitoreo de signos vitales y rendimiento con tecnologia wearable."),("Nutricion Deportiva","Planes alimenticios de nutricionistas para maximizar tus resultados."),("Clases Grupales","Yoga, spinning, crossfit y mas en un ambiente motivador y energetico."),("App Inteligente","Seguimiento de progreso con IA que adapta las rutinas a tu rendimiento."),("Flexibilidad Total","Abierto 24/7 con horarios adaptables a tu rutina diaria.")],
        "test": [("Perdi 15kg en 3 meses y gane musculo. Los mejores coaches del pais.","Diego A., Transformacion"),("Nunca pense que disfrutaria hacer ejercicio. Ahora es mi parte favorita del dia.","Valentina P., Miembro"),("El plan de nutricion cambio mi relacion con la comida. Resultados increibles.","Mauricio L., Cliente")],
        "tag": ["Transforma tu cuerpo, transforma tu vida", "Tu mejor version te espera", "Fuerza, disciplina y resultados"],
    },
    "art": {
        "kw": ["art","gallery","galeria","arte","contemporary","exhibition","artista","museo","pintura","escultura","obra","vanguard","curaduria","coleccion"],
        "feat": [("Curaduria Experta","Seleccionamos obras de artistas emergentes y consagrados con curaduria profesional."),("Talleres Creativos","Clases de pintura, escultura y arte digital para todas las edades y niveles."),("Visitas Guiadas","Recorridos interactivos que revelan los secretos detras de cada obra."),("Realidad Aumentada","Explora las colecciones desde casa con nuestra app de realidad aumentada."),("Artistas Emergentes","Plataforma de descubrimiento para nuevos talentos latinoamericanos."),("Eventos Exclusivos","Noches de inauguracion con artistas, curadores y coleccionistas privados.")],
        "test": [("Cada visita es una experiencia transformadora. La curaduria es impecable y conmovedora.","Elena M., Critica de Arte"),("Compre mi primera obra aqui. El asesoramiento fue excepcional y el proceso muy facil.","Roberto S., Coleccionista"),("Los talleres son inspiradores. Desperte mi creatividad gracias a los profesores.","Daniela R., Artista")],
        "tag": ["Donde el arte cobra vida y emociona", "Creatividad sin limites ni fronteras", "Expresion que trasciende el tiempo"],
    },
    "travel": {
        "kw": ["travel","viaje","viajero","turismo","aventura","destino","hotel","vuelo","vacaciones","explorar","descubrir","mundo","tour","expedicion"],
        "feat": [("Destinos Exclusivos","Rutas unicas a lugares que no encontraras en guias turisticas tradicionales."),("Viaja Seguro","Asistencia 24/7 y seguro de viaje incluido en todos nuestros paquetes."),("Experiencias Locales","Conectamos con guias nativos para vivir cada destino como un local."),("Ecoturismo","Viajes sostenibles que preservan la naturaleza y benefician comunidades."),("Alojamiento Premium","Hoteles boutique y eco-lodges seleccionados por su encanto y calidad."),("Itinerarios Flexibles","Planes personalizados que se adaptan a tus gustos y ritmo de viaje.")],
        "test": [("El viaje a la Amazonia fue la experiencia mas increible de mi vida. Guias excepcionales.","Sofia T., Aventurera"),("Organizaron todo perfectamente. Solo llegue y disfrute sin preocupaciones.","Andres H., Viajero"),("Conoci lugares que jamas habria encontrado por mi cuenta. Experiencias unicas.","Maria C., Mochilera")],
        "tag": ["Descubre el mundo con otros ojos", "Aventuras que transforman el alma", "Viaja, explora y vive intensamente"],
    },
    "fashion": {
        "kw": ["fashion","moda","style","clothing","ropa","sostenible","disenador","vestido","accesorio","tendencia","elegancia","coleccion"],
        "feat": [("Diseno Exclusivo","Colecciones limitadas de talentos latinoamericanos. Piezas unicas que marcan estilo."),("Moda Sostenible","Materiales organicos y procesos eticos. Vestir bien sin dañar el planeta."),("Taller a Medida","Confeccion artesanal con ajuste perfecto a tu cuerpo y personalidad."),("Asesoria de Estilo","Expertos en moda te ayudan a descubrir y potenciar tu estilo unico."),("Envio Mundial","Entrega express a cualquier pais con empaque sostenible y elegante."),("Club Exclusivo","Membresia con descuentos, previews y eventos privados para miembros.")],
        "test": [("Cada pieza es una obra de arte. La calidad y el diseno son simplemente incomparables.","Daniela R., Fashion Blogger"),("Me hicieron un vestido a medida para mi boda. Quede espectacular.","Valentina A., Novia"),("La ropa es comoda, elegante y sostenible. Justo lo que buscaba conscientemente.","Camila L., Cliente")],
        "tag": ["Tu estilo, tu esencia, tu voz", "Elegancia que trasciende tendencias", "Moda con consciencia y proposito"],
    },
    "education": {
        "kw": ["education","educacion","learn","curso","school","academy","estudio","clase","profesor","certificacion","diploma","carrera","online","aprender"],
        "feat": [("Cursos Premium","Programas de expertos de las mejores universidades del mundo."),("Mentoria Personal","Tutores dedicados que te guian uno a uno durante todo tu aprendizaje."),("Certificacion Internacional","Certificados avalados que impulsan tu carrera profesional globalmente."),("Comunidad Global","Conecta con estudiantes de mas de 50 paises. Networking sin fronteras."),("A tu Ritmo","Acceso vitalicio al contenido. Aprende cuando y donde quieras."),("Bolsa de Trabajo","Conexion directa con empresas partner que buscan nuestros talentos.")],
        "test": [("Consegui trabajo en una startup gracias a los cursos. La mejor inversion de mi vida.","Miguel R., Egresado"),("Los mentores son increibles. Aprendi mas en 3 meses que en 2 anos de universidad.","Carolina S., Estudiante"),("Pude cambiar de carrera gracias a la certificacion. Ahora trabajo en lo que amo.","Andrea L., Alumni")],
        "tag": ["Aprender sin limites ni barreras", "Conocimiento que transforma vidas", "Tu futuro comienza con education"],
    },
    "music": {
        "kw": ["music","musica","ritmo","concert","artist","band","cancion","melodia","festival","sala","grabacion","instrumento","vocal","sonido"],
        "feat": [("Conciertos Unicos","Eventos intimos con artistas emergentes y consagrados en espacios exclusivos."),("Estudio Profesional","Grabacion con equipos de ultima generacion y ingenieros de sonido expertos."),("Clases Musicales","Talleres de instrumentos, canto y produccion con musicos profesionales."),("Artistas Exclusivos","Representacion de talentos latinos con proyeccion internacional."),("Streaming en Vivo","Plataforma propia con sesiones en vivo y mixes exclusivos."),("Eventos y Festivales","Festivales, jam sessions y noches de open mic para toda la comunidad.")],
        "test": [("Grabe mi primer EP aqui. El ingeniero de sonido es un genio creativo.","Lucia M., Cantante"),("Los conciertos intimos son una experiencia unica. Cerca del artista y la musica.","Andres P., Fan"),("Las clases de guitarra cambiaron mi vida. Ahora toco en una banda profesional.","Felipe T., Estudiante")],
        "tag": ["El ritmo que conecta almas", "Musica que inspira y transforma", "Sonidos que llegan al corazon"],
    },
    "photo": {
        "kw": ["photo","fotografia","photography","capture","camara","retrato","lente","imagen","sesion","edicion","boda","evento","paisaje"],
        "feat": [("Sesiones Profesionales","Fotografia de retrato, productos y eventos con equipos de alta gama."),("Edicion Artistica","Postproduccion con estilo unico que transforma imagenes en arte."),("Bodas y Eventos","Cobertura completa de principio a fin. Recuerdos que duran toda la vida."),("Book Personal","Sesiones de modelo, graduacion y corporativas con maquillaje incluido."),("Galeria Digital","Portafolio online interactivo con galeria privada para cada cliente."),("Impresion Fine Art","Impresion en papeles premium con tintas de archivo de alta durabilidad.")],
        "test": [("Las fotos de nuestra boda son espectaculares. Cada vez que las vemos, lloramos de emocion.","Maria y Juan, Recien Casados"),("El book quedo increible. Me ayudo a conseguir mi primer trabajo como modelo.","Sofia L., Modelo"),("Capturaron la esencia de mi producto perfectamente. Vendi mucho mas gracias a ellas.","Andrea M., Emprendedora")],
        "tag": ["Capturamos tu historia en imagenes", "Momentos que se vuelven eternos", "A traves del lente, contamos tu historia"],
    },
    "nature": {
        "kw": ["nature","naturaleza","plants","plantas","jardin","verde","eco","organico","jardineria","flores","arboles","huerto","sustentable","vivero"],
        "feat": [("Variedad Unica","Mas de 200 especies de plantas exoticas y nativas seleccionadas por botanicos."),("Riego Inteligente","Sistemas automaticos con sensores de humedad para cuidar tus plantas."),("Decoracion Verde","Asesoria en diseño de interiores con plantas. Transforma tu espacio vital."),("Delivery Ecologico","Entrega a domicilio con empaque biodegradable y plantable."),("Cuidado Personalizado","Guia digital de cuidado para cada planta que llevas a tu hogar."),("Suscripcion Verde","Planta nueva cada mes. Sorpresas que llenan tu hogar de vida.")],
        "test": [("Mis plantas nunca habian estado tan saludables. Los consejos de cuidado son oro.","Valentina R., Amante de Plantas"),("El taller de terrarios fue super divertido. Aprendi mucho y me lleve mi creacion.","Camila A., Asistente"),("Transformaron mi terraza en un jardin urbano hermoso. Mi lugar favorito.","Laura P., Cliente")],
        "tag": ["Naturaleza que transforma tu hogar", "Vida verde en cada rincon", "Conecta con la esencia de la vida"],
    },
    "architecture": {
        "kw": ["architecture","arquitectura","diseno","urban","building","construccion","interiores","espacio","moderno","vivienda","oficina","plano","remodelacion"],
        "feat": [("Diseno Moderno","Proyectos arquitectonicos con lineas limpias y espacios funcionales y elegantes."),("Planos 3D","Visualizaciones fotorrealistas con realidad virtual para ver tu proyecto antes."),("Arquitectura Verde","Edificios sostenibles con certificacion LEED y huella de carbono cero."),("Interiores Personalizados","Diseno de interiores que refleja tu personalidad y forma de vida."),("Gestion de Permisos","Tramitacion completa de permisos municipales. Sin dolores de cabeza."),("Remodelaciones","Transformamos espacios existentes en lugares increibles y funcionales.")],
        "test": [("Disenaron la casa de mis suenos. Superaron todas mis expectativas y mas.","Felipe G., Cliente"),("El proyecto comercial quedo espectacular. Nuestros clientes aman el espacio innovador.","Carolina M., Empresaria"),("La visualizacion 3D nos ayudo a tomar decisiones antes de construir. Increible herramienta.","Andres L., Inversor")],
        "tag": ["Espacios que inspiran y emocionan", "Arquitectura con alma y proposito", "Disenamos el futuro, hoy"],
    },
    "coffee": {
        "kw": ["coffee","cafe","cafetero","beans","granos","barista","espresso","latte","cafeina","colombia","aroma","tostado","filtro","especialidad"],
        "feat": [("Cafe de Especialidad","Granos seleccionados de fincas colombianas con puntuacion superior a 85 puntos."),("Tueste Artesanal","Tostado en lotes pequenos para preservar el perfil unico de cada origen."),("Origen Unico","Trazabilidad completa. Sabes exactamente de que finca viene tu cafe."),("Suscripcion","Cafe fresco tostado y enviado a tu puerta cada semana."),("Cata y Cursos","Talleres de catacion y preparacion para convertirte en barista experto."),("Comercio Justo","Precio justo para productores. Cada taza apoya familias caficultoras.")],
        "test": [("El mejor cafe que he probado fuera de Colombia. Autentico, fresco y delicioso.","James B., Barista Internacional"),("La suscripcion es lo mejor. Cada mes un origen diferente. Una experiencia unica.","Maria C., Suscriptora"),("El curso de barista cambio mi forma de hacer cafe en casa. Ahora soy la barista oficial.","Camila R., Estudiante")],
        "tag": ["El mejor cafe colombiano en tu taza", "De la finca a tu mesa con amor", "Arte liquido en cada sorbo"],
    },
    "pets": {
        "kw": ["pets","mascota","pet","animal","dog","perro","cat","gato","veterinario","accesorios","alimento","cuidado","peluqueria","guarderia"],
        "feat": [("Amor y Cuidado","Profesionales apasionados que tratan a tu mascota como parte de la familia."),("Alimentacion Premium","Alimentos naturales seleccionados por nutricionistas veterinarios."),("Clinica Veterinaria","Equipos de diagnostico avanzado y emergencias 24/7 para tu tranquilidad."),("Peluqueria","Estilistas especializados en razas. Tu mascota luciendo espectacular."),("Guarderia","Hospedaje con camaras, climatizacion y mucho amor."),("Paseos","Paseos grupales supervisados con seguro de responsabilidad civil.")],
        "test": [("Mi perro ama la guarderia. Llega feliz y cansado de jugar. El mejor lugar.","Ana M., Duena de Felix"),("La veterinaria salvo a mi gato Milo. Profesionales increibles y llenos de carino.","Carlos R., Dueno de Milo"),("Los paseadores son responsables y mi perro los adora. Servicio confiable.","Andres G., Cliente")],
        "tag": ["Todo el amor que tu mascota merece", "Ellos son familia, los tratamos como tal", "Cuidado con el corazon"],
    },
    "books": {
        "kw": ["books","book","libro","lectura","libreria","literatura","novela","biblioteca","leer","autor","escritor","club","poesia","cuento","editorial"],
        "feat": [("Catalogo Extenso","Miles de titulos en fisico y digital. Clasicos, bestsellers y joyas ocultas."),("Club de Lectura","Grupos por genero con discusiones moderadas por expertos literarios."),("Autores en Vivo","Eventos con escritores nacionales e internacionales. Firmas y charlas."),("Cafeteria Literaria","Espacio acogedor para leer con cafe de especialidad y jardin."),("Book Box","Caja sorpresa mensual con libro seleccionado para ti y regalos exclusivos."),("Audiolibros","Biblioteca digital con narraciones de actores profesionales.")],
        "test": [("El club de lectura cambio mi vida. Conoci amigos y lei libros increibles.","Valentina R., Miembro"),("La seleccion de libros es exquisita. Siempre encuentro algo nuevo y emocionante.","Mateo G., Lector"),("La book box fue la mejor sorpresa. El libro era perfecto para mi.","Camila A., Suscriptora")],
        "tag": ["Libros que abren puertas a otros mundos", "Aventuras entre paginas que esperan por ti", "Donde las historias cobran vida"],
    },
}

_FALLBACK_FEATS = [
    ("Calidad Premium","Los mas altos estandares de calidad en cada detalle de nuestro servicio."),
    ("Atencion Personalizada","Te conocemos, te entendemos y te ofrecemos soluciones a tu medida."),
    ("Equipo Experto","Profesionales apasionados con anos de experiencia en el sector."),
    ("Confianza y Transparencia","Compromiso genuino en cada interaccion. Tu satisfaccion es nuestra meta."),
    ("Innovacion Constante","Siempre a la vanguardia con las ultimas tendencias y tecnologias."),
    ("Disponibilidad Total","Estamos para ti cuando nos necesitas. Soporte 24/7 los 365 dias."),
]
_FALLBACK_TESTS = [
    ("Superaron todas mis expectativas. Servicio excepcional de principio a fin.","Cliente Satisfecho"),
    ("Profesionalismo y calidad superior. Los recomiendo ampliamente.","Maria G., Cliente Fiel"),
    ("Resultados increibles en tiempo record. Equipo talentoso y dedicado.","Carlos R., Empresario"),
]
_FALLBACK_TAGS = ["Excelencia en cada detalle", "Tu satisfaccion, nuestra mision", "Calidad que marca la diferencia"]

import re
_WORD_RE = re.compile(r"[a-z]+")

def _match_content(title, desc):
    text = (title + " " + desc).lower()
    words = set(_WORD_RE.findall(text))
    best_key = None
    best_score = 0
    for key, bundle in _CONTENT.items():
        score = sum(1 for kw in bundle["kw"] if kw in words)
        if score > best_score:
            best_score = score
            best_key = key
    if best_key and best_score > 0:
        b = _CONTENT[best_key]
        return best_key, b["feat"], b["test"], b["tag"]
    return "custom", _FALLBACK_FEATS, _FALLBACK_TESTS, _FALLBACK_TAGS

# ── Memory system ──────────────────────────────────────────────────────────
def _load_memory():
    try:
        _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _MEMORY_FILE.exists():
            data = json.loads(_MEMORY_FILE.read_text("utf-8"))
            for k in ("used_palettes","used_fonts","used_effects","used_hero_layouts"):
                data.setdefault(k, [])
            data.setdefault("pages_created", 0)
            data.setdefault("history", [])
            return data
    except Exception:
        pass
    return {"used_palettes": [], "used_fonts": [], "used_effects": [], "used_hero_layouts": [], "pages_created": 0, "history": []}

def _save_memory(data):
    try:
        _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass

def _select(items, used_key, memory):
    used = memory.get(used_key, [])
    scored = []
    for item in items:
        key = item[0] if isinstance(item, tuple) else (item["name"] if isinstance(item, dict) else str(item))
        scored.append((used.count(key), item))
    scored.sort(key=lambda x: x[0])
    pool = scored[:max(1, len(scored)//3)]
    chosen = random.choice(pool)[1]
    ckey = chosen[0] if isinstance(chosen, tuple) else (chosen["name"] if isinstance(chosen, dict) else str(chosen))
    used.append(ckey)
    if len(used) > 50:
        used[:] = used[-50:]
    memory[used_key] = used
    _save_memory(memory)
    return chosen

# ── CSS generator ──────────────────────────────────────────────────────────
def _inline_css(p, fname, hlay):
    ga = random.choice(["135deg","45deg","90deg","180deg","225deg","315deg"])
    cr = random.choice(["16px","20px","24px","12px","28px"])
    br = random.choice(["50px","12px","8px","30px","20px"])
    si = random.choice(["0.15","0.2","0.25","0.3","0.1"])
    R, G, B = int(p['primary'][1:3],16), int(p['primary'][3:5],16), int(p['primary'][5:7],16)
    return (f'*{{margin:0;padding:0;box-sizing:border-box;}}'
        f'body{{font-family:"{fname}","Segoe UI",system-ui,sans-serif;background:{p["bg"]};color:{p["text"]};overflow-x:hidden;font-size:16px;line-height:1.6;}}'
        f'a{{color:inherit;text-decoration:none;}}img{{max-width:100%;height:auto;}}'
        f'.container{{max-width:1140px;margin:0 auto;padding:0 1.5rem;}}'
        f'.row{{display:flex;flex-wrap:wrap;margin:0 -0.75rem;}}'
        f'.col-md-4{{flex:0 0 33.333%;max-width:33.333%;padding:0 0.75rem;}}'
        f'.col-md-6{{flex:0 0 50%;max-width:50%;padding:0 0.75rem;}}'
        f'.col-md-8{{flex:0 0 66.666%;max-width:66.666%;padding:0 0.75rem;}}'
        f'@media(max-width:768px){{.col-md-4,.col-md-6,.col-md-8{{flex:0 0 100%;max-width:100%;}}}}'
        f'.d-flex{{display:flex;}}.flex-wrap{{flex-wrap:wrap;}}.gap-3{{gap:1rem;}}.gap-4{{gap:1.5rem;}}'
        f'.justify-content-center{{justify-content:center;}}.align-items-center{{align-items:center;}}'
        f'.text-center{{text-align:center;}}.w-100{{width:100%;}}.mt-5{{margin-top:3rem;}}.mb-4{{margin-bottom:1.5rem;}}'
        f'.navbar{{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;align-items:center;padding:0.8rem 1.5rem;background:{p["bg"]}dd;backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,0.05);}}'
        f'.navbar-brand{{font-weight:700;font-size:1.4rem;display:flex;align-items:center;gap:0.5rem;color:{p["primary"]};}}'
        f'.navbar-toggler{{display:none;background:none;border:1px solid rgba(255,255,255,0.3);color:#fff;padding:6px 14px;border-radius:8px;cursor:pointer;font-size:1.3rem;}}'
        f'.navbar-collapse{{display:flex;}}.navbar-nav{{display:flex;list-style:none;margin-left:auto;gap:0.3rem;}}'
        f'.nav-link{{padding:0.5rem 1rem;color:rgba(255,255,255,0.55);transition:color 0.3s;position:relative;font-size:0.95rem;}}'
        f'.nav-link::after{{content:"";position:absolute;bottom:0;left:50%;width:0;height:2px;background:{p["primary"]};transition:all .3s;transform:translateX(-50%);}}'
        f'.nav-link:hover,.nav-link.active{{color:{p["primary"]};}}.nav-link:hover::after,.nav-link.active::after{{width:80%;}}'
        f'@media(max-width:768px){{.navbar-toggler{{display:block;}}.navbar-collapse{{display:none;flex-direction:column;width:100%;}}.navbar-collapse.show{{display:flex;}}.navbar-nav{{flex-direction:column;width:100%;}}}}'
        f'.hero{{min-height:100vh;display:flex;align-items:center;position:relative;overflow:hidden;padding-top:4rem;}}'
        f'.hero-center{{text-align:center;justify-content:center;}}.hero-left{{text-align:left;}}'
        f'.hero-gradient{{background:radial-gradient(ellipse at center,{p["primary"]}15 0%,{p["bg"]} 70%);}}'
        f'.hero-split{{background:linear-gradient({ga},{p["bg"]} 0%,{p["bg"]} 50%,{p["primary"]}15 100%);}}'
        f'.hero-minimal{{background:{p["bg"]};}}'
        f'.hero h1{{font-size:clamp(2.2rem,7vw,4.5rem);font-weight:800;line-height:1.15;background:linear-gradient({ga},{p["primary"]},{p["secondary"]},{p["accent"]});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:1rem;}}'
        f'.hero .tagline{{text-transform:uppercase;letter-spacing:5px;font-size:0.8rem;opacity:0.5;margin-bottom:1rem;font-weight:600;}}'
        f'.hero p.lead{{font-size:1.2rem;margin-bottom:1.5rem;max-width:600px;opacity:0.85;}}'
        f'.btn{{display:inline-block;padding:14px 36px;font-weight:600;border-radius:{br};transition:all 0.4s cubic-bezier(.175,.885,.32,1.275);cursor:pointer;border:none;font-size:1rem;}}'
        f'.btn-primary{{background:linear-gradient({ga},{p["primary"]},{p["secondary"]});color:#fff;box-shadow:0 4px 20px rgba({R},{G},{B},{si});}}'
        f'.btn-primary:hover{{transform:translateY(-4px) scale(1.02);box-shadow:0 12px 40px rgba({R},{G},{B},{float(si)+0.1});}}'
        f'.btn-outline-light{{background:transparent;border:2px solid rgba(255,255,255,0.4);color:#fff;}}'
        f'.btn-outline-light:hover{{background:rgba(255,255,255,0.1);}}'
        f'.btn-lg{{padding:16px 44px;font-size:1.1rem;}}'
        f'section{{padding:5rem 0;}}section:nth-child(even){{background:rgba(255,255,255,0.015);}}'
        f'section h2{{font-size:clamp(1.6rem,3.5vw,2.8rem);font-weight:700;margin-bottom:1rem;text-align:center;}}'
        f'section .subtitle{{text-align:center;opacity:0.6;margin-bottom:3rem;font-size:1.1rem;}}'
        f'.feature-card{{background:{p["card"]};border:1px solid rgba(255,255,255,0.06);border-radius:{cr};padding:2rem;transition:all 0.5s cubic-bezier(.175,.885,.32,1.275);height:100%;}}'
        f'.feature-card:hover{{transform:translateY(-8px);border-color:{p["primary"]}44;box-shadow:0 20px 50px rgba({R},{G},{B},{si});}}'
        f'.feature-icon{{width:56px;height:56px;display:flex;align-items:center;justify-content:center;border-radius:{cr};font-size:1.6rem;background:linear-gradient({ga},{p["primary"]}22,{p["secondary"]}22);color:{p["primary"]};margin-bottom:1.2rem;}}'
        f'.feature-card h3{{margin-bottom:0.6rem;font-size:1.2rem;}}.feature-card p{{opacity:0.7;font-size:0.95rem;}}'
        f'.card{{background:{p["card"]};border:1px solid rgba(255,255,255,0.06);border-radius:{cr};padding:1.5rem;height:100%;}}'
        f'.card-body{{padding:0;}}.card-text{{margin:0.8rem 0;font-style:italic;opacity:0.85;}}'
        f'.fw-bold{{font-weight:700;}}.mb-0{{margin-bottom:0;}}.mb-3{{margin-bottom:1rem;}}.mb-4{{margin-bottom:1.5rem;}}'
        f'.form-control{{width:100%;padding:0.9rem 1.2rem;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:{p["text"]};border-radius:{cr};font-size:1rem;outline:none;}}'
        f'.form-control:focus{{border-color:{p["primary"]};box-shadow:0 0 0 3px {p["primary"]}33;}}'
        f'footer{{padding:2rem 0;text-align:center;border-top:1px solid rgba(255,255,255,0.05);color:rgba(255,255,255,0.35);font-size:0.9rem;}}'
        f'[data-aos]{{opacity:0;transform:translateY(25px);transition:opacity 0.7s ease,transform 0.7s ease;}}[data-aos].aos-animate{{opacity:1;transform:translateY(0);}}'
        f'[data-aos=fade-left]{{transform:translateX(-25px);}}[data-aos=fade-left].aos-animate{{transform:translateX(0);}}'
        f'[data-aos=zoom-in]{{transform:scale(0.92);}}[data-aos=zoom-in].aos-animate{{transform:scale(1);}}'
        f'.pill{{display:inline-block;padding:4px 16px;border-radius:50px;font-size:0.8rem;font-weight:600;background:{p["primary"]}22;color:{p["primary"]};margin-bottom:1rem;}}'
        f'::-webkit-scrollbar{{width:6px;}}::-webkit-scrollbar-track{{background:{p["bg"]};}}::-webkit-scrollbar-thumb{{background:{p["primary"]};border-radius:10px;}}'
        f'.emoji-big{{font-size:3rem;margin-bottom:1rem;display:block;}}'
        f'.highlight-box{{background:{p["primary"]}11;border-left:4px solid {p["primary"]};padding:1.5rem 2rem;border-radius:0 {cr} {cr} 0;margin:2rem 0;}}'
        f'.highlight-box p{{margin:0;opacity:0.85;}}'
        f'.section-icon{{font-size:2rem;display:block;text-align:center;margin-bottom:0.5rem;}}'
        f'.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:2rem;}}@media(max-width:768px){{.grid-2{{grid-template-columns:1fr;}}}}'
    )

def _generate_3d(palette):
    e = random.choice(THREE_EFFECTS)
    e = e.replace("PRI_COLOR", palette['primary'])
    e = e.replace("SEC_COLOR", palette['secondary'])
    e = e.replace("ACC_COLOR", palette['accent'])
    return e

def _pick_palette(memory):
    c = PALETTES[:]; random.shuffle(c)
    return _select(c, "used_palettes", memory)

def _pick_font(memory):
    return _select(FONTS, "used_fonts", memory)

def _pick_hero(memory):
    return _select(HERO_LAYOUTS, "used_hero_layouts", memory)

# ── Generate page ──────────────────────────────────────────────────────────
def _generate_landing(title, desc, memory):
    palette = _pick_palette(memory)
    font_pair = _pick_font(memory)
    font_name, font_url = font_pair
    hero_layout = _pick_hero(memory)
    effect_3d = _generate_3d(palette)
    p = palette
    fname = font_name.replace("+", " ")
    hc = f"hero-{hero_layout}"
    a1 = random.choice(["fade-up", "fade-left", "zoom-in"])
    a2 = random.choice(["fade-up", "fade-left", "zoom-in"])

    cat, feats, tests, tags = _match_content(title, desc)
    feats3 = random.sample(feats, min(3, len(feats)))
    tests3 = random.sample(tests, min(3, len(tests)))
    tagline = random.choice(tags)
    delays = [0, 100, 200]

    STAR = "\u2605"
    feat_sec = "".join(
        f'<div class="col-md-4" data-aos="{a1}" data-aos-delay="{delays[i]}"><div class="feature-card"><div class="feature-icon">{chr(9670)}</div><h3>{f[0]}</h3><p>{f[1]}</p></div></div>'
        for i, f in enumerate(feats3)
    )
    test_sec = "".join(
        f'<div class="col-md-4" data-aos="{a1}" data-aos-delay="{delays[i]}"><div class="card"><div class="card-body"><div style="color:#fbbf24;">{STAR*5}</div><p class="card-text">{chr(8220)}{t[0]}{chr(8221)}</p><p class="fw-bold mb-0">{chr(8212)} {t[1]}</p></div></div></div>'
        for i, t in enumerate(tests3)
    )

    ej = effect_3d.replace("</script>", "<\\/script>")
    pri = p["primary"]

    aos_js = (
        "(function(){"
        "var els=document.querySelectorAll('[data-aos]');"
        "function ck(){"
        "els.forEach(function(el){"
        "var r=el.getBoundingClientRect();"
        "if(r.top<window.innerHeight-80)el.classList.add('aos-animate');"
        "});"
        "}"
        "ck();"
        "window.addEventListener('scroll',ck);"
        "window.addEventListener('resize',ck);"
        "})();"
        "document.querySelectorAll('a[href^=\"#\"]').forEach(function(a){"
        "a.addEventListener('click',function(e){"
        "e.preventDefault();"
        "var t=document.querySelector(this.getAttribute('href'));"
        "if(t)t.scrollIntoView({behavior:'smooth'});"
        "});"
        "});"
        "var f=document.getElementById('contactForm');"
        "if(f){"
        "f.addEventListener('submit',function(e){"
        "e.preventDefault();"
        "if(this.checkValidity()){"
        "var t=document.createElement('div');"
        "t.textContent='Mensaje enviado correctamente.';"
        "t.style.cssText='position:fixed;bottom:2rem;right:2rem;background:" + pri + ";color:#fff;padding:1rem 2rem;border-radius:12px;z-index:9999;transform:translateY(100px);opacity:0;transition:all 0.4s';"
        "document.body.appendChild(t);"
        "requestAnimationFrame(function(){t.style.transform='translateY(0)';t.style.opacity='1';});"
        "setTimeout(function(){t.style.transform='translateY(100px)';t.style.opacity='0';setTimeout(function(){t.remove();},400);},3000);"
        "this.reset();"
        "}"
        "this.classList.add('was-validated');"
        "});"
        "}"
        + ej
    )

    html = (
        '<!DOCTYPE html>\n<html lang="es">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        '<title>' + title + '</title>\n'
        '<link href="https://fonts.googleapis.com/css2?family=' + font_url + '&display=swap" rel="stylesheet">\n'
        '<style>\n' + _inline_css(p, fname, hero_layout) + '\n</style>\n'
        '</head>\n<body>\n'
        '<nav class="navbar">\n'
        '  <a class="navbar-brand" href="#">' + chr(9733) + ' ' + title + '</a>\n'
        '  <button class="navbar-toggler" onclick="document.getElementById(\'nav\').classList.toggle(\'show\')">' + chr(9776) + '</button>\n'
        '  <div class="navbar-collapse" id="nav">\n'
        '    <ul class="navbar-nav">\n'
        '      <li><a class="nav-link active" href="#inicio">Inicio</a></li>\n'
        '      <li><a class="nav-link" href="#info">Informacion</a></li>\n'
        '      <li><a class="nav-link" href="#detalles">Detalles</a></li>\n'
        '      <li><a class="nav-link" href="#reflexion">Reflexion</a></li>\n'
        '      <li><a class="nav-link" href="#contacto">Contacto</a></li>\n'
        '    </ul>\n'
        '  </div>\n'
        '</nav>\n\n'
        '<section id="inicio" class="hero ' + hc + '">\n'
        '  <div class="container' + (' text-center' if hero_layout == 'center' else '') + '">\n'
        '    <div data-aos="' + a1 + '">\n'
        '      <div class="tagline">' + tagline + '</div>\n'
        '      <h1>' + title + '</h1>\n'
        '      <p class="lead" style="' + ('margin:0 auto;' if hero_layout == 'center' else '') + '">' + desc + '</p>\n'
        '      <div class="d-flex gap-3' + (' justify-content-center' if hero_layout == 'center' else '') + '">\n'
        '        <a href="#info" class="btn btn-primary btn-lg">Explorar <span style="margin-left:8px;">' + chr(8594) + '</span></a>\n'
        '        <a href="#contacto" class="btn btn-outline-light btn-lg">Contacto</a>\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<section id="caracteristicas">\n'
        '  <div class="container">\n'
        '    <div class="section-icon">' + chr(9889) + '</div>\n'
        '    <h2 data-aos="' + a2 + '">Caracteristicas</h2>\n'
        '    <p class="subtitle" data-aos="' + a2 + '">Lo que nos hace unicos</p>\n'
        '    <div class="row">' + feat_sec + '</div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<section id="testimonios">\n'
        '  <div class="container">\n'
        '    <div class="section-icon">' + chr(128172) + '</div>\n'
        '    <h2 data-aos="' + a2 + '">Testimonios</h2>\n'
        '    <p class="subtitle" data-aos="' + a2 + '">Lo que dicen nuestros clientes</p>\n'
        '    <div class="row">' + test_sec + '</div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<section id="contacto">\n'
        '  <div class="container">\n'
        '    <div class="section-icon">' + chr(9993) + '</div>\n'
        '    <h2 data-aos="' + a2 + '">Contacto</h2>\n'
        '    <p class="subtitle" data-aos="' + a2 + '">Escribenos y te responderemos pronto</p>\n'
        '    <div class="row justify-content-center">\n'
        '      <div class="col-md-8">\n'
        '        <form id="contactForm" data-aos="' + a1 + '">\n'
        '          <div class="mb-4"><input class="form-control" placeholder="Nombre" required></div>\n'
        '          <div class="mb-4"><input class="form-control" type="email" placeholder="Email" required></div>\n'
        '          <div class="mb-4"><textarea class="form-control" rows="4" placeholder="Mensaje" required></textarea></div>\n'
        '          <button type="submit" class="btn btn-primary w-100 btn-lg">Enviar Mensaje</button>\n'
        '        </form>\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<footer>\n'
        '  <p>' + chr(169) + ' 2026 ' + title + ' - Creado por ERIS AI</p>\n'
        '</footer>\n\n'
        '<script>\n' + aos_js + '\n</script>\n'
        '</body>\n</html>'
    )

    memory["pages_created"] = memory.get("pages_created", 0) + 1
    memory.setdefault("history", []).append({
        "id": uuid.uuid4().hex[:8],
        "title": title, "palette": palette["name"], "font": font_name,
        "hero": hero_layout, "category": cat,
        "features": [f[0] for f in feats3],
        "timestamp": time.time(),
    })
    if len(memory["history"]) > 20:
        memory["history"] = memory["history"][-20:]
    _save_memory(memory)
    return html

# ── Public API ─────────────────────────────────────────────────────────────
def web_generator(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "").lower()
    template_name = (parameters.get("template") or "landing").lower().strip()
    title = parameters.get("title") or parameters.get("titulo") or "Mi Pagina Web"
    folder = parameters.get("folder") or parameters.get("carpeta") or ""
    description = parameters.get("description") or parameters.get("descripcion") or f"Bienvenido a {title}"

    memory = _load_memory()

    if player:
        player.write_log(f"Web Generator: {action} (page #{memory.get('pages_created', 0) + 1})")

    if action in ("list", "lista", "templates"):
        m = memory
        return (
            f"Paginas creadas: {m.get('pages_created', 0)}\n"
            f"Paletas usadas: {len(m.get('used_palettes', []))}/{len(PALETTES)}\n"
            f"Fuentes usadas: {len(set(m.get('used_fonts', [])))}/{len(FONTS)}\n"
            f"Efectos 3D: {len(THREE_EFFECTS)} disponibles\n\n"
            "Usa: web_generator action=create title='...' folder=..."
        )

    elif action in ("create", "crear", "generate", "generar"):
        if not folder:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:30]
            folder = str(Path.home() / "Desktop" / f"{safe_title}_{ts}")

        folder = os.path.abspath(folder)
        os.makedirs(folder, exist_ok=True)

        html = _generate_landing(title, description, memory)
        fp = os.path.join(folder, "index.html")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(html)

        pcount = memory.get("pages_created", 0)
        pal = memory["history"][-1]["palette"] if memory.get("history") else "?"
        fn = memory["history"][-1]["font"].replace("+", " ") if memory.get("history") else "?"

        result = (
            f"Pagina #{pcount} creada en:\n  {folder}\n\n"
            f"Diseno: {palette_desc(pal)}\n"
            f"Fuente: {fn}\n"
            f"Tamano: {len(html)} bytes (todo incluido)"
        )

        if os.path.exists(fp):
            try:
                import webbrowser
                webbrowser.open(f"file://{fp}")
                result += "\n\nAbierta en el navegador."
            except Exception:
                result += "\n\nAbre manualmente: " + fp

        if player:
            player.write_log(f"  Pagina #{pcount}: {folder} ({len(html)}b)")
        return result

    elif action in ("memory", "memoria"):
        m = memory
        h = m.get("history", [])
        lines = [
            f"Memoria de diseno:",
            f"  Paginas creadas: {m.get('pages_created', 0)}",
            f"  Paletas usadas: {len(set(m.get('used_palettes', [])))}/{len(PALETTES)}",
            f"  Fuentes usadas: {len(set(m.get('used_fonts', [])))}/{len(FONTS)}",
            f"  Efectos 3D disponibles: {len(THREE_EFFECTS)}",
        ]
        if h:
            lines.append(f"\nUltimas paginas:")
            for p in h[-5:]:
                cat = p.get("category", "?")
                lines.append(f"  [{p['id']}] {p['title']} ({cat}) - {p['palette']} / {p['font'].replace('+',' ')}")
        return "\n".join(lines)

    elif action in ("reset", "reiniciar_memoria"):
        _save_memory({"used_palettes": [], "used_fonts": [], "used_effects": [], "used_hero_layouts": [], "pages_created": 0, "history": []})
        return "Memoria de diseno reiniciada."

    else:
        return (
            "Acciones:\n"
            "  create (title=, folder=) — Crear pagina unica\n"
            "  list — Estadisticas de diseno\n"
            "  memory — Ver historial\n"
            "  reset — Reiniciar memoria"
        )

def palette_desc(palette_name):
    descs = {
        "purple-cosmic": "Purple Cosmic — tonos violetas cosmicos",
        "cyan-deep": "Cyan Deep — azules oceanicos profundos",
        "amber-warm": "Amber Warm — naranjas y dorados cálidos",
        "emerald-forest": "Emerald Forest — verdes esmeralda",
        "pink-rose": "Pink Rose — rosas y magentas vibrantes",
        "blue-ocean": "Blue Ocean — azules marinos",
        "violet-neon": "Violet Neon — violetas neón eléctricos",
        "sunset": "Sunset — atardecer en tonos naranja y rojo",
        "teal-aurora": "Teal Aurora — verdes azulados aurora",
        "indigo-twilight": "Indigo Twilight — indigos crepusculares",
        "ruby": "Ruby — rojos rubí intensos",
        "sky": "Sky — azules cielo",
        "lime": "Lime — verdes lima vibrantes",
        "magenta": "Magenta — magenta puro",
        "crimson": "Crimson — rojos carmesí",
    }
    return descs.get(palette_name, palette_name)
