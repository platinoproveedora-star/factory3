const PROFILE = "platform";

export type PlatformUser = {
  id: string;
  email: string;
  nombre?: string;
  password_hash: string;
};

export type AccessGrant = {
  id: string;
  user_id: string;
  modulo_code: string;
  role: string;
  company_id: string;
  status: string;
  plan_code?: string | null;
  subscription_status?: string | null;
};

export type Company = {
  company_id: string;
  name: string;
  status?: string;
};

function platformEnv() {
  const url = process.env.PLATFORM_SUPABASE_URL?.replace(/\/$/, "");
  const key = process.env.PLATFORM_SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("PLATFORM_SUPABASE_URL y PLATFORM_SUPABASE_SERVICE_ROLE_KEY requeridos");
  return { url, key };
}

async function platformFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { url, key } = platformEnv();
  const res = await fetch(`${url}/rest/v1/${path}`, {
    ...init,
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Accept-Profile": PROFILE,
      "Content-Profile": PROFILE,
      "Content-Type": "application/json",
      Prefer: "return=representation",
      ...(init.headers || {})
    },
    cache: "no-store"
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`platform ${res.status}: ${text}`);
  return text ? (JSON.parse(text) as T) : ([] as T);
}

export async function findUserByEmail(email: string) {
  const qs = new URLSearchParams({
    email: `eq.${email.toLowerCase()}`,
    select: "id,email,nombre,password_hash",
    limit: "1"
  });
  const rows = await platformFetch<PlatformUser[]>(`users?${qs.toString()}`);
  return rows[0] || null;
}

export async function listGrants(userId: string) {
  const qs = new URLSearchParams({
    user_id: `eq.${userId}`,
    status: "in.(active,trialing,manual,comped)",
    select: "id,user_id,company_id,modulo_code,role,status,plan_code,subscription_status",
    order: "company_id.asc,modulo_code.asc"
  });
  return platformFetch<AccessGrant[]>(`access_grants?${qs.toString()}`);
}

export async function listCompanies(companyIds: string[]) {
  if (!companyIds.length) return [] as Company[];
  const quoted = companyIds.map((id) => `"${id}"`).join(",");
  const qs = new URLSearchParams({
    company_id: `in.(${quoted})`,
    select: "company_id,name,status"
  });
  return platformFetch<Company[]>(`companies?${qs.toString()}`);
}

export async function logLoginAttempt(email: string, ip: string, success: boolean) {
  try {
    await platformFetch("login_attempts", {
      method: "POST",
      body: JSON.stringify({ email: email.toLowerCase(), ip, success })
    });
  } catch {
    // Login should not fail because telemetry could not be written.
  }
}

export function companyName(companies: Company[], companyId: string) {
  return companies.find((company) => company.company_id === companyId)?.name || companyId;
}

export async function createPlatformUser(email: string, nombre: string, passwordHash: string): Promise<PlatformUser> {
  const rows = await platformFetch<PlatformUser[]>("users", {
    method: "POST",
    body: JSON.stringify({ email: email.toLowerCase(), nombre, password_hash: passwordHash })
  });
  return rows[0];
}

export async function createCompany(companyId: string, name: string): Promise<Company> {
  const rows = await platformFetch<Company[]>("companies", {
    method: "POST",
    body: JSON.stringify({ company_id: companyId, name, status: "active" })
  });
  return rows[0];
}

export async function createGrant(userId: string, companyId: string, moduloCode: string, role = "admin"): Promise<AccessGrant> {
  const rows = await platformFetch<AccessGrant[]>("access_grants", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      company_id: companyId,
      modulo_code: moduloCode,
      role,
      status: "manual",
      plan_code: "manual",
      subscription_status: "manual"
    })
  });
  return rows[0];
}
