import { jwtVerify } from "jose";
import { NextRequest, NextResponse } from "next/server";
import { APPS4ALL_COOKIE_NAME, COOKIE_NAME } from "@/lib/auth";

const PUBLIC = ["/login", "/register", "/api/auth/login", "/api/auth/register"];

export async function middleware(req: NextRequest) {
  const path = req.nextUrl.pathname;

  const ssoToken = req.nextUrl.searchParams.get("sso");
  if (ssoToken) {
    try {
      const secret = new TextEncoder().encode(process.env.PLATFORM_JWT_SECRET!);
      await jwtVerify(ssoToken, secret);
      const cleanUrl = new URL(req.nextUrl);
      cleanUrl.searchParams.delete("sso");
      const res = NextResponse.redirect(cleanUrl);
      res.cookies.set(APPS4ALL_COOKIE_NAME, ssoToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 7200,
      });
      return res;
    } catch {
      // token invalido o expirado, seguir flujo normal
    }
  }

  if (PUBLIC.some((p) => path.startsWith(p))) return NextResponse.next();

  const token = req.cookies.get(COOKIE_NAME)?.value || req.cookies.get(APPS4ALL_COOKIE_NAME)?.value;
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
  matcher: [
    "/",
    "/dashboard/:path*",
    "/api/viajes/:path*",
    "/api/gastos/:path*",
    "/api/cobranza/:path*",
    "/api/cartaporte/:path*",
    "/api/liquidaciones/:path*",
    "/api/combustible/:path*",
    "/api/mantenimiento/:path*",
    "/api/cotizaciones/:path*",
  ],
};
