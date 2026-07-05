import { NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth";

export async function POST() {
  const res = NextResponse.redirect(new URL("/login", process.env.NEXT_PUBLIC_APPS4ALL_URL || "http://localhost:3018"));
  res.cookies.delete(COOKIE_NAME);
  return res;
}
