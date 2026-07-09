import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  // El documento imprimible siempre se arma aqui con los campos propios del
  // formulario (empresa que cotiza, obra, lugar de entrega, notas). El skill
  // vertical_coti4all/coti4all_quote_pdf usa una plantilla generica que no
  // conoce esos campos, asi que no se usa para este preview en vivo.
  return NextResponse.json(buildQuoteDocument(body, user), { status: 200 });
}

function buildQuoteDocument(quote: any, user: any) {
  const lines = Array.isArray(quote.lineas) ? quote.lineas : [];
  const money = new Intl.NumberFormat("es-MX", { style: "currency", currency: quote.moneda || "MXN" });
  const subtotal = lines.reduce((acc: number, line: any) => {
    const qty = Number(line.cantidad || 0);
    const price = Number(line.precio_unitario || 0);
    return acc + qty * price;
  }, 0);
  const iva = subtotal * 0.16;
  const total = subtotal + iva;
  const companyName = quote.empresa_cotiza || "Empresa que cotiza";
  const logoDataUrl = safeImageDataUrl(quote.logo_data_url);
  const title = "Cotizacion";
  const docTitle = quote.folio ? `${title} ${quote.folio}` : title;
  const html = `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(docTitle)}</title>
  <style>
    :root { color-scheme: light; }
    body { margin: 0; background: #f4f6f8; color: #1f2933; font-family: Arial, sans-serif; }
    .page { max-width: 860px; margin: 24px auto; background: #fff; padding: 36px; border: 1px solid #d9e1e8; }
    .save-pdf-bar { max-width: 860px; margin: 16px auto 0; display: flex; justify-content: flex-end; }
    .save-pdf-btn { background: #1d4ed8; color: #fff; border: none; border-radius: 6px; padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer; }
    .save-pdf-btn:hover { background: #1e40af; }
    .top { display: flex; justify-content: space-between; gap: 24px; border-bottom: 2px solid #1d4ed8; padding-bottom: 18px; }
    .brand { min-width: 240px; }
    .brand-logo { display: block; max-width: 190px; max-height: 92px; object-fit: contain; margin: 0 0 10px; }
    .brand-name { margin: 0 0 6px; font-size: 14px; color: #475569; text-transform: uppercase; letter-spacing: .08em; }
    h1 { margin: 0; font-size: 28px; color: #0f172a; }
    h2 { margin: 0 0 8px; font-size: 14px; color: #475569; text-transform: uppercase; letter-spacing: .08em; }
    .muted { color: #64748b; font-size: 13px; line-height: 1.5; }
    .box { margin-top: 24px; border: 1px solid #e2e8f0; padding: 16px; page-break-inside: avoid; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 20px; }
    .label { color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }
    .value { margin-top: 3px; font-size: 14px; color: #0f172a; }
    table { width: 100%; border-collapse: collapse; margin-top: 24px; font-size: 13px; }
    th { background: #f1f5f9; color: #475569; text-align: left; padding: 10px; border-bottom: 1px solid #cbd5e1; }
    td { padding: 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
    .num { text-align: right; white-space: nowrap; }
    .totals { margin-left: auto; margin-top: 20px; width: 280px; font-size: 14px; }
    .totals div { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid #e2e8f0; }
    .total { font-weight: 700; color: #0f172a; font-size: 18px; }
    @media print { body { background: #fff; } .page { margin: 0; border: 0; max-width: none; } .no-print { display: none !important; } }
  </style>
</head>
<body>
  <div class="save-pdf-bar no-print">
    <button type="button" class="save-pdf-btn" onclick="window.print()">Guardar PDF</button>
  </div>
  <main class="page">
    <section class="top">
      <div class="brand">
        ${logoDataUrl ? `<img class="brand-logo" src="${escapeHtml(logoDataUrl)}" alt="Logo" />` : ""}
        <p class="brand-name">${escapeHtml(companyName)}</p>
        <h1>${escapeHtml(title)}${quote.folio ? ` ${escapeHtml(String(quote.folio))}` : ""}</h1>
      </div>
      <div class="muted">
        ${quote.folio ? `<strong>Folio:</strong> ${escapeHtml(String(quote.folio))}<br />` : ""}
        <strong>Fecha:</strong> ${new Date().toLocaleDateString("es-MX")}<br />
        <strong>Moneda:</strong> ${escapeHtml(quote.moneda || "MXN")}<br />
        <strong>Validez:</strong> ${escapeHtml(String(quote.validez_dias || 30))} dias
      </div>
    </section>
    <section class="box">
      <h2>Datos Cotizacion</h2>
      <div class="grid">
        <div><div class="label">Empresa</div><div class="value">${escapeHtml(quote.cliente_empresa || "Sin empresa")}</div></div>
        <div><div class="label">Atencion a:</div><div class="value">${escapeHtml(quote.cliente_persona || quote.cliente_nombre || "Sin contacto")}</div></div>
        <div><div class="label">Obra</div><div class="value">${escapeHtml(quote.obra || "-")}</div></div>
        <div><div class="label">Lugar de entrega</div><div class="value">${escapeHtml(quote.lugar_entrega || "-")}</div></div>
      </div>
    </section>
    ${quote.nota1 ? `<section class="box"><div class="value">${escapeHtml(quote.nota1)}</div></section>` : ""}
    <table>
      <thead>
        <tr>
          <th>Producto / concepto</th>
          <th class="num">Cantidad</th>
          <th>Unidad</th>
          <th class="num">Precio</th>
          <th class="num">Importe</th>
        </tr>
      </thead>
      <tbody>
        ${
          lines.length
            ? lines
                .map((line: any) => {
                  const qty = Number(line.cantidad || 0);
                  const price = Number(line.precio_unitario || 0);
                  const amount = qty * price;
                  return `<tr>
            <td>${escapeHtml(line.nombre || "Producto")}</td>
            <td class="num">${escapeHtml(String(qty))}</td>
            <td>${escapeHtml(line.unidad || "PZA")}</td>
            <td class="num">${money.format(price)}</td>
            <td class="num">${money.format(amount)}</td>
          </tr>`;
                })
                .join("")
            : `<tr><td colspan="5" class="muted">Sin renglones capturados.</td></tr>`
        }
      </tbody>
    </table>
    <section class="totals">
      <div><span>Subtotal</span><strong>${money.format(subtotal)}</strong></div>
      <div><span>IVA (16%)</span><strong>${money.format(iva)}</strong></div>
      <div class="total"><span>Total</span><strong>${money.format(total)}</strong></div>
    </section>
    ${renderNotes(quote)}
  </main>
</body>
</html>`;
  return { ok: true, html, filename: "cotizacion.html", source: "local_fallback" };
}

function renderNotes(quote: any) {
  const notes = [quote.nota2, quote.nota3].map((note) => String(note || "").trim()).filter(Boolean);
  if (!notes.length) return "";
  return `<section class="box"><h2>Notas</h2>${notes.map((note, index) => `<div class="value">${index + 1}. ${escapeHtml(note)}</div>`).join("")}</section>`;
}

function safeImageDataUrl(value: unknown) {
  const dataUrl = String(value || "").trim();
  if (/^data:image\/(?:png|jpe?g|webp|gif);base64,[a-z0-9+/=]+$/i.test(dataUrl)) return dataUrl;
  return "";
}

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
