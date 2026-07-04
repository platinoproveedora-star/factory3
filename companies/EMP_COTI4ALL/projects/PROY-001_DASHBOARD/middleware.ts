import { NextResponse } from "next/server";
import { jwtVerify } from "jose";

const COOKIE_NAME = "coti4all_token";
const APPS4ALL_COOKIE_NAME = "apps4all_token";

function jwtSecret() {
  return new TextEncoder().encode(process.env.PLATFORM_JWT_SECRET || "");
}

export const middleware = async (req: any) => {
  const publicPaths = ["/login", "/signup", "/_next", "/favicon.ico"];
  const publicPrefixes = ["/_next/static/"];
  const isPublic = publicPaths.includes(req.nextUrl.pathname) || publicPrefixes.some((prefix: string) => req.nextUrl.pathname.startsWith(prefix));

  const ssoToken = req.nextUrl.searchParams.get("sso");
  if (ssoToken) {
    try {
      await jwtVerify(ssoToken, jwtSecret());
      const cleanUrl = new URL(req.nextUrl);
      cleanUrl.searchParams.delete("sso");
      const res = NextResponse.redirect(cleanUrl);
      res.cookies.set(APPS4ALL_COOKIE_NAME, ssoToken, {
        httpOnly: true,
        secure: true,
        sameSite: "lax",
        path: "/",
        maxAge: 7200,
      });
      return res;
    } catch {
      // token invalido o expirado, seguir flujo normal
    }
  }

  const session = req.cookies.get(COOKIE_NAME)?.value || req.cookies.get(APPS4ALL_COOKIE_NAME)?.value;
  if (isPublic && !session) return NextResponse.next();
  if (isPublic && session) {
    return NextResponse.redirect(new URL("/", req.url));
  }
  if (!isPublic && !session) {
    return NextResponse.redirect(new URL("/login", req.url));
  }
  return NextResponse.next();
};

export const config = {
  matcher: ["/((?!api/auth/|api/|static|.*\\..*).*)"]
};
