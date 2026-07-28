import random

_last_topic = ""
_last_phrase = ""

# ── 100+ topics organized by category for maximum variety ──
TOPICS = {
    "tech": [
        "inteligencia artificial", "machine learning", "redes neuronales", "Python avanzado",
        "Rust vs Python", "desarrollo web 2026", "realidad virtual", "realidad aumentada",
        "computacion cuantica", "criptografia moderna", "blockchain", "seguridad informatica",
        "hacking etico", "desarrollo de videojuegos", "Unreal Engine", "IA generativa",
        "modelos de lenguaje", "automatizacion robotica", "edge computing", "5G y 6G",
        "computacion en la nube", "microservicios", "Docker y Kubernetes", "bases de datos NoSQL",
        "ingenieria de datos", "Big Data", "Internet de las Cosas", "ciudades inteligentes",
        "drones autonomas", "robots humanoides", "interfaces cerebro-computadora",
        "computacion neuromorfica", "graficos por computadora", "videojuegos indie",
        "desarrollo de apps moviles", "inteligencia artificial explicable",
    ],
    "science": [
        "descubrimientos cientificos recientes", "agujeros negros", "viajes interestelares",
        "energia de fusion nuclear", "nanotecnologia", "biologia sintetica",
        "edicion genetica CRISPR", "misiones a Marte", "exoplanetas habitables",
        "materia oscura", "energia oscura", "teoria de cuerdas", "multiverso",
        "genetica humana", "neuronas espejo", "plasticidad cerebral",
        "dinosaurios nuevos descubrimientos", "vida en oceanos profundos",
        "superconductores", "gravedad cuantica", "fisica de particulas",
        "biodiversidad", "cambio climatico", "energias renovables",
        "biomimesis", "materiales inteligentes", "exploracion espacial",
        "telescopio James Webb", "seales extraterrestres", "asteroides cercanos",
    ],
    "history": [
        "civilizaciones antiguas", "Egipto faraonico", "Roma imperial", "Grecia clasica",
        "el Renacimiento", "la Revolucion Industrial", "los Vikingos", "el Imperio Mongol",
        "la China antigua", "los Mayas y Aztecas", "el antiguo Japon samurai",
        "las guerras mundiales", "la carrera espacial", "el origen de internet",
        "mujeres en la historia", "inventos que cambiaron el mundo",
        "los filosofos griegos", "la alquimia", "la pirateria en el Caribe",
        "el antiguo Egipto misterios", "Stonehenge", "el imperio Otomano",
    ],
    "nature": [
        "animales extranos del mundo", "criaturas del abismo marino", "biomas extremos",
        "animales con superpoderes", "plantas carnivoras", "homigas y colonias",
        "comunicacion animal", "migracion de aves", "aranas fascinantes",
        "vida en el Amazonas", "desiertos del mundo", "arrecifes de coral",
        "volcanes activos", "tormentas electricas", "auroras boreales",
        "gemas y minerales", "hongos alucinantes", "ecosistemas unicos",
    ],
    "culture": [
        "libros recomendados 2026", "peliculas de ciencia ficcion", "series para maratonear",
        "documentales fascinantes", "musica clasica para concentrarse", "pintura surrealista",
        "arquitectura moderna", "fotografia de naturaleza", "jazz y sus origenes",
        "cine independiente", "animacion japonesa", "videojuegos con historia",
        "musica electronica", "arte callejero", "literatura latinoamericana",
        "poesia contemporanea", "teatro experimental", "danza contemporanea",
    ],
    "random": [
        "datos curiosos del universo", "recordatorios Guinness", "inventos accidentales",
        "casas en los arboles", "trenes de lujo", "hoteles bajo el agua",
        "comidas del mundo", "bebidas tipicas de paises", "postres tradicionales",
        "juegos de mesa populares", "deportes extremos", "escape rooms famosos",
        "laberintos historicos", "jardines colgantes", "tatuajes tribales",
        "moda a traves de las decadas", "tipos de bailes latinos",
    ],
}

