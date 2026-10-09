import { useState, useRef, useEffect } from "react";
import { Bot, X, Send, Sparkles } from "lucide-react";
import client, { apiErr } from "@/lib/api";

export default function AIAssistant() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([{ role: "ai", text: "Hi — I'm the SentinelLab assistant. Ask me to explain an alert, summarize an investigation, or suggest a hunt query. I only use data from your workspace." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef();

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const send = async () => {
    if (!input.trim() || busy) return;
    const q = input.trim();
    setMsgs((m) => [...m, { role: "me", text: q }]);
    setInput(""); setBusy(true);
    try {
      const { data } = await client.post("/ai/ask", { message: q });
      setMsgs((m) => [...m, { role: "ai", text: data.answer, unconfigured: !data.configured }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "ai", text: apiErr(e) }]);
    } finally { setBusy(false); }
  };

  return (
    <>
      <button className="fixed bottom-5 right-5 z-40 grid place-items-center w-12 h-12 rounded-full shadow-lg"
        style={{ background: "var(--cyan)", color: "#04161c" }} onClick={() => setOpen(!open)} data-testid="ai-toggle">
        {open ? <X size={20} /> : <Bot size={20} />}
      </button>
      {open && (
        <div className="fixed bottom-20 right-5 z-40 card flex flex-col w-96 max-w-[92vw] fade-in" style={{ height: 480 }} data-testid="ai-panel">
          <div className="h-11 flex items-center gap-2 px-3 border-b">
            <Sparkles size={15} style={{ color: "var(--cyan)" }} />
            <span className="font-head font-semibold text-[14px]" style={{ color: "var(--text)" }}>AI Security Assistant</span>
          </div>
          <div className="flex-1 overflow-auto p-3 space-y-3">
            {msgs.map((m, i) => (
              <div key={i} className={`text-[12.5px] ${m.role === "me" ? "text-right" : ""}`}>
                <div className="inline-block px-3 py-2 rounded-lg max-w-[85%] whitespace-pre-wrap text-left"
                  style={{ background: m.role === "me" ? "var(--cyan)" : "var(--surface)", color: m.role === "me" ? "#04161c" : "var(--text-2)", border: m.role === "me" ? "none" : "1px solid var(--border)" }}>
                  {m.text}
                </div>
              </div>
            ))}
            {busy && <div className="text-[12px]" style={{ color: "var(--text-3)" }}>Thinking…</div>}
            <div ref={endRef} />
          </div>
          <div className="p-2.5 border-t flex gap-2">
            <input className="inp" placeholder="Ask about security data…" value={input}
              onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} data-testid="ai-input" />
            <button className="btn btn-primary" onClick={send} disabled={busy} data-testid="ai-send"><Send size={14} /></button>
          </div>
        </div>
      )}
    </>
  );
}
