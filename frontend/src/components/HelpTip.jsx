import { useState } from "react";
import { HelpCircle } from "lucide-react";

/** Keyboard-accessible, on-demand explanation for sensitive and unfamiliar controls. */
export default function HelpTip({ text, label = "What does this option do?" }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex align-middle ml-1.5">
      <button type="button" aria-label={label} aria-expanded={open}
        onClick={() => setOpen(v => !v)} onBlur={() => setOpen(false)}
        className="inline-flex items-center justify-center rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400"
        style={{ color: "var(--cyan)" }} title={label}>
        <HelpCircle size={14} />
      </button>
      {open && <span role="tooltip" className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 max-w-[80vw] rounded-md border p-3 text-left text-[12px] normal-case font-normal shadow-lg"
        style={{ background: "var(--surface, #20242a)", color: "var(--text)", borderColor: "var(--border, #3a4149)" }}>{text}</span>}
    </span>
  );
}
