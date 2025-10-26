# ai_products.py
import random

# Pequeño catálogo de ideas simulando lo que haría la IA
IDEAS = [
    {
        "title_marketing": "Almohada cervical ergonómica premium",
        "short_bullets": [
            "Reduce tensión en cuello en 15 minutos",
            "Espuma de memoria alta densidad",
            "Funda hipoalergénica lavable",
            "Ideal para escritorio y viajes",
        ],
        "price": 5990,
        "currency": "CLP",
        "image_urls": [
            "https://via.placeholder.com/800x600?text=almohada-main",
            "https://via.placeholder.com/800x600?text=almohada-side",
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
        "currency": "CLP",
        "image_urls": [
            "https://via.placeholder.com/800x600?text=lumbar-main",
            "https://via.placeholder.com/800x600?text=lumbar-side",
        ],
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
            "https://via.placeholder.com/800x600?text=mouse-main",
            "https://via.placeholder.com/800x600?text=mouse-side",
        ],
    },
]

def pick_idea() -> dict:
    idea = random.choice(IDEAS)
    # agrega un score “IA”
    idea = {**idea, "score": round(random.uniform(0.7, 0.95), 2)}
    return idea
