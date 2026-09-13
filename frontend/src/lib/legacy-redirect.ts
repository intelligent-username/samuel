import { redirect } from "next/navigation";

/**
 * Redirect legacy result routes to canonical history.
 */
export function redirectToHistory(): never {
  redirect("/history");
}
