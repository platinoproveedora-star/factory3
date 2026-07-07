import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { createQuote, fetchQuoteList, getCompanyContextFromSession } from "@/lib/coti4all";
import { requireCompanyModuleGrant } from "@/lib/platform";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const companyId = req.nextUrl.searchParams.get("company_id") || user.company_id;
  try {
    await requireCompanyModuleGrant(user.sub, companyId);
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const search = req.nextUrl.searchParams.get("search") || undefined;
  const context = await getCompanyContextFromSession({ ...user, company_id: companyId });
  const result = await fetchQuoteList(context, { search });
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}

export async function POST(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const companyId = body.company_id || user.company_id;
  try {
    await requireCompanyModuleGrant(user.sub, companyId);
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error?.message || "Sin acceso" }, { status: 403 });
  }
  const context = await getCompanyContextFromSession({ ...user, company_id: companyId });
  const result = await createQuote(context, body, false);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
