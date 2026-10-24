import { ApiStatus } from "@/components/api-status";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center gap-6 px-6 py-24">
      <p className="text-sm font-medium tracking-wide text-primary">Fix with Me</p>
      <h1 className="text-3xl font-semibold tracking-tight">
        Repair guidance you can trust is on its way.
      </h1>
      <p className="text-muted">
        We&apos;re building an assistant that helps Indian households fix everyday items safely,
        and tells you plainly when to call a professional.
      </p>
      <ApiStatus />
    </main>
  );
}
