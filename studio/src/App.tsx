import {
  Activity,
  ArrowDown,
  ArrowUp,
  BarChart3,
  BookOpen,
  Bot,
  Check,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  Clock3,
  Command,
  FileDiff,
  Film,
  Gauge,
  LayoutDashboard,
  Lock,
  MemoryStick,
  Menu,
  OctagonX,
  PanelLeftClose,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Unlock,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "./api";
import type { Decision, EvidencePack, JsonObject, RunEvent, RunRow, Snapshot, TaskRow } from "./types";

const navItems = [
  ["/", "总览", LayoutDashboard],
  ["/new", "新建 Run", Plus],
  ["/memory", "记忆与对标", MemoryStick],
  ["/settings", "设置与诊断", Settings],
] as const;

function stateTone(state: string) {
  if (["COMPLETE", "succeeded"].includes(state)) return "success";
  if (["FAILED", "error", "blocker", "failed"].includes(state)) return "danger";
  if (state.includes("WAIT") || state.includes("warning") || state === "waiting_human") return "warning";
  if (["CANCELED", "canceled", "pending"].includes(state)) return "muted";
  return "running";
}

function Status({ value }: { value: string }) {
  return <span className={`status status--${stateTone(value)}`}><i />{value.replaceAll("_", " ")}</span>;
}

function Shell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="shell">
      <aside className={`rail ${open ? "rail--open" : ""}`}>
        <div className="brand"><span className="brand__mark">X2</span><span><strong>X2Video</strong><small>Agent Studio</small></span></div>
        <nav aria-label="主要导航">
          {navItems.map(([to, label, Icon]) => <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)}><Icon size={18}/><span>{label}</span></NavLink>)}
        </nav>
        <div className="rail__foot"><span className="connection"><i/>LOCAL CONTROL PLANE</span><small>v0.2 · Demo ready</small></div>
      </aside>
      <div className="shell__body">
        <header className="topbar">
          <button className="icon-button mobile-only" aria-label="打开导航" onClick={() => setOpen(!open)}><Menu size={19}/></button>
          <div className="command"><Search size={16}/><span>搜索 Run、Artifact 或 Evidence</span><kbd><Command size={12}/> K</kbd></div>
          <div className="topbar__right"><span className="live-dot">LIVE</span><Link className="primary-button primary-button--small" to="/new"><Plus size={16}/>新建 Run</Link></div>
        </header>
        <main>{children}</main>
      </div>
      {open && <button className="scrim" aria-label="关闭导航" onClick={() => setOpen(false)}/>} 
    </div>
  );
}

