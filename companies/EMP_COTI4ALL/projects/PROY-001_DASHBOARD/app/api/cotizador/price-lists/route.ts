import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { fetchPriceLists, getCompanyContextFromSession } from "@/lib/coti4all";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await getSession();
  if (!user) return NextResponse.json({ ok: false, error: "No autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const context = await getCompanyContextFromSession(user);
  const result = await fetchPriceLists(
    context,
    searchParams.get("product_id") || undefined,
    searchParams.get("price_list_id") || undefined
  );
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
