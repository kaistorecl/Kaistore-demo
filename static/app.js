// static/app.js
function toast(msg) {
  try {
    const t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#111;color:#fff;padding:10px 14px;border-radius:10px;font-size:14px;z-index:9999;opacity:0.95';
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  } catch (_) { alert(msg); }
}

document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('.buy-btn');

  buttons.forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        // 1) Preferimos product_id + qty (lo que espera el API)
        const pid = Number(btn.dataset.productId);
        let payload;

        if (Number.isFinite(pid) && pid > 0) {
          payload = { items: [{ product_id: pid, qty: 1 }] };
        } else {
          // 2) Fallback: title/price/quantity/currency
          const title = (btn.dataset.title || '').trim();
          const price = Number(btn.dataset.price);
          const currency = (btn.dataset.currency || 'CLP').trim();
          if (!title || !Number.isFinite(price)) {
            toast('No se pudo preparar el checkout (faltan datos).');
            return;
          }
          payload = { items: [{ title, price, quantity: 1, currency }] };
        }

        // Llamada al backend
        const res = await fetch('/api/orders/checkout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const raw = await res.text();
        let data = null;
        try { data = raw ? JSON.parse(raw) : null; } catch { /* ignore */ }

        if (!res.ok) {
          const detail = data && (data.detail || data.message) ? `: ${data.detail || data.message}` : ` (HTTP ${res.status})`;
          toast('No se pudo iniciar el pago' + detail);
          console.error('Checkout error:', res.status, raw);
          return;
        }

        if (!data || !data.url) {
          toast('Respuesta inválida del backend (falta url).');
          console.error('Respuesta sin url:', raw);
          return;
        }

        // Redirigir a Stripe
        window.location.href = data.url;

      } catch (err) {
        console.error(err);
        toast('Error de red al iniciar el pago.');
      }
    });
  });
});
