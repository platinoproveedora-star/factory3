import clsx from "clsx";

const tones: Record<string, string> = {
  draft: "border-slate-700 bg-slate-900/40 text-slate-300",
  ready_to_quote: "border-blue-800 bg-blue-900/30 text-blue-300",
  supplier_quoting: "border-yellow-800 bg-yellow-900/30 text-yellow-300",
  quoted: "border-green-800 bg-green-900/30 text-green-300",
  ready_to_send: "border-blue-800 bg-blue-900/30 text-blue-300",
  sent_manual: "border-yellow-800 bg-yellow-900/30 text-yellow-300",
  response_received: "border-green-800 bg-green-900/30 text-green-300",
  processed: "border-green-800 bg-green-900/30 text-green-300",
  pending: "border-yellow-800 bg-yellow-900/30 text-yellow-300",
  active: "border-green-800 bg-green-900/30 text-green-300",
  cancelled: "border-red-800 bg-red-900/30 text-red-300",
};

export default function StatusBadge({ value }: { value?: string | null }) {
  const text = value || "pending";
  return (
    <span className={clsx("inline-flex rounded-full border px-2 py-0.5 text-xs", tones[text] || tones.pending)}>
      {text.replaceAll("_", " ")}
    </span>
  );
}