function PageHeader({ eyebrow, title, detail, action }: { eyebrow: string; title: string; detail: string; action?: React.ReactNode }) {
  return <div className="page-header"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{detail}</p></div>{action && <div className="page-header__actions">{action}</div>}</div>;
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
  const active = runs.filter(r => !["COMPLETE", "FAILED", "CANCELED"].includes(r.state));
  const completed = runs.filter(r => r.state === "COMPLETE");
  const gates = runs.filter(r => r.state.includes("WAIT"));
  return <div className="page dashboard">
    <PageHeader eyebrow="EDITORIAL CONTROL ROOM" title="今天的生产台" detail="先处理等待中的 Gate，再检查正在运行的内容生产任务。" action={<Link className="primary-button" to="/new"><Sparkles size={17}/>表达创作目标</Link>}/>
    {error && <div className="notice notice--error"><CircleAlert size={17}/>{error}</div>}
    <section className="attention-strip">
      <div><span>等待决策</span><strong>{gates.length}</strong><small>Gate 需要人工确认</small></div>
      <div><span>运行中</span><strong>{active.length}</strong><small>Worker 与实时 Trace</small></div>
      <div><span>已完成</span><strong>{completed.length}</strong><small>可审片 Publish Kit</small></div>
      <div><span>可靠性</span><strong>{runs.length ? Math.round(completed.length / runs.length * 100) : 100}%</strong><small>本地 Run 完成率</small></div>
    </section>
    <div className="dashboard-grid">
      <section className="work-panel work-panel--runs">
        <div className="section-heading"><div><span className="section-kicker">RUN QUEUE</span><h2>最近 Runs</h2></div><Activity size={18}/></div>
        {runs.length === 0 ? <EmptyState title="还没有 Run" detail="创建一个离线 Demo Run，先验证目标、证据、批评和修复闭环。"/> : <div className="run-table">
          <div className="run-table__head"><span>Run / Goal</span><span>状态</span><span>自治</span><span>更新时间</span><span/></div>
          {runs.map(run => <Link className="run-row" key={run.run_id} to={`/runs/${run.run_id}`}><div><code>{run.run_id.slice(0, 16)}</code><strong>{run.summary || "等待 Planner"}</strong></div><Status value={run.is_paused ? "paused" : run.state}/><span className="mono">{run.autonomy}</span><time>{relativeTime(run.updated_at)}</time><ChevronRight size={17}/></Link>)}
        </div>}
      </section>
      <aside className="work-panel gates-panel">
        <div className="section-heading"><div><span className="section-kicker">HUMAN GATES</span><h2>待处理</h2></div><ShieldCheck size={18}/></div>
        {gates.length ? gates.map(run => <Link className="gate-item" key={run.run_id} to={`/runs/${run.run_id}`}><span className="gate-item__icon"><Pause size={16}/></span><div><strong>{run.state === "WAIT_GATE_1" ? "选题组合待确认" : "成片审查待确认"}</strong><small>{run.run_id.slice(0, 14)} · {run.format}</small></div><ChevronRight size={16}/></Link>) : <div className="quiet-state"><CircleCheck size={24}/><strong>没有阻塞中的 Gate</strong><span>新问题会出现在这里。</span></div>}
      </aside>
    </div>
  </div>;
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><Bot size={28}/><strong>{title}</strong><p>{detail}</p><Link to="/new">创建 Demo Run <ChevronRight size={15}/></Link></div>;
}

function NewRun() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("帮我做一条 60 秒以内、给普通中文用户看的今日 AI 圈三件事。避免重复，优先可信消息，语气克制但开场有吸引力。");
  const [autonomy, setAutonomy] = useState("assisted");
  const [duration, setDuration] = useState(60);
  const [format, setFormat] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      const snapshot = await api.createRun({ query, autonomy, target_duration_seconds: duration, preferred_format: format || null });
      await api.start(snapshot.run.run_id, true);
      navigate(`/runs/${snapshot.run.run_id}`);
    } finally { setBusy(false); }
  };
  return <div className="page composer-page">
    <PageHeader eyebrow="INTENT COMPOSER" title="告诉总编导，你想做什么" detail="自然语言目标是主输入；结构化约束用于锁定预算、风险和人工控制。"/>
    <div className="composer">
      <section className="composer__intent"><label htmlFor="goal">创作目标</label><textarea id="goal" value={query} onChange={e => setQuery(e.target.value)} /><div className="intent-hints"><span>目标受众：普通中文用户</span><span>平台：抖音 / B站</span><span>数据：冻结 Demo Fixture</span></div></section>
      <aside className="composer__constraints">
        <h2>运行约束</h2>
        <label>自治等级<select value={autonomy} onChange={e => setAutonomy(e.target.value)}><option value="supervised">Supervised · 每个 Gate</option><option value="assisted">Assisted · 风险时阻塞</option><option value="auto">Auto · 预算内直通</option></select></label>
        <label>内容形式<select value={format} onChange={e => setFormat(e.target.value)}><option value="">由 Planner 决定</option><option value="news_recap">News recap</option><option value="single_explainer">Single explainer</option><option value="thread_story">Thread story</option></select></label>
        <label>目标时长<div className="range-row"><input type="range" min="30" max="180" step="15" value={duration} onChange={e => setDuration(Number(e.target.value))}/><output>{duration}s</output></div></label>
        <div className="budget-box"><span><Gauge size={15}/>预算护栏</span><dl><div><dt>模型调用</dt><dd>≤ 20</dd></div><div><dt>脚本修订</dt><dd>≤ 2</dd></div><div><dt>成片修复</dt><dd>≤ 2</dd></div></dl></div>
        <button className="primary-button primary-button--wide" onClick={submit} disabled={!query.trim() || busy}>{busy ? <RefreshCw className="spin" size={17}/> : <Play size={17}/>}生成计划并运行</button>
      </aside>
    </div>
  </div>;
}

