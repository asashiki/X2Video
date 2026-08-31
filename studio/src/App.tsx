import {
  Activity,
  ArrowDown,
  ArrowUp,
  BookOpen,
  Bot,
  Check,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  Clock3,
  FileDiff,
  Film,
  LayoutDashboard,
  MemoryStick,
  Menu,
  Moon,
  OctagonX,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sun,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "./api";
import type { Decision, EvidencePack, JsonObject, RunEvent, RunRow, Snapshot, TaskRow } from "./types";

const navItems = [
  ["/", "总览", LayoutDashboard],
  ["/new", "新建", Plus],
  ["/memory", "记忆", MemoryStick],
  ["/settings", "设置", Settings],
] as const;

function stateTone(state: string) {
  if (["COMPLETE", "succeeded"].includes(state)) return "success";
  if (["FAILED", "error", "blocker", "failed"].includes(state)) return "danger";
  if (state.includes("WAIT") || state.includes("warning") || state === "waiting_human") return "warning";
  if (["CANCELED", "canceled", "pending"].includes(state)) return "muted";
  return "running";
}

function statusLabel(value: string) {
  return ({
    COMPLETE: "完成", FAILED: "失败", PLAN: "未开始", CANCELED: "已取消",
    succeeded: "完成", failed: "失败", pending: "等待", running: "进行中",
    skipped: "跳过", paused: "暂停", warning: "注意",
  } as Record<string, string>)[value] || value.replaceAll("_", " ");
}

function taskTitle(task: TaskRow) {
  return ({
    legacy_fetch: "抓帖", legacy_curate: "选题", legacy_card: "做卡片",
    legacy_script: "写口播", legacy_render: "合成视频",
    discover: "抓帖", research: "核材料", curate: "选题", script: "写口播",
    produce: "合成视频",
  } as Record<string, string>)[task.task_type] || task.task_type.replaceAll("_", " ");
}

function Status({ value }: { value: string }) {
  return <span className={`status status--${stateTone(value)}`}><i />{statusLabel(value)}</span>;
}

function Shell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    window.localStorage.getItem("x2video-theme") === "dark" ? "dark" : "light",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem("x2video-theme", theme);
  }, [theme]);
  return (
    <div className="shell">
      <aside className={`rail ${open ? "rail--open" : ""}`}>
        <div className="brand"><span className="brand__mark">X2</span><span><strong>X2Video</strong><small>Agent Studio</small></span></div>
        <nav aria-label="主要导航">
          {navItems.map(([to, label, Icon]) => <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)}><Icon size={18}/><span>{label}</span></NavLink>)}
        </nav>
      </aside>
      <div className="shell__body">
        <header className="topbar">
          <button className="icon-button mobile-only" aria-label="打开导航" onClick={() => setOpen(!open)}><Menu size={19}/></button>
          <div className="topbar__spacer" />
          <div className="topbar__right">
            <button className="theme-toggle" aria-label={`切换到${theme === "light" ? "深色" : "浅色"}模式`} onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
              {theme === "light" ? <Moon size={16}/> : <Sun size={16}/>}<span>{theme === "light" ? "深色" : "浅色"}</span>
            </button>
            <Link className="primary-button primary-button--small" to="/new"><Plus size={16}/>新建 Run</Link>
          </div>
        </header>
        <main>{children}</main>
      </div>
      {open && <button className="scrim" aria-label="关闭导航" onClick={() => setOpen(false)}/>} 
    </div>
  );
}

function PageHeader({ title, action }: { eyebrow?: string; title: string; detail?: string; action?: React.ReactNode }) {
  return <div className="page-header"><h1>{title}</h1>{action && <div className="page-header__actions">{action}</div>}</div>;
}

function useRuns() {
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(() => api.runs().then(r => setRuns(r.items)).catch(e => setError(String(e))), []);
  useEffect(() => { void load(); const timer = window.setInterval(load, 2500); return () => clearInterval(timer); }, [load]);
  return { runs, error, load };
}

