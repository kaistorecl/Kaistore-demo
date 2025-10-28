# ai_products.py
#
# Generador FALSO de ideas de producto.
# (No llama a ninguna IA real. Es pura lista estática + random.)
#
# IMPORTANTE:
# - Mantener las claves: title_marketing, short_bullets, image_urls,
#   price, currency. El resto del backend asume ese formato.

import random
from config import settings

SAMPLE_IDEAS = [
    {
        "title_marketing": "Mini ventilador USB silencioso",
        "short_bullets": [
            "Enfría sin ruido en videollamadas o mientras duermes",
            "Tres niveles de velocidad",
            "Base ajustable 180°",
            "Carga por USB-C",
        ],
        "price": 4990,
        "currency": settings.CURRENCY,
        "image_urls": [
            "https://via.placeholder.com/800x800?text=ventilador-main",
            "https://via.placeholder.com/800x800?text=ventilador-side",
        ],
    },
    {
        "title_marketing": "Organizador plegable para closet",
        "short_bullets": [
            "Ordena ropa y accesorios en segundos",
            "Plegable y fácil de guardar",
            "Tela reforzada de alta resistencia",
            "Ideal para viajes o mudanzas",
        ],
        "price": 5990,
        "currency": settings.CURRENCY,
        "image_urls": [
            "https://via.placeholder.com/800x800?text=closet-main",
            "https://via.placeholder.com/800x800?text=closet-side",
        ],
    },
    {
        "title_marketing": "Lámpara LED portátil recargable",
        "short_bullets": [
            "Luz cálida para escritorio, velador o camping",
            "Batería interna recargable",
            "Brillo regulable con un toque",
            "Liviana y fácil de llevar",
        ],
        "price": 9990,
        "currency": settings.CURRENCY,
        "image_urls": [
            "https://via.placeholder.com/800x800?text=lamp-main",
            "https://via.placeholder.com/800x800?text=lamp-side",
        ],
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
        "currency": settings.CURRENCY,
        "image_urls": [
            "https://via.placeholder.com/800x800?text=lumbar-main",
            "https://via.placeholder.com/800x800?text=lumbar-side",
        ],
    },
]


def generate_fake_product_idea():
    """
    Devuelve un dict con la forma que 'auto_generate' espera.
    """
    idea = random.choice(SAMPLE_IDEAS)

    # Podríamos randomizar precio un poquito para que no todos salgan iguales
    base_price = idea["price"]
    wiggle = random.randint(-500, 500)
    final_price = max(1000, base_price + wiggle)

    return {
        "title_marketing": idea["title_marketing"],
        "short_bullets": idea["short_bullets"],
        "price": final_price,
        "currency": idea["currency"],
        "image_urls": idea["image_urls"],
    }
