import { redirect } from "next/navigation";
import { getSession, type SessionUser } from "@/lib/auth";
import { requireCompanyModuleGrant } from "@/lib/platform";

const MODULE_CODE = process.env.MODULE_CODE || "factu4all";

export async function requireModuleSession(): Promise<SessionUser> {
  const user = await getSession();
  if (!user) {
    redirect("/login");
  }
  try {
    await requireCompanyModuleGrant(user.sub, user.company_id, MODULE_CODE);
  } catch {
    redirect("/login");
  }
  return user;
}