function Dashboard() {
  const { runs, error } = useRuns();
  const active = runs.filter(r => !["COMPLETE", "FAILED", "CANCELED", "PLAN"].includes(r.state) && !r.state.includes("WAIT"));
  const completed = runs.filter(r => r.state === "COMPLETE");
  const gates = runs.filter(r => r.state.includes("WAIT"));
  return <div className="page dashboard">
    <PageHeader title="今天的生产台" action={<Link className="primary-button" to="/new"><Plus size={16}/>新建</Link>}/>
    {error && <div className="notice notice--error"><CircleAlert size={17}/>{error}</div>}
    <section className="attention-strip">
      <div><span>等待决策</span><strong>{gates.length}</strong></div>
      <div><span>运行中</span><strong>{active.length}</strong></div>
      <div><span>已完成</span><strong>{completed.length}</strong></div>
      <div><span>完成率</span><strong>{runs.length ? Math.round(completed.length / runs.length * 100) : 0}%</strong></div>
    </section>
    <div className="dashboard-grid">
      <section className="work-panel work-panel--runs">
        <div className="section-heading"><div><h2>最近</h2></div></div>
        {runs.length === 0 ? <EmptyState title="还没有 Run" detail="新建一条，抓热点做成片。"/> : <div className="run-table">
          <div className="run-table__head"><span>Run / Goal</span><span>状态</span><span>自治</span><span>更新时间</span><span/></div>
          {runs.map(run => <Link className="run-row" key={run.run_id} to={`/runs/${run.run_id}`}><div><code>{run.run_id.slice(0, 16)}</code><strong>{run.summary || "等待 Planner"}</strong></div><Status value={run.is_paused ? "paused" : run.state}/><span className="mono">{run.autonomy}</span><time>{relativeTime(run.updated_at)}</time><ChevronRight size={17}/></Link>)}
        </div>}
      </section>
      <aside className="work-panel gates-panel">
        <div className="section-heading"><div><h2>待处理</h2></div></div>
        {gates.length ? gates.map(run => <Link className="gate-item" key={run.run_id} to={`/runs/${run.run_id}`}><span className="gate-item__icon"><Pause size={16}/></span><div><strong>{run.state === "WAIT_GATE_1" ? "选题组合待确认" : "成片审查待确认"}</strong><small>{run.run_id.slice(0, 14)} · {run.format}</small></div><ChevronRight size={16}/></Link>) : <div className="quiet-state"><CircleCheck size={24}/><strong>没有阻塞中的 Gate</strong><span>新问题会出现在这里。</span></div>}
      </aside>
    </div>
  </div>;
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><Bot size={28}/><strong>{title}</strong><p>{detail}</p><Link to="/new">新建 <ChevronRight size={15}/></Link></div>;
}

function NewRun() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("帮我做一条今日 AI 科技圈热点速览，中文口播，抓最近的外文热帖。");
  const [autonomy, setAutonomy] = useState("auto");
  const [duration, setDuration] = useState(60);
  const [format, setFormat] = useState("news_recap");
  const [busy, setBusy] = useState(false);
  const [liveReady, setLiveReady] = useState(false);
  useEffect(() => { void api.health().then(h => {
    setLiveReady(Boolean(h.live_ready));
    if (!h.live_ready) setAutonomy("auto");
  }).catch(() => setLiveReady(false)); }, []);
  const submit = async () => {
    setBusy(true);
    try {
      const snapshot = await api.createRun({
        query,
        autonomy,
        target_duration_seconds: duration,
        preferred_format: format || null,
        mode: liveReady ? "live" : "demo",
      });
      await api.start(snapshot.run.run_id, true);
      navigate(`/runs/${snapshot.run.run_id}`);
    } finally { setBusy(false); }
  };
  return <div className="page composer-page">
    <PageHeader title="做成片"/>
    <div className="composer">
      <section className="composer__intent"><label htmlFor="goal">想做什么</label><textarea id="goal" value={query} onChange={e => setQuery(e.target.value)} /></section>
      <aside className="composer__constraints">
        <label>时长<div className="range-row"><input type="range" min="30" max="180" step="15" value={duration} onChange={e => setDuration(Number(e.target.value))}/><output>{duration}s</output></div></label>
        <button className="primary-button primary-button--wide" onClick={submit} disabled={!query.trim() || busy}>{busy ? <RefreshCw className="spin" size={17}/> : <Play size={17}/>}做成片</button>
      </aside>
    </div>
  </div>;
}

const views = [["timeline", "进度", Activity], ["curation", "选题", BookOpen], ["script", "口播", FileDiff], ["qc", "成片", ShieldCheck]] as const;