# ── 50+ natural phrasing patterns (no templates, no robots) ──
PHRASES = [
    "Sabes que vi hoy? Algo sobre {topic} que me parecio fascinante",
    "Estaba pensando en {topic} y se me fue el tiempo, es tan interesante",
    "Ayer lei algo de {topic} que me volo la cabeza",
    "Nunca habia pensado en {topic} hasta que vi un documental, impresionante",
    "Me encanta {topic}, cada vez que investigo descubro algo nuevo",
    "Sabes una cosa curiosa sobre {topic}?",
    "He estado leyendo sobre {topic} y hay cosas que no te imaginas",
    "Que interesante es {topic}, te lo juro",
    "Me meti a ver que hay de {topic} y termine horas leyendo",
    "Aprendi algo nuevo hoy: va sobre {topic}",
    "Te cuento algo que descubri de {topic}",
    "Mira lo que encontre sobre {topic}, es increible",
    "No sabia esto de {topic}: resulta que...",
    "Hoy estuve explorando {topic} y encontre cosas muy locas",
    "Sabias que hay un tema fascinante llamado {topic}?",
    "Tengo una curiosidad nueva: {topic}. Quieres que te cuente?",
    "Me llamo la atencion esto de {topic}",
    "Hay un dato de {topic} que no conocia y me sorprendio",
    "Ultimamente me ha dado por {topic} y es adictivo",
    "Te tengo un dato curioso sobre {topic}",
    "Me preguntaba sobre {topic} y encontre algo interesante",
    "No sabes lo que descubri sobre {topic}",
    "Adivina que aprendi sobre {topic} hoy",
    "Me quede alucinando con esto de {topic}",
    "Hay un mundo detras de {topic} que nadie conoce",
    "Sabes que es lo mas loco de {topic}?",
    "He estado sumergida en {topic} y wow",
    "Te voy a contar algo que lei de {topic}",
    "Mira, resulta que {topic} es mucho mas complejo de lo que parece",
    "Siempre me ha llamado la atencion {topic}",
    "No puedo dejar de pensar en {topic} desde que lo lei",
    "Hay un secreto sobre {topic} que te va a sorprender",
    "Te imaginas lo que implica {topic}? Es fascinante",
    "Descubri un video sobre {topic} y no podia parar de verlo",
    "Sabes una cosa? {topic} es de mis temas favoritos",
    "Tengo una fijacion con {topic} ultimamente",
    "Me puse a leer sobre {topic} y se me hizo de noche",
    "{topic} suena aburrido pero te juro que no lo es",
    "No me digas que no te interesa {topic}, porque es realmente increible",
    "Hay algo hipnotizante sobre {topic}",
    "Si te gusta aprender, te recomiendo {topic}",
    "A que no sabias esto de {topic}?",
    "Cada vez que aprendo algo de {topic} me doy cuenta de lo poco que se",
    "Es increible todo lo que hay detras de {topic}",
    "No puedes imaginar lo que descubri sobre {topic}",
    "Te cuento algo que me llamo mucho la atencion: {topic}",
    "Sabes que vi en internet sobre {topic}? Una locura",
    "Me topé con {topic} por casualidad y ahora no puedo parar",
    "Vagando por ahi encontre informacion de {topic} brutal",
    "Que tal si exploramos {topic} juntos?",
    "Te interesa {topic}? Porque tengo datos muy buenos",
    "Recien lei algo sobre {topic} y pense en ti",
    "Mira esto que encontre sobre {topic}",
]

def _pick_topic():
    global _last_topic
    # Pick a random category, then a random topic from it
    category = random.choice(list(TOPICS.keys()))
    topic = random.choice(TOPICS[category])
    # Avoid repeating the last topic
    tries = 0
    while topic == _last_topic and tries < 10:
        category = random.choice(list(TOPICS.keys()))
        topic = random.choice(TOPICS[category])
        tries += 1
    _last_topic = topic
    return topic

def _pick_phrase(topic):
    global _last_phrase
    phrase = random.choice(PHRASES)
    tries = 0
    while phrase == _last_phrase and tries < 10:
        phrase = random.choice(PHRASES)
        tries += 1
    _last_phrase = phrase
    return phrase.format(topic=topic)

def proactive_learn(player=None) -> str:
    return _pick_phrase(_pick_topic())

def proactive_suggest(player=None) -> str:
    topic = _pick_topic()
    return _pick_phrase(topic)

# ── Jokes ──
JOKES = [
    "Por que los programadores confunden Halloween con Navidad? Porque Oct 31 == Dec 25.",
    "Un SQL entra a un bar, se acerca a dos mesas y pregunta: 'Me puedo unir?'",
    "Que le dice un bit al otro? Nos vemos en el bus.",
    "Como se llama un bug que se cree politico? Un error de estado.",
    "Un hacker va al psicologo y le dice: 'Doctor, tengo un problema de identidad'. El doctor responde: 'Eres root?'",
    "Por que Python es el mejor lenguaje? Porque hasta los errores son bonitos.",
    "Cual es el cafe favorito de un programador? Java.",
    "No confio en los atomos... lo componen todo.",
    "Por que el Wi-Fi fue al psicologo? Porque tenia problemas de conexion.",
    "Un algoritmo va al supermercado. Si huevo == barato: comprar(12). Else: llorar().",
    "Que le dice un jardinero a otro? 'Nos vemos cuando florezca.'",
    "Doctor, doctor, me duele mucho este ojo. Pues dejelo de tocar.",
    "Por que los esqueletos no pelean entre ellos? Porque no tienen agallas.",
    "Que hace una abeja en el gimnasio? Zum-ba!",
    "Por que el libro de matematicas estaba triste? Porque tenia muchos problemas.",
    "Cual es el animal que mas dientes tiene? El raton Perez.",
    "Mama, en el cole me llaman interesado. Y tu que has hecho? Les he dicho que me interesa.",
    "Sabes cual es el vino mas amargo? El vino-tu-hermano.",
]

