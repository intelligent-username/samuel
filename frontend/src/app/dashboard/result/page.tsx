import { redirect } from "next/navigation";

export default function DashboardResultIndexPage() {
  redirect("/history");
}

// legacy redirect — canonical route is /history (see audit 09)
