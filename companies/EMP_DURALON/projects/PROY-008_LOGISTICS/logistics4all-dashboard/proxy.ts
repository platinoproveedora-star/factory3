import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth";

export function proxy(req: NextRequest) {
  const token = req.nextUrl.searchParams.get("sso");
  if (!token) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.searchParams.delete("sso");
  const res = NextResponse.redirect(url);
  res.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 7200
  });
  return res;
}

export const config = {
  matcher: ["/"]
};
