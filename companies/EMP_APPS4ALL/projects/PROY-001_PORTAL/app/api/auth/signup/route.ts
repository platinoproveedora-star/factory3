import { NextRequest, NextResponse } from "next/server";
import { hash } from "@node-rs/argon2";
import { cookieOptions, COOKIE_NAME, signSession } from "@/lib/auth";
import { createCompany, createGrant, createPlatformUser, findUserByEmail } from "@/lib/platform";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const CATEGORIES_DEFAULT = [
  "combustible",
  "taller y mantenimiento",
  "nomina",
  "recargas celulares",
  "gastos varios",
  "alimentacion",
  "hospedaje",
  "peajes y casetas",
  "refacciones",
  "papeleria",
  "servicios",
  "otros"
];

function generateCompanyId(name: string): string {
  const slug = name.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 10);
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `EMP_${slug}_${rand}`;
}

async function seedCategories(companyId: string) {
  const url = process.env.SUPABASE_URL?.replace(/\/$/, "");
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return;
  const rows = CATEGORIES_DEFAULT.map((nombre, i) => ({
    folio: `CAT-${String(i + 1).padStart(3, "0")}`,
    nombre,
    activo: true,
    empresa_id: companyId
  }));
  await fetch(`${url}/rest/v1/categorias_gasto`, {
    method: "POST",
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Accept-Profile": "gastos4all",
      "Content-Profile": "gastos4all",
      "Content-Type": "application/json",
      Prefer: "return=minimal"
    },
    body: JSON.stringify(rows),
    cache: "no-store"
  }).catch(() => null);
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const company_name = String(body?.company_name || "").trim();
  const email = String(body?.email || "").trim().toLowerCase();
  const password = String(body?.password || "");
  const password_confirm = String(body?.password_confirm || "");

  if (!company_name) return NextResponse.json({ ok: false, error: "nombre de empresa requerido" }, { status: 400 });
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ ok: false, error: "email invalido" }, { status: 400 });
  }
  if (password.length < 8) return NextResponse.json({ ok: false, error: "password debe tener al menos 8 caracteres" }, { status: 400 });
  if (password !== password_confirm) return NextResponse.json({ ok: false, error: "las passwords no coinciden" }, { status: 400 });

  try {
    const existing = await findUserByEmail(email);
    if (existing) return NextResponse.json({ ok: false, error: "El email ya esta registrado" }, { status: 409 });

    const passwordHash = await hash(password, { memoryCost: 65536, timeCost: 2, parallelism: 2 });
    const user = await createPlatformUser(email, company_name, passwordHash);
    const companyId = generateCompanyId(company_name);
    await createCompany(companyId, company_name);
    await createGrant(user.id, companyId, "apps4all_portal");
    await createGrant(user.id, companyId, "gastos");
    await seedCategories(companyId);

    const token = await signSession({
      sub: user.id,
      email: user.email,
      company_id: companyId,
      company_name,
      modulo_code: "apps4all_portal",
      role: "admin",
      plan_code: "manual",
      subscription_status: "manual"
    });
    const res = NextResponse.json({ ok: true });
    res.cookies.set(COOKIE_NAME, token, cookieOptions(7200));
    return res;
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "registro fallo" }, { status: 500 });
  }
}
