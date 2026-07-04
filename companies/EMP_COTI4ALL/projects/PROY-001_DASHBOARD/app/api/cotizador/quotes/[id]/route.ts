import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { fetchQuoteById, getCompanyContextFromSession } from "@/lib/coti4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const { id } = await params;
  const companyId = req.nextUrl.searchParams.get("company_id") || user.company_id;
  const context = await getCompanyContextFromSession({ ...user, company_id: companyId });
  const result = await fetchQuoteById(context, id);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
