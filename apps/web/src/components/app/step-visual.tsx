import { Icon, type IconName } from "@/components/ui/icons";

// Keyword → picture for a guide step (English and Hindi). The first match is the main picture.
const RULES: [RegExp, IconName][] = [
  [/\b(mcb|switch off|power off|turn off|unplug)\b|बंद|प्लग/i, "power"],
  [/\b(plug|socket|charger|wall)\b|सॉकेट|चार्जर/i, "plug"],
  [/\b(ladder|climb|canopy)\b|सीढ़ी/i, "ladder"],
  [/\b(photo|photograph|camera)\b|फ़ोटो|फोटो|कैमरा/i, "camera"],
  [/\b(discharge|terminal|screw|screwdriver|tighten|connect)\b|पेचकस|टर्मिनल/i, "wrench"],
  [/\b(clean|wipe|swab|scrub|alcohol|vinegar|brush|lint|dust)\b|साफ|पोंछ/i, "sparkles"],
  [/\b(batter|cell)\w*|बैटरी|सेल/i, "battery"],
  [/\b(phone|bluetooth|pair|settings)\b|फ़ोन|फोन|ब्लूटूथ/i, "smartphone"],
  [/\b(regulator|turn the|rotate|speed)\b|रेगुलेटर|घुमा/i, "rotate"],
  [/\b(wait|minute|seconds|hours|dry)\b|मिनट|घंटे|सूख/i, "clock"],
  [/\b(water|liquid|leak|drip)\b|पानी/i, "droplet"],
  [/\b(check|test|try|look|inspect|find|shine)\b|जांच|देख/i, "search"],
];

export function stepIcons(text: string): IconName[] {
  const found = RULES.filter(([re]) => re.test(text)).map(([, icon]) => icon);
  return [...new Set(found)].slice(0, 3).concat(found.length ? [] : ["wrench"]);
}

/** A clear picture for each step: the main action large, up to two supporting actions small. */
export function StepVisual({ text, n, caution }: { text: string; n: number; caution: boolean }) {
  const [main, ...rest] = stepIcons(text);
  return (
    <div
      className={`relative grid h-52 place-items-center rounded-3xl ${
        caution ? "bg-[var(--color-status-caution-bg)]" : "bg-brand-subtle"
      }`}
      aria-hidden="true"
    >
      <span className="absolute left-4 top-4 grid size-10 place-items-center rounded-full bg-brand text-lg font-bold text-on-brand">
        {n}
      </span>
      <div className="flex items-center gap-5 text-brand">
        <span className="grid size-28 place-items-center rounded-full bg-surface shadow-soft">
          <Icon name={main} size={60} />
        </span>
        {rest.length > 0 && (
          <div className="flex flex-col gap-3">
            {rest.map((icon) => (
              <span key={icon} className="grid size-14 place-items-center rounded-full bg-surface shadow-soft">
                <Icon name={icon} size={28} />
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
