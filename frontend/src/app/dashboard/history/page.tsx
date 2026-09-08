import { redirect } from "next/navigation";

export default function DashboardHistoryPage() {
  redirect("/history");
}

// legacy redirect — canonical route is /history (see audit 09)
