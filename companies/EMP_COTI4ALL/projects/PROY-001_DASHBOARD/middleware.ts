import { NextResponse } from "next/server";

const COOKIE_NAME = "coti4all_token";
const APPS4ALL_COOKIE_NAME = "apps4all_token";

export const middleware = (req: any) => {
  const publicPaths = ["/login", "/signup", "/_next", "/favicon.ico"];
  const publicPrefixes = ["/_next/static/"];
  const isPublic = publicPaths.includes(req.nextUrl.pathname) || publicPrefixes.some((prefix) => req.nextUrl.pathname.startsWith(prefix));
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