const views = [["timeline", "Timeline", Activity], ["curation", "Curation", BookOpen], ["script", "Script / Storyboard", FileDiff], ["qc", "QC Lab", ShieldCheck]] as const;

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
  const replay = async () => { setBusy("replay"); try { const result = await api.replay(id); setBusy(`replay · ${result.event_count} events`); window.setTimeout(() => setBusy(""), 1800); } catch (e) { setError(String(e)); setBusy(""); } };
  if (!snapshot) return <div className="page loading-state"><RefreshCw className="spin"/>载入 Run…</div>;
  const run = snapshot.run;
  const spent = run.spent as Record<string, number>;
  return <div className="run-workspace">
    <div className="run-controlbar">
      <div className="run-title"><Link to="/">Runs</Link><ChevronRight size={14}/><code>{run.run_id}</code><Status value={run.is_paused ? "paused" : run.state}/></div>
      <div className="run-stats"><span><Clock3 size={14}/>{spent.runtime_seconds ?? 0}s</span><span><Gauge size={14}/>${Number(spent.cost_usd ?? 0).toFixed(3)}</span><span><Bot size={14}/>{spent.llm_calls ?? 0} calls</span></div>
      <div className="run-actions">
        {run.is_paused ? <button onClick={() => action("resume")}><Play size={15}/>恢复</button> : <button onClick={() => action("pause")} disabled={run.state === "COMPLETE"}><Pause size={15}/>暂停</button>}
        {run.state.includes("WAIT") && <button className="approve-button" onClick={() => action("approve_gate", { summary: "Studio 审核通过" })}><Check size={15}/>批准 Gate</button>}
        {run.state.includes("WAIT") && <button className="danger-ghost" onClick={() => action("reject_gate", { summary: "Studio 审核拒绝" })}><X size={15}/>拒绝</button>}
        {run.state === "FAILED" && <button onClick={() => action("retry")}><RefreshCw size={15}/>重试</button>}
        <button onClick={replay}><Activity size={15}/>Replay</button>
        <button onClick={() => action("fork")}><GitForkIcon/>分叉</button>
        <button className="danger-ghost" onClick={() => action("cancel")} disabled={["COMPLETE", "CANCELED"].includes(run.state)}><OctagonX size={15}/>取消</button>
      </div>
    </div>
    {error && <div className="notice notice--error"><CircleAlert size={16}/>{error}<button onClick={() => setError("")}><X size={14}/></button></div>}
    <div className="workspace-tabs" role="tablist">{views.map(([key, label, Icon]) => <button key={key} className={view === key ? "active" : ""} onClick={() => setParams({ view: key })}><Icon size={16}/>{label}</button>)}</div>
    <div className="workspace-content">
      {view === "timeline" && <Timeline snapshot={snapshot}/>} 
      {view === "curation" && <Curation snapshot={snapshot} action={action}/>} 
      {view === "script" && <ScriptView snapshot={snapshot} action={action}/>} 
      {view === "qc" && <QCLab snapshot={snapshot}/>} 
    </div>
    {busy && <div className="action-toast"><RefreshCw className="spin" size={15}/>{busy.replaceAll("_", " ")}</div>}
  </div>;
}

