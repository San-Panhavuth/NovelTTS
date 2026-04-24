"use client";

import { useRef, useState } from "react";

type PitchSliderProps = {
  defaultValue: number;
  inputName?: string;
};

export function PitchSlider({ defaultValue, inputName = "thoughtPitchSemitones" }: PitchSliderProps) {
  const [value, setValue] = useState(defaultValue);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);

  function stopPreview() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlaying(false);
    setLoading(false);
  }

  async function previewThought(event: React.MouseEvent<HTMLButtonElement>) {
    const form = event.currentTarget.closest("form");
    const dialogueInput = form?.querySelector<HTMLInputElement | HTMLSelectElement>(
      'select[name="dialogueVoiceId"], input[name="dialogueVoiceId"]'
    );
    const dialogueVoiceId = dialogueInput?.value ?? "";
    if (!dialogueVoiceId) return;

    stopPreview();
    try {
      setLoading(true);
      const res = await fetch(
        `/api/voices/preview/thought?voiceId=${encodeURIComponent(dialogueVoiceId)}&pitch=${encodeURIComponent(
          value.toString()
        )}`
      );
      if (!res.ok) {
        setLoading(false);
        return;
      }
      const blob = await res.blob();
      const src = URL.createObjectURL(blob);
      const audio = new Audio(src);
      audioRef.current = audio;
      audio.onended = stopPreview;
      audio.onerror = stopPreview;
      await audio.play();
      setPlaying(true);
      setLoading(false);
    } catch {
      stopPreview();
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="thoughtPitch" className="text-sm font-medium">
        Thought Pitch Offset (semitones)
      </label>
      <p className="text-xs text-zinc-500">
        Applied to the dialogue voice for inner-monologue segments. Default: -2 st.
      </p>
      <input
        id="thoughtPitch"
        type="range"
        name={inputName}
        min="-12"
        max="0"
        step="0.5"
        value={value}
        onChange={(e) => setValue(parseFloat(e.target.value))}
        className="w-full"
      />
      <span className="text-xs text-zinc-500">Current: {value} st</span>
      <div>
        <button
          type="button"
          onClick={playing ? stopPreview : previewThought}
          disabled={loading}
          className="rounded-md border px-3 py-1.5 text-xs hover:bg-zinc-100 disabled:opacity-50 dark:hover:bg-zinc-800"
          title="Preview thought voice with current dialogue voice and pitch"
        >
          {playing ? "■ Stop Thought Preview" : loading ? "Loading..." : "▶ Preview Thought Voice"}
        </button>
      </div>
    </div>
  );
}
