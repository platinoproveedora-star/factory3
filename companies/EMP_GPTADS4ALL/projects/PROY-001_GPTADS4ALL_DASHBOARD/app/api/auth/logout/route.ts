import { NextResponse } from "next/server";
import { COOKIE_NAME, cookieOptions } from "@/lib/auth";

export async function POST() {
  const res = NextResponse.redirect(new URL("/", process.env.NEXT_PUBLIC_APPS4ALL_URL || "http://localhost:3018"));
  res.cookies.set(COOKIE_NAME, "", cookieOptions(0));
  return res;
}