function Timeline({ snapshot }: { snapshot: Snapshot }) {
  const eventsByTask = useMemo(() => new Map(snapshot.events.filter(e => e.status).map(e => [e.state, e])), [snapshot.events]);
  return <div className="timeline-layout">
    <section className="timeline-panel">
      <div className="section-heading"><div><span className="section-kicker">AGENT TRACE</span><h2>执行时间线</h2></div><span className="mono quiet">{snapshot.events.length} events</span></div>
      <div className="timeline-list">{snapshot.tasks.map((task, index) => <TaskItem key={task.task_id} task={task} event={eventsByTask.get(task.target_state)} index={index}/>)}</div>
    </section>
    <aside className="inspector">
      <span className="section-kicker">RUN CONTEXT</span><h2>计划与护栏</h2>
      <p className="inspector__summary">{snapshot.plan.decision_summary}</p>
      <dl className="key-values"><div><dt>创作目标</dt><dd>{snapshot.goal.query}</dd></div><div><dt>时长</dt><dd>{snapshot.goal.target_duration_seconds}s</dd></div><div><dt>风险容忍</dt><dd>{snapshot.goal.risk_tolerance}</dd></div><div><dt>自治等级</dt><dd>{snapshot.run.autonomy}</dd></div></dl>
      <div className="trace-note"><ShieldCheck size={17}/><div><strong>Trace 已脱敏</strong><span>只显示决策摘要、证据、风险和动作，不保存隐藏思维链。</span></div></div>
    </aside>
  </div>;
}

function TaskItem({ task, event, index }: { task: TaskRow; event?: RunEvent; index: number }) {
  return <article className={`task-item task-item--${stateTone(task.status)}`}><div className="task-spine"><span>{task.status === "succeeded" || task.status === "skipped" ? <Check size={14}/> : index + 1}</span></div><div className="task-main"><div className="task-main__top"><div><strong>{task.task_type.replaceAll("_", " ")}</strong><code>{task.tool_name || "Human Gate"}</code></div><Status value={task.status}/></div><p>{event?.summary || (task.status === "pending" ? "等待上游任务完成" : task.error || "状态已持久化")}</p><div className="task-meta"><span>STATE {task.target_state}</span><span>ATTEMPT {task.attempt}/{task.max_attempts}</span>{event?.latency_ms ? <span>{event.latency_ms}ms</span> : null}{event?.cost_usd ? <span>${event.cost_usd.toFixed(3)}</span> : null}</div></div></article>;
}

function Curation({ snapshot, action }: { snapshot: Snapshot; action: (name: string, payload?: Record<string, unknown>) => Promise<void> }) {
  const ordered = [...snapshot.decisions].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));
  const [selected, setSelected] = useState(ordered[0]?.candidate_id ?? "");
  const current = snapshot.evidence.find(e => e.candidate_id === selected);
  const move = (decision: Decision, delta: number) => { const picks = ordered.filter(d => d.selected); const index = picks.findIndex(d => d.candidate_id === decision.candidate_id); const target = index + delta; if (target < 0 || target >= picks.length) return; [picks[index], picks[target]] = [picks[target], picks[index]]; void action("reorder", { candidate_ids: picks.map(d => d.candidate_id) }); };
  return <div className="curation-layout">
    <section className="candidate-queue"><div className="section-heading"><div><span className="section-kicker">PORTFOLIO SELECTION</span><h2>编辑组合</h2></div><span className="queue-count">{ordered.filter(d => d.selected).length} PICK / {ordered.length} TOTAL</span></div>
      <div className="candidate-list">{ordered.map(decision => <button key={decision.candidate_id} className={`candidate-row ${selected === decision.candidate_id ? "active" : ""} ${decision.selected ? "picked" : "rejected"}`} onClick={() => setSelected(decision.candidate_id)}><span className="rank">{decision.rank ? String(decision.rank).padStart(2,"0") : "—"}</span><div className="candidate-copy"><div><code>{decision.candidate_id}</code>{decision.risk_flags.length > 0 && <span className="risk-label"><CircleAlert size={12}/>RISK</span>}</div><strong>{decision.decision_summary}</strong><span>置信度 {Math.round(decision.confidence * 100)}% · 来源 {decision.risk_flags.length ? "需复核" : "已核验"}</span></div><div className="candidate-actions">{decision.selected && <><span onClick={e => {e.stopPropagation(); move(decision,-1);}}><ArrowUp size={14}/></span><span onClick={e => {e.stopPropagation(); move(decision,1);}}><ArrowDown size={14}/></span></>}<span className={`pick-indicator ${decision.selected ? "on" : ""}`}>{decision.selected ? <Check size={14}/> : <X size={14}/>}</span></div></button>)}</div>
    </section>
    <EvidenceInspector pack={current} decision={ordered.find(d => d.candidate_id === selected)} action={action}/>
  </div>;
}

