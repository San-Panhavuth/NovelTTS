"use client";

import { useState } from "react";
import { updateSegmentCorrection } from "@/app/books/actions";

type Segment = {
  id: string;
  segment_idx: number;
  text: string;
  type: "narration" | "dialogue" | "thought";
  character_id: string | null;
  character_name: string | null;
  confidence: number | null;
  low_confidence: boolean;
};

type ChapterTabsProps = {
  rawText: string;
  segments: Segment[];
  bookId: string;
  chapterIndex: string;
};

function RawTextBody({ text }: { text: string }) {
  const sections = text.split(/={5,}/);

  return (
    <div className="w-full space-y-1 text-sm leading-7 text-zinc-800 dark:text-zinc-200">
      {sections.map((section, sIdx) => (
        <div key={sIdx}>
          {sIdx > 0 && <hr className="my-5 border-zinc-300 dark:border-zinc-700" />}
          <SectionContent text={section.trim()} />
        </div>
      ))}
    </div>
  );
}

function SectionContent({ text }: { text: string }) {
  if (!text) return null;

  // Newline-preserved text (new uploads after backend fix)
  if (text.includes("\n")) {
    return (
      <>
        {text
          .split(/\n+/)
          .filter((l) => l.trim())
          .map((line, i) => (
            <p key={i} className="mb-3 last:mb-0">
              {line}
            </p>
          ))}
      </>
    );
  }

  // Legacy flat text: split on [bracket blocks] — each is a discrete in-world message / system notice
  const parts = text.split(/(\[[^\]]+\])/);
  return (
    <>
      {parts.map((part, i) => {
        const trimmed = part.trim();
        if (!trimmed) return null;
        if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
          return (
            <p key={i} className="mb-2 rounded bg-indigo-50 px-2.5 py-1 font-mono text-xs text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
              {trimmed}
            </p>
          );
        }
        return (
          <p key={i} className="mb-3 last:mb-0">
            {trimmed}
          </p>
        );
      })}
    </>
  );
}

const typeStyles: Record<string, { pill: string; border: string }> = {
  narration: {
    pill: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
    border: "border-l-blue-400",
  },
  dialogue: {
    pill: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
    border: "border-l-amber-400",
  },
  thought: {
    pill: "bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
    border: "border-l-violet-400",
  },
};

export function ChapterTabs({ rawText, segments, bookId, chapterIndex }: ChapterTabsProps) {
  const [activeTab, setActiveTab] = useState<"raw" | "segments">(
    segments.length === 0 ? "raw" : "segments"
  );

  return (
    <div>
      {/* Tab bar */}
      <div className="mb-6 flex gap-1 border-b border-zinc-200 dark:border-zinc-800">
        <button
          onClick={() => setActiveTab("raw")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "raw"
              ? "border-b-2 border-indigo-500 text-indigo-600 dark:text-indigo-400"
              : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          }`}
        >
          Raw Text
        </button>
        <button
          onClick={() => setActiveTab("segments")}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "segments"
              ? "border-b-2 border-indigo-500 text-indigo-600 dark:text-indigo-400"
              : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          }`}
        >
          Segments
          {segments.length > 0 && (
            <span className="rounded-full bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
              {segments.length}
            </span>
          )}
        </button>
      </div>

      {/* Raw Text pane */}
      {activeTab === "raw" && (
        <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6 dark:border-zinc-800 dark:bg-zinc-900/50">
          {rawText ? (
            <RawTextBody text={rawText} />
          ) : (
            <p className="text-sm text-zinc-400">No raw text available for this chapter.</p>
          )}
        </div>
      )}

      {/* Segments pane */}
      {activeTab === "segments" && (
        <>
          {segments.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-zinc-200 py-16 text-center dark:border-zinc-800">
              <p className="text-sm font-medium text-zinc-500">No segments yet</p>
              <p className="mt-1 text-xs text-zinc-400">Click Re-process to run attribution</p>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="mb-4 flex flex-wrap items-center gap-3 text-xs">
                {(["narration", "dialogue", "thought"] as const).map((t) => (
                  <span key={t} className={`rounded-full px-2.5 py-0.5 font-medium ${typeStyles[t].pill}`}>
                    {t}
                  </span>
                ))}
                <span className="ml-2 text-zinc-400">{segments.length} segments</span>
              </div>

              {segments.map((segment) => {
                const styles = typeStyles[segment.type] ?? typeStyles.narration;
                return (
                  <div
                    key={segment.id}
                    className={`rounded-xl border border-zinc-200 border-l-4 bg-white dark:border-zinc-800 dark:bg-zinc-900 ${styles.border} ${
                      segment.low_confidence ? "ring-1 ring-amber-300 dark:ring-amber-700" : ""
                    }`}
                  >
                    <div className="flex items-center gap-2 border-b border-zinc-100 px-4 py-2 dark:border-zinc-800">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles.pill}`}>
                        {segment.type}
                      </span>
                      {segment.character_name && (
                        <span className="text-xs text-zinc-500">{segment.character_name}</span>
                      )}
                      <span className="ml-auto text-xs text-zinc-400">
                        #{segment.segment_idx + 1}
                        {segment.confidence !== null && <> · {(segment.confidence * 100).toFixed(0)}%</>}
                        {segment.low_confidence && <span className="ml-1 text-amber-500">⚠ review</span>}
                      </span>
                    </div>

                    <p className="px-4 py-3 text-sm leading-7 text-zinc-800 dark:text-zinc-200">
                      {segment.text}
                    </p>

                    <form
                      action={updateSegmentCorrection}
                      className="flex flex-wrap items-center gap-2 border-t border-zinc-100 px-4 py-2.5 dark:border-zinc-800"
                    >
                      <input type="hidden" name="bookId" value={bookId} />
                      <input type="hidden" name="chapterIndex" value={chapterIndex} />
                      <input type="hidden" name="segmentId" value={segment.id} />

                      <select
                        name="type"
                        defaultValue={segment.type}
                        className="rounded-md border border-zinc-200 bg-transparent px-2 py-1 text-xs focus:outline-none dark:border-zinc-700"
                      >
                        <option value="narration">narration</option>
                        <option value="dialogue">dialogue</option>
                        <option value="thought">thought</option>
                      </select>

                      <input
                        type="text"
                        name="characterName"
                        defaultValue={segment.character_name ?? ""}
                        placeholder="Character (optional)"
                        className="min-w-40 rounded-md border border-zinc-200 bg-transparent px-2 py-1 text-xs placeholder-zinc-400 focus:outline-none dark:border-zinc-700"
                      />

                      <button
                        type="submit"
                        className="rounded-md bg-zinc-900 px-3 py-1 text-xs text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
                      >
                        Save
                      </button>
                    </form>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
