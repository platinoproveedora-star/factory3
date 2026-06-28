import { jwtVerify } from "jose";
import { cookies } from "next/headers";

export const COOKIE_NAME = "c4a_token";
export const MODULO_CODE = "conta4all";

function jwtSecret() {
  return new TextEncoder().encode(process.env.PLATFORM_JWT_SECRET!);
}

export interface SessionUser {
  sub: string;
  email: string;
  modulo_code: string;
  exp: number;
}

export async function getSession(): Promise<SessionUser | null> {
  const token = (await cookies()).get(COOKIE_NAME)?.value;
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, jwtSecret());
    return payload as unknown as SessionUser;
  } catch {
    return null;
  }
}

export function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict" as const,
    path: "/",
    maxAge,
  };
}
