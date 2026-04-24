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
  const pitch = req.nextUrl.searchParams.get("pitch") ?? "-2.0";
  if (!voiceId) {
    return NextResponse.json({ detail: "Missing voiceId" }, { status: 400 });
  }

  try {
    const res = await fetch(
      `${API_BASE}/voices/preview/thought?voice_id=${encodeURIComponent(voiceId)}&pitch_semitones=${encodeURIComponent(pitch)}`,
      {
        headers: { Authorization: `Bearer ${session.access_token}` },
        cache: "no-store",
      }
    );
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return NextResponse.json({ detail: text || "Thought preview generation failed" }, { status: res.status });
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
    return NextResponse.json({ detail: "Backend unavailable while previewing thought voice" }, { status: 503 });
  }
}
