"use client";

import { useEffect, useRef, useState } from "react";
import { Fixy } from "@/components/fixy/fixy";
import { Icon, type IconName } from "@/components/ui/icons";
import { Bubble } from "@/components/ui/parts";
import { type Lang, type StringKey, t } from "@/lib/i18n";
import { speechSupported } from "@/lib/media";

export function Welcome({ lang, onDone }: { lang: Lang; onDone: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDone, 1800);
    return () => clearTimeout(timer);
  }, [onDone]);

  return (
    <button
      type="button"
      onClick={onDone}
      className="relative flex flex-1 flex-col items-center justify-center gap-6"
      aria-label={t("hello", lang)}
    >
      <div className="absolute size-80 rounded-full bg-brand-subtle" aria-hidden="true" />
      <div className="relative">
        <Bubble>
          <p className="text-2xl font-semibold">{t("hello", lang)}</p>
        </Bubble>
      </div>
      <Fixy mood="wave" size={220} className="relative" />
    </button>
  );
}

function RoundAction({
  icon,
  label,
  big,
  onClick,
}: {
  icon: IconName;
  label: string;
  big?: boolean;
  onClick: () => void;
}) {
  return (
    <div className={`flex flex-col items-center gap-2 ${big ? "" : "pt-4"}`}>
      <button
        type="button"
        onClick={onClick}
        aria-label={label}
        className={
          big
            ? "grid size-24 place-items-center rounded-full bg-brand text-on-brand shadow-lift transition-transform active:scale-95"
            : "grid size-15 place-items-center rounded-full border border-line bg-surface text-[var(--color-icon-default)] transition-transform active:scale-95"
        }
      >
        <Icon name={icon} size={big ? 40 : 24} />
      </button>
      <span className="text-sm font-medium text-muted">{label}</span>
    </div>
  );
}

export function Home({
  lang,
  onLang,
  onType,
  onTalk,
  onPhoto,
}: {
  lang: Lang;
  onLang: () => void;
  onType: () => void;
  onTalk: () => void;
  onPhoto: (file: File) => void;
}) {
  const [notice, setNotice] = useState<StringKey | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 3000);
    return () => clearTimeout(timer);
  }, [notice]);

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex justify-end px-4 pt-3">
        <button
          type="button"
          onClick={onLang}
          aria-label={t("language", lang)}
          className="min-h-11 rounded-full border border-line bg-surface px-4 text-sm font-medium"
        >
          EN · हिं
        </button>
      </div>
      <div className="relative flex flex-1 flex-col items-center justify-center gap-4">
        <div className="absolute top-1/2 size-72 -translate-y-1/2 rounded-full bg-brand-subtle" aria-hidden="true" />
        <div className="relative" aria-live="polite">
          <Bubble>
            <p className="text-xl font-semibold">{t(notice ?? "whatNeedsFixing", lang)}</p>
          </Bubble>
        </div>
        <Fixy mood="wave" size={190} className="relative" />
      </div>
      <div className="flex items-start justify-center gap-8 pb-14">
        <RoundAction
          icon="mic"
          label={t("talk", lang)}
          onClick={() => (speechSupported() ? onTalk() : setNotice("voiceUnsupported"))}
        />
        <RoundAction icon="camera" label={t("scan", lang)} big onClick={() => fileRef.current?.click()} />
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) onPhoto(file);
          }}
        />
        <RoundAction icon="keyboard" label={t("type", lang)} onClick={onType} />
      </div>
    </div>
  );
}
