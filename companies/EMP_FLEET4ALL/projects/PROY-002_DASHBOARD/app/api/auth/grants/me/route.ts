import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { listCompanies, listGrants } from "@/lib/platform";

export const dynamic = "force-dynamic";

export async function GET() {
  const user = await getSession();
  if (!user) return NextResponse.json({ error: "No autenticado" }, { status: 401 });
  try {
    const grants = await listGrants(user.sub);
    const companyIds = Array.from(new Set(grants.map((grant) => grant.company_id)));
    const companies = await listCompanies(companyIds);
    const company = companies.find((row) => row.company_id === user.company_id);
    return NextResponse.json({
      user: { ...user, company_name: company?.name || user.company_id },
      grants,
      companies,
    });
  } catch (error: any) {
    return NextResponse.json({ error: error?.message || "Token invalido" }, { status: 500 });
  }
}
