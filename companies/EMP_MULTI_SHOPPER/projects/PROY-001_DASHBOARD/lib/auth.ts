import { jwtVerify } from "jose";
import { cookies } from "next/headers";

export const COOKIE_NAME = "multi_shopper_token";

export function moduloCode() {
  const code = process.env.MULTI_SHOPPER_MODULE_CODE;
  if (!code) throw new Error("MULTI_SHOPPER_MODULE_CODE requerido");
  return code;
}

function jwtSecret() {
  const secret = process.env.PLATFORM_JWT_SECRET;
  if (!secret) throw new Error("PLATFORM_JWT_SECRET requerido");
  return new TextEncoder().encode(secret);
}

export interface SessionUser {
  sub: string;
  email: string;
  modulo_code: string;
  company_id?: string;
  role?: string;
  grant_id?: string;
  plan_code?: string;
  subscription_status?: string;
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
