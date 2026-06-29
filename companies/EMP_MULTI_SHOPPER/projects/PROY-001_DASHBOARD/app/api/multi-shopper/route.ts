import { NextRequest, NextResponse } from "next/server";
import { baseContext, dataSkill } from "@/lib/factory";
import { emptyDashboardData } from "@/lib/types";

const DATA_SKILL = "vertical_multi_shopper/multi_shopper_dashboard_data";

export async function GET(req: NextRequest) {
  const params = Object.fromEntries(req.nextUrl.searchParams.entries());
  const result = await dataSkill(DATA_SKILL, baseContext(params));
  if (!result.ok) {
    return NextResponse.json({
      ok: true,
      data: emptyDashboardData,
      warning: result.error,
    });
  }
  return NextResponse.json({ ok: true, data: result.data || emptyDashboardData });
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const skill = typeof body.skill === "string" && body.skill ? body.skill : DATA_SKILL;
  const { skill: _skill, ...payload } = body;
  if (!payload.bucket && process.env.MULTI_SHOPPER_STORAGE_BUCKET) {
    payload.bucket = process.env.MULTI_SHOPPER_STORAGE_BUCKET;
  }
  const result = await dataSkill(skill, baseContext({ ...payload, dry_run: payload.dry_run ?? false }));
  if (!result.ok) {
    return NextResponse.json({ ok: false, error: result.error }, { status: 400 });
  }
  return NextResponse.json({ ok: true, data: result.data });
}
