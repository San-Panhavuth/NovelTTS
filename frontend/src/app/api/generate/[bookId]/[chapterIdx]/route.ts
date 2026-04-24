import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ bookId: string; chapterIdx: string }> }
) {
  const supabase = await createSupabaseServerClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

  const { bookId, chapterIdx } = await params;
  try {
    const res = await fetch(
      `${API_BASE}/books/${bookId}/chapters/${chapterIdx}/generate`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
      }
    );
    const text = await res.text();
    const data = text ? (JSON.parse(text) as unknown) : {};
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { detail: "Backend unavailable while starting generation" },
      { status: 503 }
    );
  }
}
