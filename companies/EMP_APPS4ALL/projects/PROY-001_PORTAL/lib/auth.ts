import { jwtVerify, SignJWT } from "jose";
import { cookies } from "next/headers";

export const COOKIE_NAME = "apps4all_token";

export type SessionUser = {
  sub: string;
  email: string;
  company_id: string;
  company_name?: string;
  modulo_code: string;
  role: string;
  grant_id?: string;
  plan_code?: string;
  subscription_status?: string;
  exp: number;
};

function jwtSecret() {
  const secret = process.env.PLATFORM_JWT_SECRET;
  if (!secret || secret.length < 32) throw new Error("PLATFORM_JWT_SECRET requerido >= 32 chars");
  return new TextEncoder().encode(secret);
}

export async function signSession(payload: Omit<SessionUser, "exp">, maxAge = 7200) {
  const now = Math.floor(Date.now() / 1000);
  return new SignJWT(payload)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt(now)
    .setExpirationTime(now + maxAge)
    .sign(jwtSecret());
}

export async function getSession(): Promise<SessionUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
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
    maxAge
  };
}

export function activeSubscription(status?: string) {
  return ["active", "trialing", "manual", "comped"].includes(String(status || "manual"));
}
