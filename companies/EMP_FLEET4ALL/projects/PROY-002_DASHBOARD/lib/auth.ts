import { jwtVerify } from "jose";
import { cookies } from "next/headers";

export const COOKIE_NAME = "f4a_token";
export const APPS4ALL_COOKIE_NAME = "apps4all_token";
export const MODULO_CODE = "fleet4all";

function jwtSecret() {
  return new TextEncoder().encode(process.env.PLATFORM_JWT_SECRET!);
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
  const cookieStore = await cookies();
  const token = cookieStore.get(APPS4ALL_COOKIE_NAME)?.value || cookieStore.get(COOKIE_NAME)?.value;
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
