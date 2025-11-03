// ======= CONFIG RÁPIDA (editas desde el celular) =======

// 1) Pega aquí tus Payment Links por id de producto:
const PAYMENT_LINKS = {
  // "1": "https://buy.stripe.com/test_xxxxxxxxxxxxx",
  // "2": "https://buy.stripe.com/test_yyyyyyyyyyyyy",
};

// 2) (Opcional) Tu WhatsApp como 569XXXXXXXX:
const WHATSAPP_PHONE = ""; // ejemplo: "56987654321"

// =======================================================

const API = "/api";
const grid = document.getElementById("grid");
const empty = document.getElementById("empty");
const q = document.getElementById("q");
const toast = document.getElementById("toast");

function moneyCLP(n){ try { return n.toLocaleString("es-CL",{style:"currency",currency:"CLP"}); } catch { return "$"+(n||0).toString(); } }
function showToast(msg){ toast.textContent = msg; toast.classList.add("show"); setTimeout(()=>toast.classList.remove("show"), 2200); }

async function fetchJSON(url, opts){
  const r = await fetch(url, opts);
  if(!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

async function loadProducts(){
  try{
    const items = await fetchJSON(`${API}/products/published`);
    renderProducts(items || []);
  }catch(e){
    console.error("Error listando productos:", e);
    renderProducts([]);
  }
}

function renderProducts(items){
  grid.innerHTML = "";
  const term = (q.value||"").trim().toLowerCase();
  const list = items.filter(p => {
    if(!term) return true;
    return (p.title_marketing||"").toLowerCase().includes(term) ||
           (p.description_long||"").toLowerCase().includes(term);
  });

  if(list.length === 0){
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";

  for(const p of list){
    const el = document.createElement("div");
    el.className = "card";
    const img = p.image_url || "https://picsum.photos/seed/rail/800/600";
    const title = p.title_marketing || p.marketing_title || "Producto";
    const desc = p.short_bullets || p.description_short || (p.description_long||"").slice(0,80);
    const price = p.price ?? 5990;

    el.innerHTML = `
      <img src="${img}" alt="${title}">
      <div class="pad">
        <div class="title">${title}</div>
        <div class="desc">${desc}</div>
        <div class="price">${moneyCLP(price)}</div>
        <button class="btn" data-id="${p.id||""}">Comprar ahora</button>
      </div>
    `;
    const btn = el.querySelector("button");
    btn.addEventListener("click", () => handleBuy(p));
    grid.appendChild(el);
  }
}

function openWhatsApp(p){
  if(!WHATSAPP_PHONE){ showToast("Pago no disponible. Falta configurar WhatsApp."); return; }
  const txt = encodeURIComponent(`Hola! Quiero comprar: ${p.title_marketing || "Producto"} (${moneyCLP(p.price||0)}).`);
  const url = `https://wa.me/${WHATSAPP_PHONE}?text=${txt}`;
  window.open(url, "_blank");
}

async function handleBuy(p){
  try{
    // 1) Si hay Payment Link configurado para este producto, úsalo.
    const link = PAYMENT_LINKS[String(p.id)];
    if(link){ window.location.href = link; return; }

    // 2) Sin Payment Link: intenta el checkout del backend (si está operativo).
    try{
      const body = { items: [{ product_id: p.id, qty: 1 }] };
      const r = await fetchJSON(`${API}/orders/checkout`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(body)
      });
      // Soportar dos posibles respuestas:
      if(r && r.url){ window.location.href = r.url; return; }
      if(typeof r === "string" && r.length > 10){
        window.location.href = `${API}/payments/session/${r}`;
        return;
      }
      // Si nada de lo anterior aplica, pasamos a WhatsApp.
      console.warn("Respuesta checkout inesperada:", r);
      openWhatsApp(p);
    }catch(e){
      console.warn("Fallo checkout backend, usando WhatsApp:", e);
      openWhatsApp(p);
    }
  }catch(e){
    console.error(e);
    showToast("No se pudo iniciar el pago");
  }
}

// Búsqueda
q?.addEventListener("input", () => loadProducts());

// Arranque
loadProducts();
