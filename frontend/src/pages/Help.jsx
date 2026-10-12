import { useState } from "react";
import { PageHead } from "@/components/common";
import HelpTip from "@/components/HelpTip";

const guides = [
  { title: "First launch and database", steps: ["Install MongoDB Community Server and start its Windows service on port 27017.", "Launch SentinelLab and check the service indicators on the login screen.", "On a fresh database, create the first administrator account. Existing installations use the saved administrator credentials."] },
  { title: "Sign in safely", steps: ["Select Administrator Login for admin or super-admin accounts.", "Select Non-Admin Login for analyst and other non-administrator accounts.", "A mismatched role is rejected by the server even if the password is correct."] },
  { title: "Manage users and permissions", steps: ["Sign in as an administrator.", "Open Settings → Security to create analysts and review user roles.", "Super administrators can reset other users' passwords, disable accounts, and unlock login incidents.", "Review Production access requests carefully; independent approval may be required."] },
  { title: "Monitor and investigate", steps: ["Open Overview to review workspace activity.", "Use Sources & Ingestion to inspect event sources and incoming data.", "Use Events Explorer and Alerts to triage suspicious activity.", "Use Investigations, Detection Rules, and Reports for follow-up work."] },
  { title: "Close and upgrade safely", steps: ["Use the window close button and confirm shutdown.", "Wait for the SentinelLab API process to exit before installing a new version.", "MongoDB runs independently and remains active after SentinelLab closes."] },
];

export default function Help() {
  const [open, setOpen] = useState(0);
  return <div data-testid="how-to-use-page" className="max-w-4xl">
    <PageHead title="How to Use SentinelLab" desc="Quick-start guide for analysts and administrators" />
    <p className="text-[13px] mb-5" style={{ color: "var(--text-2)" }}>Select a topic for step-by-step instructions. Look for <HelpTip text="A question-mark icon explains the nearby option. Select it to read the explanation." /> beside settings and sensitive actions for contextual guidance.</p>
    <div className="space-y-3">{guides.map((guide, index) =>
      <section key={guide.title} className="card p-4">
        <button type="button" className="w-full text-left font-semibold text-[14px]" aria-expanded={open === index} onClick={() => setOpen(open === index ? -1 : index)}>{guide.title} <span className="float-right">{open === index ? "−" : "+"}</span></button>
        {open === index && <ol className="list-decimal pl-5 mt-3 space-y-2 text-[13px]" style={{ color: "var(--text-2)" }}>{guide.steps.map(step => <li key={step}>{step}</li>)}</ol>}
      </section>)}</div>
  </div>;
}