function RunWorkspace() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const view = params.get("view") || "timeline";
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const load = useCallback(() => api.run(id).then(setSnapshot).catch(e => setError(String(e))), [id]);
  useEffect(() => { void load(); const timer = window.setInterval(load, 1000); return () => clearInterval(timer); }, [load]);
  const action = async (name: string, payload: Record<string, unknown> = {}) => { setBusy(name); try { const next = await api.action(id, name, payload); setSnapshot(next); if (name === "fork") { navigate(`/runs/${next.run.run_id}`); return; } if (name === "resume" || name === "approve_gate" || name === "retry") await api.start(id, true); } catch (e) { setError(String(e)); } finally { setBusy(""); } };
  if (!snapshot) return <div className="page loading-state"><RefreshCw className="spin"/>载入 Run…</div>;
  const run = snapshot.run;
  const spent = run.spent as Record<string, number>;
  return <div className="run-workspace">
    <div className="run-controlbar">
      <div className="run-title"><Link to="/">Runs</Link><ChevronRight size={14}/><code>{run.run_id}</code><Status value={run.is_paused ? "paused" : run.state}/></div>
      <div className="run-stats"><span><Clock3 size={14}/>{spent.runtime_seconds ?? 0}s</span></div>
      <div className="run-actions">
        {run.state === "FAILED" && <button onClick={() => action("retry")}><RefreshCw size={15}/>重试</button>}
        {run.state.includes("WAIT") && <button className="approve-button" onClick={() => action("approve_gate", { summary: "通过" })}><Check size={15}/>通过</button>}
        {!["COMPLETE", "FAILED", "CANCELED"].includes(run.state) && <button className="danger-ghost" onClick={() => action("cancel")}><OctagonX size={15}/>取消</button>}
      </div>
    </div>
    {(error || (run.state === "FAILED" && run.error)) && <div className="notice notice--error"><CircleAlert size={16}/>{error || run.error}<button onClick={() => setError("")}><X size={14}/></button></div>}
    <div className="workspace-tabs" role="tablist">{views.map(([key, label, Icon]) => <button key={key} className={view === key ? "active" : ""} onClick={() => setParams({ view: key })}><Icon size={16}/>{label}</button>)}</div>
    <div className="workspace-content">
      {view === "timeline" && <Timeline snapshot={snapshot}/>} 
      {view === "curation" && <Curation snapshot={snapshot} action={action}/>} 
      {view === "script" && <ScriptView snapshot={snapshot}/>} 
      {view === "qc" && <QCLab snapshot={snapshot}/>} 
    </div>
    {busy && <div className="action-toast"><RefreshCw className="spin" size={15}/>{busy.replaceAll("_", " ")}</div>}
  </div>;
}

function Timeline({ snapshot }: { snapshot: Snapshot }) {
  const eventsByTask = useMemo(() => new Map(snapshot.events.filter(e => e.status).map(e => [e.state, e])), [snapshot.events]);
  return <div className="timeline-layout">
    <section className="timeline-panel">
      <div className="section-heading"><div><h2>进度</h2></div></div>
      <div className="timeline-list">{snapshot.tasks.map((task, index) => <TaskItem key={task.task_id} task={task} event={eventsByTask.get(task.target_state)} index={index}/>)}</div>
    </section>
    <aside className="inspector">
      <h2>这条要做什么</h2>
      <p className="inspector__summary">{snapshot.goal.query}</p>
    </aside>
  </div>;
}

function TaskItem({ task, event, index }: { task: TaskRow; event?: RunEvent; index: number }) {
  return <article className={`task-item task-item--${stateTone(task.status)}`}><div className="task-spine"><span>{task.status === "succeeded" || task.status === "skipped" ? <Check size={14}/> : index + 1}</span></div><div className="task-main"><div className="task-main__top"><div><strong>{taskTitle(task)}</strong></div><Status value={task.status}/></div><p>{task.error || event?.summary || (task.status === "pending" ? "还没轮到" : "")}</p></div></article>;
}

function Curation({ snapshot, action }: { snapshot: Snapshot; action: (name: string, payload?: Record<string, unknown>) => Promise<void> }) {
  const ordered = [...snapshot.decisions].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));
  const [selected, setSelected] = useState(ordered[0]?.candidate_id ?? "");
  const current = snapshot.evidence.find(e => e.candidate_id === selected);
  const move = (decision: Decision, delta: number) => { const picks = ordered.filter(d => d.selected); const index = picks.findIndex(d => d.candidate_id === decision.candidate_id); const target = index + delta; if (target < 0 || target >= picks.length) return; [picks[index], picks[target]] = [picks[target], picks[index]]; void action("reorder", { candidate_ids: picks.map(d => d.candidate_id) }); };
  return <div className="curation-layout">
    <section className="candidate-queue"><div className="section-heading"><div><h2>选题</h2></div><span className="queue-count">留 {ordered.filter(d => d.selected).length} 条</span></div>
      <div className="candidate-list">{ordered.map(decision => <button key={decision.candidate_id} className={`candidate-row ${selected === decision.candidate_id ? "active" : ""} ${decision.selected ? "picked" : "rejected"}`} onClick={() => setSelected(decision.candidate_id)}><span className="rank">{decision.rank ? String(decision.rank).padStart(2,"0") : "—"}</span><div className="candidate-copy"><strong>{decision.decision_summary}</strong></div><div className="candidate-actions">{decision.selected && <><span onClick={e => {e.stopPropagation(); move(decision,-1);}}><ArrowUp size={14}/></span><span onClick={e => {e.stopPropagation(); move(decision,1);}}><ArrowDown size={14}/></span></>}<span className={`pick-indicator ${decision.selected ? "on" : ""}`}>{decision.selected ? <Check size={14}/> : <X size={14}/>}</span></div></button>)}</div>
    </section>
    <EvidenceInspector pack={current} decision={ordered.find(d => d.candidate_id === selected)} action={action}/>
  </div>;
}

