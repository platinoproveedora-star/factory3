import { NextResponse } from "next/server";
import { APPS4ALL_COOKIE_NAME, COOKIE_NAME, cookieOptions } from "@/lib/auth";

export async function POST() {
  const res = NextResponse.redirect(new URL("/login", process.env.NEXT_PUBLIC_GPTADS4ALL_URL || "http://localhost:3020"));
  res.cookies.set(COOKIE_NAME, "", cookieOptions(0));
  res.cookies.set(APPS4ALL_COOKIE_NAME, "", cookieOptions(0));
  return res;
}
