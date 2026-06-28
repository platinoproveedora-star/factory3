import { jwtVerify } from "jose";
import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth";

const PUBLIC = ["/login", "/register", "/api/auth/login", "/api/auth/register"];

export async function middleware(req: NextRequest) {
  const path = req.nextUrl.pathname;
  if (PUBLIC.some((p) => path.startsWith(p))) return NextResponse.next();

  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (!token) return NextResponse.redirect(new URL("/login", req.url));

  try {
    const secret = new TextEncoder().encode(process.env.PLATFORM_JWT_SECRET!);
    await jwtVerify(token, secret);
    return NextResponse.next();
  } catch {
    const res = NextResponse.redirect(new URL("/login", req.url));
    res.cookies.delete(COOKIE_NAME);
    return res;
  }
}

export const config = {
  matcher: ["/dashboard/:path*", "/api/rfcs/:path*", "/api/sync/:path*", "/api/cfdis/:path*"],
};
