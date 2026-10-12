import { useEffect, useState } from "react";
import client from "@/lib/api";
import { toast } from "sonner";

export default function AIModelSettings() {
  const [presets,setPresets]=useState({});
  const [form,setForm]=useState({provider:"ollama",base_url:"http://127.0.0.1:11434/v1",model:"",api_key:"",enabled:true});
  const [busy,setBusy]=useState(false);
  const [status,setStatus]=useState("");
  useEffect(()=>{client.get("/admin/ai-config").then(({data})=>{
    setPresets(data.presets||{});
    if(data.config)setForm({...data.config,api_key:""});
  }).catch(()=>toast.error("Unable to load AI configuration"));},[]);
  const save=async e=>{e.preventDefault();setBusy(true);try{
    await client.put("/admin/ai-config",form);
    toast.success("AI model settings saved");setForm(p=>({...p,api_key:""}));setStatus("Saved. Send a test request to confirm the model works.");
  }catch(err){toast.error(err.response?.data?.detail||"Unable to save AI settings");}finally{setBusy(false);}};
  const test=async()=>{setBusy(true);setStatus("Contacting model…");try{
    const {data}=await client.post("/admin/ai-config/test");setStatus(data.answer||"AI connected");
  }catch(err){setStatus(err.response?.data?.detail||"AI connection failed");}finally{setBusy(false);}};
  return <section className="border rounded-md p-4 space-y-3 mt-5" data-testid="ai-model-settings">
    <h3 className="text-[14px] font-semibold">AI Models — Local & Online</h3>
    <p className="text-[12px] opacity-70">Connect Ollama or LM Studio on this PC, or an online OpenAI-compatible provider. AI helps explain alerts and events; it never performs response actions automatically.</p>
    <form onSubmit={save} className="space-y-3">
      <label className="text-[12px] block">Provider
        <select className="inp w-full mt-1" value={form.provider} onChange={e=>setForm(p=>({...p,provider:e.target.value,base_url:presets[e.target.value]||"",api_key:""}))}>
          {Object.keys(presets).map(name=><option key={name} value={name}>{({lmstudio:"LM Studio",openrouter:"OpenRouter",ollama:"Ollama",openai:"OpenAI",groq:"Groq",together:"Together AI",mistral:"Mistral",deepseek:"DeepSeek",fireworks:"Fireworks AI",custom:"Custom OpenAI-compatible"})[name]||name}</option>)}
        </select>
      </label>
      <label className="text-[12px] block">Base URL
        <input className="inp w-full mt-1" required value={form.base_url} placeholder="https://provider.example/v1" onChange={e=>setForm(p=>({...p,base_url:e.target.value}))}/>
      </label>
      <label className="text-[12px] block">Model identifier
        <input className="inp w-full mt-1" required placeholder="Enter the exact model ID available on your server" value={form.model} onChange={e=>setForm(p=>({...p,model:e.target.value}))}/>
      </label>
      <label className="text-[12px] block">API key {form.provider==="ollama"||form.provider==="lmstudio"?"(usually not needed)":"(required for cloud providers)"}
        <input className="inp w-full mt-1" type="password" autoComplete="off" placeholder="Leave blank to keep an existing key" value={form.api_key} onChange={e=>setForm(p=>({...p,api_key:e.target.value}))}/>
      </label>
      <label className="text-[12px] flex items-center gap-2"><input type="checkbox" checked={form.enabled} onChange={e=>setForm(p=>({...p,enabled:e.target.checked}))}/> Enable AI assistant</label>
      <div className="flex gap-2"><button className="btn btn-primary btn-sm" disabled={busy}>Save AI configuration</button><button type="button" className="btn btn-sm" disabled={busy} onClick={test}>Test connection</button></div>
    </form>
    {status&&<p className="text-[12px]" role="status">{status}</p>}
    <p className="text-[11px] opacity-70">Local endpoints use this Windows PC's loopback address. For remote AI servers, use a secure HTTPS OpenAI-compatible endpoint. Credentials are encrypted in MongoDB and never returned by the API.</p>
  </section>;
}
