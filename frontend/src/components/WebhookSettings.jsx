import { useEffect, useState } from "react";
import client from "@/lib/api";
import { toast } from "sonner";
import HelpTip from "@/components/HelpTip";

const TYPES = [
  ["critical_alert", "Critical alerts"],
  ["alert", "Other alerts"],
  ["investigation", "Investigations"],
  ["ingestion", "Ingestion"],
  ["security", "Account security"],
  ["system", "System notices"]
];
const INITIAL = { name: "", provider: "discord", url: "", events: ["critical_alert", "alert"], enabled: true };

export default function WebhookSettings() {
  const [hooks, setHooks] = useState([]);
  const [form, setForm] = useState(INITIAL);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState("");
  const load = () => client.get("/admin/webhooks").then(({ data }) => setHooks(data.webhooks)).catch(() => toast.error("Could not load webhooks"));
  useEffect(() => { load(); }, []);
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await client.post("/admin/webhooks", form);
      toast.success("Webhook saved. Use Send test to verify delivery.");
      setForm(INITIAL);
      await load();
    } catch (error) { toast.error(error.response?.data?.detail || "Could not save webhook"); }
    finally { setBusy(false); }
  };
  const update = async (hook, patch) => {
    try { await client.patch(`/admin/webhooks/${hook.id}`, patch); await load(); }
    catch (error) { toast.error(error.response?.data?.detail || "Update failed"); }
  };
  const remove = async (hook) => {
    if (!window.confirm(`Delete webhook "${hook.name}"? It will stop receiving notifications.`)) return;
    try { await client.delete(`/admin/webhooks/${hook.id}`); await load(); toast.success("Webhook deleted"); }
    catch (error) { toast.error(error.response?.data?.detail || "Delete failed"); }
  };
  const test = async (hook) => {
    setTesting(hook.id);
    try {
      const { data } = await client.post(`/admin/webhooks/${hook.id}/test`);
      if (data.status === "delivered") toast.success("Test message sent successfully");
      else toast.error("Delivery failed. Check the destination and webhook URL.");
      await load();
    } catch (error) { toast.error(error.response?.data?.detail || "Test failed"); }
    finally { setTesting(""); }
  };
  return <section className="space-y-5 mt-6" data-testid="webhook-settings">
    <div><h2 className="text-[15px] font-semibold flex items-center">Outgoing webhooks <HelpTip text="Webhooks automatically send selected SentinelLab notifications to an external app. Use a separate URL for each channel or destination." /></h2>
      <p className="text-[12px] mt-1" style={{color:"var(--text-3)"}}>Send SOC notifications to Discord, Slack, Microsoft Teams Workflows, or any compatible public HTTPS JSON endpoint. Only administrators can configure them. Webhook URLs are encrypted and never displayed after saving.</p></div>
    <form onSubmit={save} className="border rounded-md p-4 space-y-3">
      <h3 className="font-semibold text-[13px]">Add a destination</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <label className="text-[12px]">Destination name<input className="inp mt-1 w-full" required maxLength={80} placeholder="SOC alerts channel" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label>
        <label className="text-[12px]">Provider<select className="inp mt-1 w-full" value={form.provider} onChange={e=>setForm({...form,provider:e.target.value})}>
          <option value="discord">Discord</option><option value="slack">Slack</option><option value="teams">Microsoft Teams (Workflows)</option><option value="generic">Generic HTTPS JSON</option>
        </select></label>
      </div>
      <label className="text-[12px] block">Webhook URL <HelpTip text="Create an incoming webhook in the destination service, copy its HTTPS URL, and paste it here. Treat this URL like a password." />
        <input className="inp mt-1 w-full" type="password" autoComplete="off" required placeholder="https://…" value={form.url} onChange={e=>setForm({...form,url:e.target.value})}/>
      </label>
      <div><div className="text-[12px] font-semibold mb-2">Send notifications for <HelpTip text="Choose which types of events this destination should receive. Different channels can subscribe to different event types." /></div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">{TYPES.map(([id,label])=><label key={id} className="text-[12px] flex items-center gap-2"><input type="checkbox" checked={form.events.includes(id)} onChange={e=>setForm({...form,events:e.target.checked?[...form.events,id]:form.events.filter(v=>v!==id)})}/>{label}</label>)}</div>
      </div>
      <button className="btn btn-primary btn-sm" disabled={busy || !form.events.length}>{busy?"Saving…":"Save webhook"}</button>
    </form>
    <div className="space-y-2"><h3 className="font-semibold text-[13px]">Saved destinations ({hooks.length})</h3>
      {!hooks.length && <p className="text-[12px]" style={{color:"var(--text-3)"}}>No webhooks yet. Add one above to begin.</p>}
      {hooks.map(hook=><div key={hook.id} className="border rounded-md p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0"><div className="text-[13px] font-semibold">{hook.name} <span className="font-normal opacity-70">· {hook.provider}</span></div>
          <div className="text-[11px] opacity-70">{hook.events.join(", ")} · {hook.enabled?"Enabled":"Paused"} · Last: {hook.last_status || "Never sent"}</div></div>
        <div className="flex flex-wrap gap-2"><button className="btn btn-sm" disabled={testing===hook.id} onClick={()=>test(hook)}>{testing===hook.id?"Sending…":"Send test"}</button>
          <button className="btn btn-sm" onClick={()=>update(hook,{enabled:!hook.enabled})}>{hook.enabled?"Pause":"Enable"}</button>
          <button className="btn btn-sm" onClick={()=>remove(hook)}>Delete</button></div>
      </div>)}
    </div>
    <p className="text-[11px]" style={{color:"var(--text-3)"}}>Initial notification wiring covers alerts and built-in SOC notifications. Other categories are being connected module by module. Use Send test to confirm each destination before relying on it for security response.</p>
  </section>;
}