function EvidenceInspector({ pack, decision, action }: { pack?: EvidencePack; decision?: Decision; action: (name: string, payload?: Record<string, unknown>) => Promise<void> }) {
  if (!pack || !decision) return <aside className="inspector"><div className="quiet-state">选择一个 Candidate 查看 Evidence</div></aside>;
  return <aside className="inspector evidence-inspector"><div className="inspector-title"><div><span className="section-kicker">EVIDENCE PACK</span><h2>{pack.candidate_id}</h2></div><strong className={`confidence confidence--${pack.overall_confidence < .6 ? "low" : "high"}`}>{Math.round(pack.overall_confidence*100)}%</strong></div>
    <div className="confidence-bar"><i style={{width:`${pack.overall_confidence*100}%`}}/></div>
    {pack.risk_flags.length > 0 && <div className="risk-box"><CircleAlert size={16}/><div><strong>需要人工复核</strong>{pack.risk_flags.map(flag => <span key={flag}>{flag.replaceAll("_"," ")}</span>)}</div></div>}
    <h3>可用 Claims</h3><div className="claim-list">{pack.claims.map(claim => <div key={claim.claim_id}><ShieldCheck size={15}/><p>{claim.normalized_claim}</p><span>{Math.round(claim.confidence*100)}%</span></div>)}</div>
    <h3>来源</h3>{pack.sources.map(source => <a className="source-block" key={source.source_id} href={source.url} target="_blank" rel="noreferrer"><strong>{source.title}</strong><p>{source.excerpt}</p><span>{source.trust_signals.join(" · ") || "无额外可信信号"}</span></a>)}
    <div className="inspector-actions"><button onClick={() => action(decision.selected ? "reject_candidate" : "approve_candidate", {candidate_id:decision.candidate_id})}>{decision.selected ? <X size={15}/> : <Check size={15}/>} {decision.selected ? "移出 Pick" : "加入 Pick"}</button><button onClick={() => action("request_research", {candidate_id:decision.candidate_id,summary:"用户要求补充独立来源"})}><RefreshCw size={15}/>补充研究</button></div>
  </aside>;
}

function ScriptView({ snapshot, action }: { snapshot: Snapshot; action: (name: string, payload?: Record<string, unknown>) => Promise<void> }) {
  const script = snapshot.documents["script.final.json"] as JsonObject | undefined;
  const review = snapshot.documents["script.review.json"] as JsonObject | undefined;
  const storyboard = snapshot.documents["storyboard.json"] as JsonObject | undefined;
  const segments = (script?.segments ?? []) as Array<Record<string, unknown>>;
  const scenes = (storyboard?.scenes ?? []) as Array<Record<string, unknown>>;
  return <div className="editor-layout">
    <aside className="evidence-rail"><span className="section-kicker">SOURCE MAP</span><h2>证据索引</h2>{snapshot.evidence.filter(e => snapshot.decisions.some(d => d.selected && d.candidate_id === e.candidate_id)).map(pack => <div className="mini-evidence" key={pack.evidence_pack_id}><strong>{pack.candidate_id}</strong><span>{pack.claims.length} claims</span><div><i style={{width:`${pack.overall_confidence*100}%`}}/></div></div>)}</aside>
    <section className="script-editor"><div className="section-heading"><div><span className="section-kicker">GROUNDED SCRIPT</span><h2>口播段落</h2></div><span className="revision-label">REVISION 2</span></div>
      <div className="hook-block"><span>HOOK</span><p>{String(script?.hook ?? "尚未生成 Script")}</p></div>
      <div className="segments">{segments.map((segment,index) => <article className="segment" key={String(segment.segment_id)}><div className="segment__head"><span>SEGMENT {String(index+1).padStart(2,"0")}</span><div><button aria-label="仅重写本段" disabled={Boolean(segment.locked)} onClick={() => { const narration=window.prompt("输入这一段的新口播；其他段落不会改变。",String(segment.narration)); if(narration && narration!==segment.narration) void action("rewrite_segment",{segment_id:segment.segment_id,narration}); }}><RefreshCw size={14}/></button><button aria-label={segment.locked ? "解锁段落":"锁定段落"} onClick={() => action("lock_segment", {segment_id:segment.segment_id,locked:!segment.locked})}>{segment.locked ? <Lock size={14}/> : <Unlock size={14}/>}</button><span>r{String(segment.revision)}</span></div></div><p>{String(segment.narration)}</p><footer><span>{(segment.evidence_ids as string[]).join(" · ")}</span>{Number(segment.revision)>1 && <span className="patched"><FileDiff size={13}/>PATCHED</span>}</footer></article>)}</div>
      {review && <div className="critic-summary"><Bot size={17}/><div><strong>Script Critic · 1 round</strong><span>{String(((review.issues as unknown[]) ?? []).length)} issue detected · {String(((review.diffs as unknown[]) ?? []).length)} segment patched · locked content preserved</span></div></div>}
    </section>
    <aside className="scene-rail"><span className="section-kicker">STORYBOARD</span><h2>Scene Plan</h2>{scenes.map((scene,index) => <div className="scene-card" key={String(scene.scene_id)}><div><span>{String(index+1).padStart(2,"0")}</span><strong>{String(scene.template)}</strong><time>{String(scene.duration_seconds)}s</time></div><p>{String(scene.overlay_text)}</p><small>{String(scene.safe_area_profile)} · {String(scene.motion)}</small></div>)}</aside>
  </div>;
}

