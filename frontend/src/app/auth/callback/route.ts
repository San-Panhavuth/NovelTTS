import { type NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const redirectTo = requestUrl.searchParams.get("redirectTo");

  if (!isSupabaseConfigured()) {
    return NextResponse.redirect(
      new URL("/login?message=Supabase env is not configured.", request.url)
    );
  }

  if (code) {
    const supabase = await createSupabaseServerClient();
    await supabase.auth.exchangeCodeForSession(code);
  }

  const destination = redirectTo ? `/${redirectTo}` : "/";
  return NextResponse.redirect(new URL(destination, request.url));
}
