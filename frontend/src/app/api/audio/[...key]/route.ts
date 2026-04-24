import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ key: string[] }> }
) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

  const { key } = await params;
  if (!key || key.length < 3) {
    return NextResponse.json({ detail: "Invalid audio key" }, { status: 400 });
  }

  const [audioPrefix, bookId, chapterFilename] = key;
  if (audioPrefix !== "audio" || !chapterFilename.endsWith(".mp3")) {
    return NextResponse.json({ detail: "Invalid audio key" }, { status: 400 });
  }
  const chapterId = chapterFilename.replace(/\.mp3$/i, "");

  try {
    const res = await fetch(`${API_BASE}/audio/${bookId}/${chapterId}.mp3`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
      cache: "no-store",
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return NextResponse.json(
        { detail: text || "Failed to fetch audio from backend" },
        { status: res.status }
      );
    }

    const audioBuffer = await res.arrayBuffer();
    return new NextResponse(audioBuffer, {
      status: 200,
      headers: {
        "Content-Type": "audio/mpeg",
        "Cache-Control": "private, max-age=0, must-revalidate",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "Backend unavailable while fetching audio" },
      { status: 503 }
    );
  }
}
