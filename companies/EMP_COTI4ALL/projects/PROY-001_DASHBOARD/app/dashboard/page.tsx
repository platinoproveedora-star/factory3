import { redirect } from "next/navigation";

export default function DashboardPage() {
  redirect(process.env.NEXT_PUBLIC_APPS4ALL_URL || "http://localhost:3018");
}