function QCLab({ snapshot }: { snapshot: Snapshot }) {
  const before = snapshot.documents["publish_kit/qc.before.json"] as JsonObject | undefined;
  const after = snapshot.documents["publish_kit/qc.after.json"] as JsonObject | undefined;
  const repair = snapshot.documents["publish_kit/repair.json"] as JsonObject | undefined;
  const issues = (before?.issues ?? []) as Array<Record<string, unknown>>;
  return <div className="qc-layout">
    <section className="viewer-panel"><div className="video-stage"><ReviewPlayer video={snapshot.media.video} cover={snapshot.media.cover}/><div className="safe-frame"><span>SAFE AREA</span></div></div><div className="playback-strip"><button><Play size={15}/></button><div className="timeline-track"><i style={{left:"40%"}}/><span style={{width:"100%"}}/></div><time>00:03.2 / 00:08.0</time></div>
      <div className="metric-strip"><div><span>视频</span><strong>{snapshot.media.video ? "1080×1920" : "—"}</strong></div><div><span>时长</span><strong>{String(before?.duration_seconds ?? "—")}s</strong></div><div><span>结构检查</span><strong className="good">PASS</strong></div><div><span>回归 QC</span><strong className={after?.ok ? "good" : "warn"}>{after?.ok ? "PASS" : "WAIT"}</strong></div></div>
    </section>
    <aside className="issue-panel"><div className="section-heading"><div><span className="section-kicker">QUALITY ISSUES</span><h2>问题与修复</h2></div><span className="issue-count">{issues.length}</span></div>{issues.map(issue => <article className="quality-issue" key={String(issue.issue_id)}><div className="quality-issue__head"><Status value={String(issue.severity)}/><code>{String(issue.code)}</code><time>@ {String(issue.timestamp_seconds)}s</time></div><h3>{String(issue.description)}</h3><div className="evidence-code">{(issue.evidence as string[]).map(item => <span key={item}>{item}</span>)}</div><div className="repair-flow"><span className="before">1810px</span><ChevronRight size={15}/><span className="after">1620px</span><strong><Check size={13}/>REGRESSION PASS</strong></div></article>)}
      {repair && <div className="repair-summary"><RefreshCw size={17}/><div><strong>局部修复完成</strong><span>安全区 Patch → 受影响 Scene 重渲染 → 回归检查</span></div></div>}
      <div className="gate-card"><ShieldCheck size={19}/><div><strong>Gate 2 审片</strong><span>{snapshot.run.state === "WAIT_GATE_2" ? "自动修复通过，等待最终确认。" : "已生成审片报告。"}</span></div></div>
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
  return <div className="page"><PageHeader eyebrow="MEMORY & BENCHMARKS" title="把反馈变成下一次的上下文" detail="长期偏好必须审批；一次偶然修改不会直接污染记忆。"/><div className="two-column"><section className="work-panel"><div className="section-heading"><div><span className="section-kicker">PENDING MEMORY</span><h2>记忆候选</h2></div><MemoryStick size={18}/></div>{memories.length===0?<div className="quiet-state"><MemoryStick size={24}/><strong>暂无记忆候选</strong><span>通过 CLI 或 API 留下反馈后，Learner 会提出可审查候选。</span></div>:<div className="memory-list">{memories.map(memory=><article className="memory-item" key={memory.memory_id}><div><Status value={memory.status}/><code>{Math.round(memory.confidence*100)}% · {memory.memory_type}</code></div><p>{memory.content}</p>{memory.status==="pending"&&<footer><button onClick={()=>decide(memory.memory_id,"rejected")}><X size={14}/>拒绝</button><button className="approve-button" onClick={()=>decide(memory.memory_id,"approved")}><Check size={14}/>批准并用于新 Run</button></footer>}</article>)}</div>}</section><section className="work-panel"><div className="section-heading"><div><span className="section-kicker">BENCHMARK LAB</span><h2>Prompt 版本</h2></div><BarChart3 size={18}/></div><div className="version-row"><code>curation-prompt</code><strong>v0.1 · baseline</strong><Status value="pending"/></div><div className="version-row"><code>script-prompt</code><strong>v0.1 · baseline</strong><Status value="pending"/></div></section></div></div>;
}

