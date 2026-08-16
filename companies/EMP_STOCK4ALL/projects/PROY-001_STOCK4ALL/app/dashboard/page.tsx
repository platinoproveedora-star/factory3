import { getSession } from "@/lib/auth";
import InventoryPanel from "@/components/InventoryPanel";

export default async function DashboardPage() {
  const user = await getSession();
  if (!user) return null;

  return <InventoryPanel />;
}