function EvidenceInspector({ pack, decision, action }: { pack?: EvidencePack; decision?: Decision; action: (name: string, payload?: Record<string, unknown>) => Promise<void> }) {
  if (!pack || !decision) return <aside className="inspector"><div className="quiet-state">点左边一条看原文</div></aside>;
  return <aside className="inspector evidence-inspector"><h2>原文</h2>
    <div className="claim-list">{pack.claims.map(claim => <div key={claim.claim_id}><p>{claim.normalized_claim}</p></div>)}</div>
    {pack.sources.map(source => <a className="source-block" key={source.source_id} href={source.url} target="_blank" rel="noreferrer"><strong>{source.title}</strong><p>{source.excerpt}</p></a>)}
    <div className="inspector-actions"><button onClick={() => action(decision.selected ? "reject_candidate" : "approve_candidate", {candidate_id:decision.candidate_id})}>{decision.selected ? <X size={15}/> : <Check size={15}/>} {decision.selected ? "去掉" : "留下"}</button></div>
  </aside>;
}

function ScriptView({ snapshot }: { snapshot: Snapshot }) {
  const script = snapshot.documents["script.final.json"] as JsonObject | undefined;
  const segments = (script?.segments ?? []) as Array<Record<string, unknown>>;
  return <div className="editor-layout">
    <section className="script-editor"><div className="section-heading"><div><h2>口播</h2></div></div>
      {script?.hook ? <div className="hook-block"><p>{String(script.hook)}</p></div> : null}
      <div className="segments">{segments.map((segment,index) => <article className="segment" key={String(segment.segment_id)}><div className="segment__head"><span>{String(index+1).padStart(2,"0")}</span></div><p>{String(segment.narration)}</p></article>)}</div>
    </section>
  </div>;
}

function formatClock(seconds: unknown) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value < 0) return "—";
  const mm = Math.floor(value / 60);
  const ss = (value % 60).toFixed(1).padStart(4, "0");
  return `${String(mm).padStart(2, "0")}:${ss}`;
}

function QCLab({ snapshot }: { snapshot: Snapshot }) {
  const before = snapshot.documents["publish_kit/qc.before.json"] as JsonObject | undefined;
  const after = snapshot.documents["publish_kit/qc.after.json"] as JsonObject | undefined;
  const issues = (before?.issues ?? []) as Array<Record<string, unknown>>;
  const duration = Number(before?.duration_seconds);
  const marker = Number(issues[0]?.timestamp_seconds);
  const structureOk = Boolean(snapshot.media.video);
  return <div className="qc-layout">
    <section className="viewer-panel"><div className="video-stage"><ReviewPlayer video={snapshot.media.video} cover={snapshot.media.cover}/></div><div className="playback-strip"><button><Play size={15}/></button><div className="timeline-track">{Number.isFinite(marker) && Number.isFinite(duration) && duration > 0 && <i style={{left:`${Math.min(marker / duration * 100, 100)}%`}}/>}<span style={{width: structureOk ? "100%" : "0%"}}/></div><time>{structureOk ? `${formatClock(marker || 0)} / ${formatClock(duration)}` : "—"}</time></div>
      <div className="metric-strip"><div><span>视频</span><strong>{snapshot.media.video ? "1080×1920" : "—"}</strong></div><div><span>时长</span><strong>{Number.isFinite(duration) ? `${duration}s` : "—"}</strong></div><div><span>结构检查</span><strong className={structureOk ? "good" : "warn"}>{structureOk ? "PASS" : "WAIT"}</strong></div><div><span>回归 QC</span><strong className={after?.ok ? "good" : "warn"}>{after?.ok ? "PASS" : "WAIT"}</strong></div></div>
    </section>
    <aside className="issue-panel"><div className="section-heading"><div><h2>成片</h2></div></div>{issues.map(issue => {
      const evidence = (issue.evidence as string[]) ?? [];
      const beforePx = evidence.find(item => item.startsWith("subtitle_bottom="))?.split("=")[1] ?? "1810";
      const patched = (issue.proposed_patch as Record<string, unknown> | undefined)?.subtitle_bottom ?? 1620;
      return <article className="quality-issue" key={String(issue.issue_id)}><div className="quality-issue__head"><Status value={String(issue.severity)}/><code>{String(issue.code)}</code><time>@ {String(issue.timestamp_seconds)}s</time></div><h3>{String(issue.description)}</h3><div className="evidence-code">{evidence.map(item => <span key={item}>{item}</span>)}</div><div className="repair-flow"><span className="before">{beforePx}px</span><ChevronRight size={15}/><span className="after">{String(patched)}px</span>{after?.ok ? <strong><Check size={13}/>REGRESSION PASS</strong> : <strong className="warn">WAITING</strong>}</div></article>;
    })}
    </aside>
  </div>;
}

