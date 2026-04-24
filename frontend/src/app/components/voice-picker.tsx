"use client";

import { useRef, useState } from "react";

export type VoiceOption = {
  id: string;
  name: string;
  provider: string;
  provider_id: string;
  locale: string | null;
  sample_url: string | null;
};

type VoicePickerProps = {
  label: string;
  description?: string;
  name: string;
  voices: VoiceOption[];
  defaultValue: string;
  placeholder?: string;
};

export function VoicePicker({
  label,
  description,
  name,
  voices,
  defaultValue,
  placeholder = "(none)",
}: VoicePickerProps) {
  const [selected, setSelected] = useState(defaultValue);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const currentVoice = voices.find((v) => v.provider_id === selected);
  const sampleUrl = currentVoice?.sample_url ?? null;

  async function handlePreview() {
    if (!selected) return;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlaying(false);
    }
    try {
      setLoadingPreview(true);
      let audioSrc = sampleUrl;
      if (!audioSrc) {
        const res = await fetch(`/api/voices/preview?voiceId=${encodeURIComponent(selected)}`);
        if (!res.ok) {
          setLoadingPreview(false);
          return;
        }
        const blob = await res.blob();
        audioSrc = URL.createObjectURL(blob);
      }

      const audio = new Audio(audioSrc);
      audioRef.current = audio;
      audio.onended = () => {
        setPlaying(false);
        setLoadingPreview(false);
      };
      audio.onerror = () => {
        setPlaying(false);
        setLoadingPreview(false);
      };
      await audio.play();
      setPlaying(true);
    } catch {
      setPlaying(false);
      setLoadingPreview(false);
    }
  }

  function handleStop() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlaying(false);
      setLoadingPreview(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={name} className="text-sm font-medium">
        {label}
      </label>
      {description && <p className="text-xs text-zinc-500">{description}</p>}
      <div className="flex items-center gap-2">
        <select
          id={name}
          name={name}
          value={selected}
          onChange={(e) => {
            setSelected(e.target.value);
            handleStop();
          }}
          className="flex-1 rounded-md border px-3 py-2 text-sm focus:outline-none dark:bg-zinc-900"
        >
          <option value="">{placeholder}</option>
          {voices.map((v) => (
            <option key={v.id} value={v.provider_id}>
              {v.name} — {v.provider}
              {v.locale ? ` (${v.locale})` : ""}
            </option>
          ))}
        </select>

        {selected ? (
          <button
            type="button"
            onClick={playing ? handleStop : handlePreview}
            disabled={loadingPreview}
            className="shrink-0 rounded-md border px-3 py-2 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-800"
            title={playing ? "Stop preview" : "Preview voice"}
          >
            {playing ? "■ Stop" : loadingPreview ? "Loading..." : "▶ Preview"}
          </button>
        ) : (
          <span className="shrink-0 px-3 py-2 text-xs text-zinc-400">No preview</span>
        )}
      </div>
    </div>
  );
}
