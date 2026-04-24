import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

  const voiceId = req.nextUrl.searchParams.get("voiceId");
  if (!voiceId) {
    return NextResponse.json({ detail: "Missing voiceId" }, { status: 400 });
  }

  try {
    const res = await fetch(`${API_BASE}/voices/preview?voice_id=${encodeURIComponent(voiceId)}`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return NextResponse.json({ detail: text || "Preview generation failed" }, { status: res.status });
    }
    const audioBuffer = await res.arrayBuffer();
    return new NextResponse(audioBuffer, {
      status: 200,
      headers: {
        "Content-Type": "audio/mpeg",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Backend unavailable while previewing voice" }, { status: 503 });
  }
}