function ReviewPlayer({video,cover}:{video?:string|null;cover?:string|null}) {
  const [playing,setPlaying]=useState(false);
  if(!video)return <div className="empty-video"><Film size={34}/>等待 Producer 输出</div>;
  if(playing)return <video autoPlay controls preload="auto" src={video}/>;
  return <button className="video-poster" aria-label="播放最终成片" onClick={()=>setPlaying(true)}>{cover&&<img src={cover} alt="最终成片封面"/>}<span><Play size={22} fill="currentColor"/>播放成片</span></button>;
}

function MemoryPage() {
  const [memories,setMemories]=useState<import("./types").MemoryCandidate[]>([]);
  const load=useCallback(()=>api.memories().then(result=>setMemories(result.items)),[]);
  useEffect(()=>{void load()},[load]);
  const decide=async(id:string,status:"approved"|"rejected")=>{await api.memoryStatus(id,status); await load();};
  return <div className="page"><PageHeader title="记忆"/><section className="work-panel">{memories.length===0?<div className="quiet-state"><strong>还没有记忆</strong></div>:<div className="memory-list">{memories.map(memory=><article className="memory-item" key={memory.memory_id}><div><Status value={memory.status}/></div><p>{memory.content}</p>{memory.status==="pending"&&<footer><button onClick={()=>decide(memory.memory_id,"rejected")}><X size={14}/>拒绝</button><button className="approve-button" onClick={()=>decide(memory.memory_id,"approved")}><Check size={14}/>留下</button></footer>}</article>)}</div>}</section></div>;
}

function SettingsPage() {
  const [health,setHealth] = useState<{ok:boolean;version:string;mode:string;live_ready?:boolean;source_provider?:string|null;auth_logged_in?:boolean;checks:Record<string,boolean>}|null>(null);
  useEffect(()=>{void api.health().then(setHealth)},[]);
  const live = Boolean(health?.live_ready);
  return <div className="page"><PageHeader title="设置"/><section className="doctor-list"><DoctorRow label="服务" detail={health?.ok ? "正常" : "检查中"} ok={Boolean(health?.ok)}/><DoctorRow label="FFmpeg" detail="做视频用" ok={Boolean(health?.checks.ffmpeg)}/><DoctorRow label="浏览器" detail="做卡片用" ok={Boolean(health?.checks.browser)}/><DoctorRow label="X 登录" detail={live ? "已登录" : "未登录"} ok={live}/></section></div>;
}

function DoctorRow({label,detail,ok}:{label:string;detail:string;ok:boolean}) { return <div className="doctor-row"><span className={`doctor-icon ${ok?"ok":"warn"}`}>{ok?<Check size={16}/>:<CircleAlert size={16}/>}</span><div><strong>{label}</strong><span>{detail}</span></div><Status value={ok?"succeeded":"warning"}/></div>; }

export function App() { return <Shell><Routes><Route path="/" element={<Dashboard/>}/><Route path="/new" element={<NewRun/>}/><Route path="/runs/:id" element={<RunWorkspace/>}/><Route path="/memory" element={<MemoryPage/>}/><Route path="/settings" element={<SettingsPage/>}/></Routes></Shell>; }

function relativeTime(value:string) { const delta=Math.max(0,Date.now()-new Date(value).getTime()); if(delta<60_000)return "刚刚"; if(delta<3_600_000)return `${Math.floor(delta/60_000)} 分钟前`; return new Date(value).toLocaleDateString("zh-CN",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}); }
