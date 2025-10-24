# Kaistore (Single App: Frontend + Backend) — Sandbox Stripe
Demo lista para Render (plan gratis).

## Despliegue rápido
1) Sube este repo a GitHub (público).
2) En Render → New → Blueprint (o Web Service con Dockerfile) → selecciona tu repo.
3) En Variables de Entorno añade tus claves de prueba Stripe:
   - STRIPE_SECRET_KEY=sk_test_...
   - STRIPE_WEBHOOK_SECRET=whsec_... (cuando tengas la URL del backend, crea el webhook en Stripe)
4) La app expone `/api/*` y sirve el frontend estático en `/`.

## Probar pagos (sandbox)
- Usa tarjeta `4242 4242 4242 4242`, fecha futura y CVC 123.
- El webhook confirmará `checkout.session.completed` y marcará orden como PAID.
