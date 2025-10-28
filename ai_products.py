import random


def pick_idea():
    """
    Devuelve una idea simulada de producto en formato dict.
    Estas ideas las usa /api/admin/auto_generate para crear un draft.
    """

    ideas = [
        {
            "title_marketing": "Lámpara LED portátil recargable",
            "short_bullets": [
                "Luz potente para emergencia o camping",
                "Batería USB recargable",
                "Liviana y fácil de llevar",
            ],
            "price": 9990,
            "currency": "CLP",
            # usamos picsum (sirve como placeholder real, sí carga imagen)
            "image_urls": [
                "https://picsum.photos/seed/lampara-led/800/800"
            ],
            "score": 0.91,
        },
        {
            "title_marketing": "Soporte lumbar para silla",
            "short_bullets": [
                "Mejora tu postura al trabajar",
                "Malla transpirable 3D",
                "Alivia zona baja de la espalda",
            ],
            "price": 7990,
            "currency": "CLP",
            "image_urls": [
                "https://picsum.photos/seed/lumbar/800/800"
            ],
            "score": 0.88,
        },
        {
            "title_marketing": "Almohada cervical ergonómica premium",
            "short_bullets": [
                "Reduce tensión en cuello en 15 minutos",
                "Espuma memory foam de alta densidad",
                "Ideal para escritorio y viajes",
            ],
            "price": 5990,
            "currency": "CLP",
            "image_urls": [
                "https://picsum.photos/seed/cervical/800/800"
            ],
            "score": 0.86,
        },
        {
            "title_marketing": "Mini ventilador USB silencioso",
            "short_bullets": [
                "Frescura directa en tu escritorio",
                "Silencioso, ideal para videollamadas",
                "Gira 360° y cabe en la mochila",
            ],
            "price": 4990,
            "currency": "CLP",
            "image_urls": [
                "https://picsum.photos/seed/ventilador-usb/800/800"
            ],
            "score": 0.83,
        },
        {
            "title_marketing": "Organizador plegable para closet",
            "short_bullets": [
                "Ahorra espacio y mantiene todo visible",
                "Plegable, fácil de guardar",
                "Perfecto para ropa interior y accesorios",
            ],
            "price": 5490,
            "currency": "CLP",
            "image_urls": [
                "https://picsum.photos/seed/organizador/800/800"
            ],
            "score": 0.8,
        },
    ]

    # elegimos una idea random
    idea = random.choice(ideas)
    return idea
