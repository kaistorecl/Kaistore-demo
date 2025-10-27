# ai_products.py
#
# Catálogo de ideas simulando lo que haría la "IA".
# Cada idea es un producto potencial todavía no generado.
# El endpoint /api/admin/auto_generate elige una de estas,
# la mete en la base como draft, y opcionalmente la publica.

import random

IDEAS = [
    {
        "title_marketing": "Almohada cervical ergonómica premium",
        "short_bullets": [
            "Reduce tensión cervical en 15 minutos",
            "Espuma de memoria alta densidad",
            "Funda hipoalergénica lavable",
            "Ideal para escritorio y viajes",
        ],
        "price": 5990,
        "currency": "CLP",
        "image_urls": [
            "https://picsum.photos/seed/almohada-main/800/800",
            "https://picsum.photos/seed/almohada-side/800/800",
        ],
        "score": 0.91,
        "source_label": "ai_seed_v1",
    },
    {
        "title_marketing": "Soporte lumbar para silla",
        "short_bullets": [
            "Mejora postura en teletrabajo",
            "Malla transpirable 3D",
            "Correas universales",
            "Alivia zona baja de la espalda",
        ],
        "price": 7990,
        "currency": "CLP",
        "image_urls": [
            "https://picsum.photos/seed/lumbar-main/800/800",
            "https://picsum.photos/seed/lumbar-side/800/800",
        ],
        "score": 0.88,
        "source_label": "ai_seed_v1",
    },
    {
        "title_marketing": "Mouse vertical ergonómico",
        "short_bullets": [
            "Agarre natural para muñeca",
            "Botones silenciosos",
            "Conexión inalámbrica",
            "Batería de larga duración",
        ],
        "price": 12990,
        "currency": "CLP",
        "image_urls": [
            "https://picsum.photos/seed/mouse-main/800/800",
            "https://picsum.photos/seed/mouse-side/800/800",
        ],
        "score": 0.86,
        "source_label": "ai_seed_v1",
    },
    {
        "title_marketing": "Lámpara LED portátil recargable",
        "short_bullets": [
            "Luz cálida o fría regulable",
            "Hasta 12h de batería",
            "Carga USB-C rápida",
            "Perfecta para escritorio o velador",
        ],
        "price": 9990,
        "currency": "CLP",
        "image_urls": [
            "https://picsum.photos/seed/lampara-main/800/800",
            "https://picsum.photos/seed/lampara-side/800/800",
        ],
        "score": 0.89,
        "source_label": "ai_seed_v1",
    },
]

def pick_idea() -> dict:
    """
    Devuelve una de las ideas anteriores,
    agregando una leve variación en 'score'
    para que no sea siempre idéntico.
    """
    idea = random.choice(IDEAS)
    return {
        **idea,
        "score": round(idea["score"] + random.uniform(-0.03, 0.03), 2)
    }