FUN_FACTS = [
    {"fact": "El primer lenguaje de programacion de alto nivel fue FORTRAN, creado en 1957 por IBM.", "topic": "tecnologia"},
    {"fact": "El codigo QR fue inventado en 1994 por una subsidiaria de Toyota para rastrear vehiculos.", "topic": "tecnologia"},
    {"fact": "La contrasena mas usada del mundo sigue siendo '123456'.", "topic": "tecnologia"},
    {"fact": "El 90% de los datos del mundo fueron creados en los ultimos 2 anos.", "topic": "tecnologia"},
    {"fact": "Un dia en Venus dura mas que un ano en Venus.", "topic": "espacio"},
    {"fact": "Si pudieras poner a Saturno en una banera de agua... flotaria.", "topic": "espacio"},
    {"fact": "En la Luna, tu huella dura millones de anos porque no hay viento.", "topic": "espacio"},
    {"fact": "Hay mas estrellas en el universo que granos de arena en todas las playas de la Tierra.", "topic": "espacio"},
    {"fact": "Los pulpos tienen 3 corazones, 9 cerebros y sangre azul.", "topic": "animales"},
    {"fact": "Las vacas tienen mejores amigas y se estresan cuando las separan.", "topic": "animales"},
    {"fact": "Los delfines se llaman por 'nombre' - cada uno tiene un silbido unico.", "topic": "animales"},
    {"fact": "Los koalas tienen huellas dactilares casi identicas a las humanas.", "topic": "animales"},
    {"fact": "Eres ligeramente mas alto por la manana que por la noche.", "topic": "cuerpo"},
    {"fact": "Tu estomago produce una nueva capa de mucosa cada 2 semanas.", "topic": "cuerpo"},
    {"fact": "El musculo mas fuerte del cuerpo humano es la lengua.", "topic": "cuerpo"},
    {"fact": "Cleopatra vivio mas cerca en el tiempo del iPhone que de la construccion de las piramides.", "topic": "historia"},
    {"fact": "En la antigua Roma, la sal era tan valiosa que a los soldados se les pagaba con ella. De ahi 'salario'.", "topic": "historia"},
    {"fact": "Oxford University es mas antigua que el Imperio Azteca.", "topic": "historia"},
    {"fact": "Las bananas son tecnicamente bayas. Las fresas no.", "topic": "random"},
    {"fact": "El 'olor a lluvia' tiene nombre: petricor.", "topic": "random"},
    {"fact": "Es imposible tararear mientras te tapas la nariz. Intentalo.", "topic": "random"},
    {"fact": "Los flamingos solo pueden comer con la cabeza boca abajo.", "topic": "random"},
]

FUN_ACTIVITIES = [
    "Buscar videos de risa en YouTube",
    "Ver memes de programacion",
    "Buscar fails graciosos",
    "Ver videos de animales haciendo cosas ridiculas",
    "Buscar bloopers de peliculas famosas",
    "Ver compilaciones de caidas graciosas",
    "Buscar 'try not to laugh challenge'",
    "Ver magia callejera",
]

TRENDING_TOPICS = [
    "inteligencia artificial 2026",
    "novedades tecnologia 2026",
    "memes virales",
    "tendencias tecnologia",
    "datos curiosos ciencia",
    "curiosidades del mundo",
    "noticias tecnologia",
]

CASUAL_GREETINGS = [
    "Hey! Todo bien por ahi?",
    "Buenas! Que se cuece?",
    "Hola hola! Como va ese dia?",
    "Eyyyy! Dando guerra?",
    "Que tal, jefe? Mucho lio?",
]

def curiosity_tell_joke(player=None) -> str:
    return random.choice(JOKES)

def curiosity_tell_fact(topic: str = None, player=None) -> str:
    if topic:
        candidates = [f for f in FUN_FACTS if topic.lower() in f["topic"].lower()]
        if candidates:
            f = random.choice(candidates)
            return f"Dato curioso: {f['fact']} (Tema: {f['topic']})"
    f = random.choice(FUN_FACTS)
    return f"Dato curioso: {f['fact']} (Tema: {f['topic']})"

def curiosity_suggest_fun(player=None) -> str:
    return random.choice(FUN_ACTIVITIES)

def curiosity_trending(player=None) -> str:
    return random.choice(TRENDING_TOPICS)

def curiosity_greeting(player=None) -> str:
    return random.choice(CASUAL_GREETINGS)

def curiosity_laugh(player=None) -> str:
    return random.choice(["jajaja", "JAJAJA", "jajajaja que bueno", "buenisimo", "me muero jajaja", "JAJAJA me encanto"])