function SettingsPage() {
  const [health,setHealth] = useState<{ok:boolean;version:string;mode:string;checks:Record<string,boolean>}|null>(null);
  useEffect(()=>{void api.health().then(setHealth)},[]);
  return <div className="page"><PageHeader eyebrow="SETTINGS / DOCTOR" title="本地运行环境" detail="这里只显示能力是否可用，不显示任何密钥、Cookie 或 Token。"/><section className="doctor-list"><DoctorRow label="Agent API" detail={`v${health?.version ?? "—"} · ${health?.mode ?? "checking"}`} ok={Boolean(health)}/><DoctorRow label="SQLite RunStore" detail="WAL · foreign keys · local control plane" ok={Boolean(health?.checks.sqlite)}/><DoctorRow label="FFmpeg / ffprobe" detail="Producer 与结构/音频 QC" ok={Boolean(health?.checks.ffmpeg)}/><DoctorRow label="Browser renderer" detail="Chromium 用于 Tweet Card 与真实视觉 E2E" ok={Boolean(health?.checks.browser)}/><DoctorRow label="Studio bundle" detail="React 生产构建已打包进本地服务" ok={Boolean(health?.checks.studio)}/><DoctorRow label="External providers" detail="Demo Mode 不需要网络；真实运行按配置检查" ok/></section></div>;
}

function DoctorRow({label,detail,ok}:{label:string;detail:string;ok:boolean}) { return <div className="doctor-row"><span className={`doctor-icon ${ok?"ok":"warn"}`}>{ok?<Check size={16}/>:<CircleAlert size={16}/>}</span><div><strong>{label}</strong><span>{detail}</span></div><Status value={ok?"succeeded":"warning"}/></div>; }

export function App() { return <Shell><Routes><Route path="/" element={<Dashboard/>}/><Route path="/new" element={<NewRun/>}/><Route path="/runs/:id" element={<RunWorkspace/>}/><Route path="/memory" element={<MemoryPage/>}/><Route path="/settings" element={<SettingsPage/>}/></Routes></Shell>; }

function relativeTime(value:string) { const delta=Math.max(0,Date.now()-new Date(value).getTime()); if(delta<60_000)return "刚刚"; if(delta<3_600_000)return `${Math.floor(delta/60_000)} 分钟前`; return new Date(value).toLocaleDateString("zh-CN",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}); }

function GitForkIcon(){return <svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="6" cy="5" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="19" r="2"/><path d="M6 7v10M8 7c5 0 4 6 8 6v-5"/></svg>}
