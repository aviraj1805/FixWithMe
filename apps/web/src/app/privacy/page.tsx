import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Privacy & terms · Fix with Me" };

const SECTIONS: { title: string; body: string[] }[] = [
  {
    title: "Who can use it",
    body: [
      "Fix with Me is for adults (18+). It gives general repair guidance, not professional advice. You use it at your own risk.",
      "For anything involving mains wiring, gas, refrigerant, swollen batteries or smoke, stop and call a professional or 112.",
    ],
  },
  {
    title: "What we send to AI services",
    body: [
      "Your typed or spoken text and any photo you take are sent to Google's Gemini API to understand the problem. Google may use free-tier inputs to improve its products, and people at Google may review them. Don't include personal details, faces or documents.",
      "We remove phone numbers, email addresses and links from text before sending it. Photos are shrunk and their location data is removed on your phone first.",
      "Voice input uses your browser's speech recognition. In Chrome, audio is processed by Google. You can always type instead.",
    ],
  },
  {
    title: "What we store",
    body: [
      "No accounts, no names, no photos. If you tap \"Did it work?\", we store an anonymous record (item, likely cause, your yes/no answers, language) to improve the repair guides.",
      "Our servers keep short-lived request logs and a per-IP request counter to stop abuse.",
    ],
  },
  {
    title: "Answers and sources",
    body: [
      "Answers come from our curated guides, Wikipedia (CC BY-SA) and, for items we don't cover yet, web search results. Each answer shows its sources and whether it was checked. AI suggestions can be wrong. Check before you act.",
      "Shopping links open a search on the store's own site. We earn nothing from them and don't rank products.",
    ],
  },
  {
    title: "Contact",
    body: ["Questions or a request to remove data: open an issue at github.com/aviraj1805/FixWithMe."],
  },
];

export default function Privacy() {
  return (
    <main className="mx-auto w-full max-w-md space-y-6 px-6 py-8">
      <Link href="/" className="text-sm text-muted underline">
        ← Fix with Me
      </Link>
      <h1 className="text-2xl font-bold">Privacy &amp; terms</h1>
      <p className="text-sm text-muted">Last updated 24 October 2026.</p>
      {SECTIONS.map((s) => (
        <section key={s.title} className="space-y-2">
          <h2 className="text-lg font-semibold">{s.title}</h2>
          {s.body.map((p) => (
            <p key={p} className="text-[15px] leading-relaxed">
              {p}
            </p>
          ))}
        </section>
      ))}
    </main>
  );
}
