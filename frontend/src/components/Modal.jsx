import { X } from "lucide-react";

export default function Modal({ open, onClose, title, children, wide, testId }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 overflow-auto"
      style={{ background: "rgba(0,0,0,.6)" }} onMouseDown={onClose} data-testid={testId}>
      <div className={`card fade-in my-8 ${wide ? "w-[900px]" : "w-[540px]"} max-w-full`}
        onMouseDown={(e) => e.stopPropagation()}>
        <div className="h-12 flex items-center justify-between px-4 border-b">
          <div className="font-head font-semibold text-[15px]" style={{ color: "var(--text)" }}>{title}</div>
          <button onClick={onClose} style={{ color: "var(--text-3)" }} data-testid="modal-close"><X size={18} /></button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}
