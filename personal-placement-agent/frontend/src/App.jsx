import React,{useEffect,useState} from 'react';
import {BriefcaseBusiness,Search,LayoutDashboard,ListChecks,FileText,Settings,Plus,RefreshCw,Sparkles,Trash2,ArrowUpRight,ShieldCheck,Activity} from 'lucide-react';
const API='http://127.0.0.1:8000/api';
const initialProfile={full_name:'',degree:'',graduation_year:2027,skills:[],preferred_locations:['Remote'],target_roles:['Python Developer','Software Engineer'],include_internships:true,resume_text:''};
const initialJob={title:'',company:'',location:'Remote',job_type:'Full-time',experience:'Fresher',graduation_years:[],required_skills:[],description:'',source_url:'',source:'Manual'};
async function api(path,opts={}){const r=await fetch(API+path,{headers:{'Content-Type':'application/json'},...opts});if(!r.ok)throw new Error((await r.json()).detail||'API request failed');return r.json()}
function Badge({children,tone=''}){return <span className={'badge '+tone}>{children}</span>}
export default function App(){
 const [page,setPage]=useState('Overview'),[profile,setProfile]=useState(initialProfile),[skills,setSkills]=useState(''),[jobs,setJobs]=useState([]),[matches,setMatches]=useState([]),[apps,setApps]=useState([]),[audit,setAudit]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[query,setQuery]=useState(''),[modal,setModal]=useState(false),[job,setJob]=useState(initialJob),[jobSkills,setJobSkills]=useState(''),[plan,setPlan]=useState(null),[toast,setToast]=useState('');
 async function load(){setLoading(true);try{const [p,j,m,a,l]=await Promise.all([api('/profile'),api('/jobs'),api('/matches'),api('/applications'),api('/audit')]);setProfile(p);setSkills((p.skills||[]).join(', '));setJobs(j);setMatches(m);setApps(a);setAudit(l);setError('')}catch(e){setError(e.message+'. Start the FastAPI backend on port 8000.')}finally{setLoading(false)}}
 useEffect(()=>{load()},[]);
 function notify(s){setToast(s);setTimeout(()=>setToast(''),2500)}
 async function saveProfile(e){e.preventDefault();try{await api('/profile',{method:'PUT',body:JSON.stringify({...profile,skills:skills.split(',').map(x=>x.trim()).filter(Boolean)})});await load();notify('Profile saved')}catch(e){setError(e.message)}}
 async function addJob(e){e.preventDefault();try{await api('/jobs',{method:'POST',body:JSON.stringify({...job,required_skills:jobSkills.split(',').map(x=>x.trim()).filter(Boolean)})});setModal(false);setJob(initialJob);setJobSkills('');await load();notify('Job saved')}catch(e){setError(e.message)}}
 async function status(id,s){try{await api('/applications/'+id,{method:'POST',body:JSON.stringify({status:s,notes:''})});await load();notify('Tracker updated')}catch(e){setError(e.message)}}
 async function remove(id){if(!confirm('Delete this listing and its tracker record?'))return;try{await api('/jobs/'+id,{method:'DELETE'});await load()}catch(e){setError(e.message)}}
 async function showPlan(id){try{setPlan(await api('/agent/plan/'+id))}catch(e){setError(e.message)}}
 const filtered=matches.filter(j=>(j.title+' '+j.company+' '+j.location+' '+j.required_skills.join(' ')).toLowerCase().includes(query.toLowerCase()));
 const active=apps.filter(a=>['Applied','Assessment','Interview','Offer'].includes(a.status)).length;
 return <div className="shell"><aside className="sidebar"><div className="brand"><div className="brand-icon"><Sparkles/></div><div><b>CareerPilot</b><small>PERSONAL AI AGENT</small></div></div><div className="nav-label">WORKSPACE</div>{[['Overview',LayoutDashboard],['Job matches',Search],['Applications',ListChecks],['My profile',FileText],['Agent activity',Activity],['AI tools',Sparkles],['Settings',Settings]].map(([n,I])=><button key={n} className={'nav '+(page===n?'selected':'')} onClick={()=>setPage(n)}><I size={17}/>{n}</button>)}<div className="side-note"><ShieldCheck size={18}/><b>Local-first MVP</b><p>Your profile and tracker are stored locally.</p></div></aside>
 <main><header className="top"><div><small>PERSONAL PLACEMENT WORKSPACE</small><h1>{page}</h1></div><div className="topright"><span className="dot"/>Local workspace <button className="iconbtn" onClick={load}><RefreshCw size={16}/></button><div className="avatar">{(profile.full_name||'S').charAt(0).toUpperCase()}</div></div></header>
 {error&&<div className="error">{error}<button onClick={()=>setError('')}>×</button></div>}{toast&&<div className="toast">{toast}</div>}
 {loading?<div className="loading">Loading workspace…</div>:<>
 {page==='Overview'&&<div className="content"><section className="hero"><Badge tone="purple">✦ YOUR JOB SEARCH, ORGANIZED</Badge><h2>Find the right role.<br/><span>Prepare with purpose.</span></h2><p>One workspace for job discovery, eligibility checks and application progress.</p><div className="actions"><button className="primary" onClick={()=>setPage('Job matches')}>Explore job matches <ArrowUpRight size={15}/></button><button className="secondary" onClick={()=>setPage('My profile')}>Update profile</button></div><div className="hero-orb"><Sparkles size={40}/></div></section>
 <div className="section-title"><div><h2>Search at a glance</h2><p>Keep your placement journey moving.</p></div><button className="linkbtn" onClick={()=>setPage('Applications')}>View tracker ↗</button></div>
 <div className="stats">{[['Jobs collected',jobs.length,'Saved listings'],['Eligible matches',matches.filter(j=>j.eligible).length,'By current rules'],['Active applications',active,'Applied or in progress'],['Interviews / offers',apps.filter(a=>['Interview','Offer'].includes(a.status)).length,'Tracked milestones']].map(([label,value,note])=><div className="stat" key={label}><span>{label}</span><b>{value}</b><small>{note}</small></div>)}</div>
 <div className="columns"><section className="panel"><div className="panelhead"><div><h2>Top job matches</h2><p>Ranked against your profile</p></div><button className="iconbtn" onClick={()=>setPage('Job matches')}>↗</button></div>{matches.slice(0,4).map(j=><JobRow key={j.id} j={j} plan={showPlan}/>)}{!matches.length&&<Empty text="No jobs yet. Add a job listing to begin." click={()=>setModal(true)}/>}</section><section className="panel"><div className="panelhead"><div><h2>Agent readiness</h2><p>Current MVP capabilities</p></div><Badge tone="green">MVP</Badge></div>{[['Candidate profile',!!profile.resume_text,'Add resume text in My profile'],['Job collection',jobs.length>0,`${jobs.length} saved listing(s)`],['Application tracking',apps.length>0,`${apps.length} tracked application(s)`],['Naukri browser integration',false,'Not enabled; requires permitted access']].map(([a,b,c])=><div className="ready" key={a}><span className={b?'readyyes':'readyno'}>{b?'✓':'!'}</span><div><b>{a}</b><p>{c}</p></div></div>)}<div className="security"><ShieldCheck size={16}/> Application submission is disabled in this MVP.</div></section></div>
 <section className="panel addstrip"><div className="plusicon"><Plus/></div><div><h2>Bring a job into your workspace</h2><p>Add listing details and get an explainable match.</p></div><button className="primary" onClick={()=>setModal(true)}>Add a job <Plus size={15}/></button></section></div>}
 {page==='Job matches'&&<div className="content"><div className="toolbar"><div className="search"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search roles, companies, skills…"/></div><button className="primary" onClick={()=>setModal(true)}><Plus size={15}/> Add job</button></div><p className="muted">{filtered.length} listings · {filtered.filter(j=>j.eligible).length} eligible by current rules · scores are estimates, not hiring predictions</p><div className="joblist">{filtered.map(j=><article className="jobcard" key={j.id}><div className="jobhead"><div className="companyicon">{(j.company||j.title||'J')[0].toUpperCase()}</div><div className="jobtitle"><h2>{j.title}</h2><p>{j.company||'Company not specified'} · {j.location||'Location unspecified'}</p><div className="badges"><Badge>{j.job_type}</Badge><Badge tone={j.eligible?'green':'red'}>{j.eligible?'Eligible by rules':'Check eligibility'}</Badge></div></div><div className="score">{j.score}%<small>match</small></div></div><div className="jobdetails"><div><b>Why this match</b><ul>{j.reasons.slice(0,4).map(r=><li key={r}>{r}</li>)}</ul></div>{j.missing_skills.length>0&&<div><b>Skills to build</b><div className="skills">{j.missing_skills.map(s=><span key={s}>{s}</span>)}</div></div>}</div><div className="jobfoot"><div className="joblinks">{j.source_url&&<a href={j.source_url} target="_blank" rel="noreferrer">Open listing ↗</a>}<button className="linkbtn" onClick={()=>showPlan(j.id)}>✦ Agent plan</button></div><div className="jobactions"><select aria-label="Application status" value={j.application?.status||'Saved'} onChange={e=>status(j.id,e.target.value)}>{['Saved','Needs review','Ready to apply','Applied','Assessment','Interview','Rejected','Offer','Withdrawn'].map(s=><option key={s}>{s}</option>)}</select><button className="iconbtn" title="Delete listing" onClick={()=>remove(j.id)}><Trash2 size={15}/></button></div></div></article>)}{!filtered.length&&<Empty text="No jobs found. Add a listing to get started." click={()=>setModal(true)}/>}</div></div>}
 {page==='Applications'&&<div className="content"><div className="section-title"><div><h2>Application pipeline</h2><p>Track each role from saved to outcome.</p></div><button className="primary" onClick={()=>setPage('Job matches')}>Browse jobs ↗</button></div><div className="pipeline">{['Saved','Needs review','Ready to apply','Applied','Assessment','Interview','Offer','Rejected'].map(s=><div key={s}><b>{apps.filter(a=>a.status===s).length}</b><span>{s}</span></div>)}</div><section className="panel tablepanel"><table><thead><tr><th>ROLE / COMPANY</th><th>STATUS</th><th>UPDATED</th><th>LINK</th></tr></thead><tbody>{apps.map(a=><tr key={a.id}><td><b>{a.title}</b><small>{a.company||'Company unspecified'}</small></td><td><Badge tone={['Applied','Interview','Offer'].includes(a.status)?'green':''}>{a.status}</Badge></td><td>{a.updated_at?.slice(0,10)||'—'}</td><td>{a.source_url?<a href={a.source_url} target="_blank" rel="noreferrer">Open ↗</a>:'—'}</td></tr>)}</tbody></table>{!apps.length&&<Empty text="No applications tracked yet." />}</section></div>}
 {page==='My profile'&&<div className="content narrow"><section className="panel"><div className="panelhead"><div><h2>Candidate profile</h2><p>Used for job matching and truthful application preparation.</p></div><FileText/></div><form className="formgrid" onSubmit={saveProfile}><Field label="Full name"><input value={profile.full_name||''} onChange={e=>setProfile({...profile,full_name:e.target.value})}/></Field><Field label="Degree"><input value={profile.degree||''} placeholder="B.E. Computer Science" onChange={e=>setProfile({...profile,degree:e.target.value})}/></Field><Field label="Graduation year"><input type="number" value={profile.graduation_year||''} onChange={e=>setProfile({...profile,graduation_year:e.target.value?Number(e.target.value):null})}/></Field><Field label="Skills, comma separated"><input value={skills} onChange={e=>setSkills(e.target.value)} placeholder="Python, SQL, React"/></Field><Field label="Target roles, comma separated"><input value={(profile.target_roles||[]).join(', ')} onChange={e=>setProfile({...profile,target_roles:e.target.value.split(',').map(s=>s.trim()).filter(Boolean)})}/></Field><Field label="Preferred locations, comma separated"><input value={(profile.preferred_locations||[]).join(', ')} onChange={e=>setProfile({...profile,preferred_locations:e.target.value.split(',').map(s=>s.trim()).filter(Boolean)})}/></Field><label className="check"><input type="checkbox" checked={!!profile.include_internships} onChange={e=>setProfile({...profile,include_internships:e.target.checked})}/> Include internships</label><Field label="Resume text" wide><textarea rows="9" value={profile.resume_text||''} onChange={e=>setProfile({...profile,resume_text:e.target.value})} placeholder="Paste resume text here. Do not include passwords or unrelated sensitive information."/></Field><div className="formactions"><button className="primary">Save profile <ShieldCheck size={15}/></button></div></form></section></div>}
 {page==='Agent activity'&&<div className="content"><section className="panel"><div className="panelhead"><div><h2>Audit log</h2><p>Recent actions recorded by the backend.</p></div><Activity/></div>{audit.map(a=><div className="auditrow" key={a.id}><b>{a.action.replaceAll('_',' ')}</b><span>{a.details}</span><small>{a.created_at}</small></div>)}</section></div>}
 {page==='AI tools'&&<div className="content"><AITools jobs={jobs} profile={profile} notify={notify} setError={setError} onReload={load}/></div>}
 {page==='Settings'&&<div className="content narrow"><section className="panel"><div className="panelhead"><div><h2>Security & integrations</h2><p>Configure the future agent safely.</p></div><ShieldCheck/></div>{[['Naukri account','Sign in only on the official site. Never paste your password into this app.','Not connected'],['Automatic submission','Disabled until permitted integration and safeguards exist.','Disabled'],['LLM provider','Not configured; add only through backend environment variables.','Optional'],['Data storage','Local SQLite database. Keep database and secrets out of Git.','Local']].map(([a,b,c])=><div className="settingrow" key={a}><div><b>{a}</b><p>{b}</p></div><Badge>{c}</Badge></div>)}</section></div>}
 </>}
 <footer>CareerPilot MVP · Built for your placement journey · Local-first by design</footer></main>
 {modal&&<div className="overlay" onClick={()=>setModal(false)}><div className="modal" onClick={e=>e.stopPropagation()}><div className="modalhead"><div><h2>Add job listing</h2><p>Enter verified details from a job listing.</p></div><button className="iconbtn" onClick={()=>setModal(false)}>×</button></div><form className="formgrid" onSubmit={addJob}><Field label="Job title"><input required value={job.title} onChange={e=>setJob({...job,title:e.target.value})} placeholder="Python Developer Intern"/></Field><Field label="Company"><input value={job.company} onChange={e=>setJob({...job,company:e.target.value})}/></Field><Field label="Location"><input value={job.location} onChange={e=>setJob({...job,location:e.target.value})}/></Field><Field label="Job type"><select value={job.job_type} onChange={e=>setJob({...job,job_type:e.target.value})}><option>Full-time</option><option>Internship</option><option>Contract</option><option>Part-time</option></select></Field><Field label="Eligible graduation years"><input value={job.graduation_years.join(',')} onChange={e=>setJob({...job,graduation_years:e.target.value.split(',').map(x=>Number(x.trim())).filter(Boolean)})} placeholder="2026, 2027 (optional)"/></Field><Field label="Required skills, comma separated"><input value={jobSkills} onChange={e=>setJobSkills(e.target.value)} placeholder="Python, FastAPI, SQL"/></Field><Field label="Source URL" wide><input type="url" value={job.source_url} onChange={e=>setJob({...job,source_url:e.target.value})} placeholder="https://…"/></Field><Field label="Job description" wide><textarea rows="5" value={job.description} onChange={e=>setJob({...job,description:e.target.value})}/></Field><div className="formactions"><button type="button" className="secondary" onClick={()=>setModal(false)}>Cancel</button><button className="primary">Save listing</button></div></form></div></div>}
 {plan&&<div className="overlay" onClick={()=>setPlan(null)}><div className="modal" onClick={e=>e.stopPropagation()}><div className="modalhead"><div><Badge tone="purple">✦ AGENT PLAN</Badge><h2>{plan.title}</h2><p>Match {plan.score}% · {plan.eligible?'Eligible by current rules':'Eligibility mismatch'}</p></div><button className="iconbtn" onClick={()=>setPlan(null)}>×</button></div>{plan.steps.map((s,i)=><div className="planrow" key={s.step}><b>{i+1}. {s.step.replaceAll('_',' ')}</b><p>{s.description}</p></div>)}<div className="security"><ShieldCheck size={16}/> This plan does not submit applications or interact with Naukri.</div><button className="primary full" onClick={()=>setPlan(null)}>Close</button></div></div>}
 </div>
}
function Field({label,children,wide}){return <label className={'field '+(wide?'wide':'')}><span>{label}</span>{children}</label>}
function JobRow({j,plan}){return <div className="jobrow"><div className="companyicon">{(j.company||j.title||'J')[0].toUpperCase()}</div><div className="jobrowtext"><b>{j.title}</b><p>{j.company||'Company unspecified'} · {j.location||'Location unspecified'}</p><div className="badges"><Badge tone={j.eligible?'green':'red'}>{j.eligible?'Eligible':'Check eligibility'}</Badge><Badge>{j.score}% match</Badge></div></div><button className="iconbtn" onClick={()=>plan(j.id)}><ArrowUpRight size={16}/></button></div>}
function Empty({text,click}){return <div className="empty"><BriefcaseBusiness size={25}/><p>{text}</p>{click&&<button className="secondary" onClick={click}>Add a job</button>}</div>}


function AITools({jobs,profile,notify,setError,onReload}) {
 const [jobId,setJobId]=useState(jobs[0]?.id ? String(jobs[0].id) : '');
 const [feedUrl,setFeedUrl]=useState('');
 const [naukriRole,setNaukriRole]=useState('');
 const [naukriLocation,setNaukriLocation]=useState('');
 const [resumeDraft,setResumeDraft]=useState('');
 const [interviewFocus,setInterviewFocus]=useState('technical interview');
 const [interviewPlan,setInterviewPlan]=useState('');
 const [matchExplanation,setMatchExplanation]=useState('');
 const [reviews,setReviews]=useState([]);
 const [notifications,setNotifications]=useState([]);
 const [aiStatus,setAiStatus]=useState(null);
 const [fillReviewId,setFillReviewId]=useState('');
 const [fillSelector,setFillSelector]=useState('input[name="name"]');
 const [fillProfileKey,setFillProfileKey]=useState('full_name');
 const [busy,setBusy]=useState(false);
 const [importSummary,setImportSummary]=useState('');
 const [autoDiscovery,setAutoDiscovery]=useState(null);
 const [discoveryInterval,setDiscoveryInterval]=useState('6');
 useEffect(()=>{if(!jobId&&jobs[0]?.id)setJobId(String(jobs[0].id))},[jobs,jobId]);
 useEffect(()=>{if(!naukriRole&&(profile.target_roles||[]).length)setNaukriRole(profile.target_roles[0]);if(!naukriLocation&&(profile.preferred_locations||[]).length)setNaukriLocation(profile.preferred_locations[0])},[profile,naukriRole,naukriLocation]);
 async function refresh(){
   try{
     const [r,n,s,d]=await Promise.all([api('/reviews'),api('/notifications'),api('/ai/status'),api('/browser/auto-discovery')]);
     setReviews(r);setNotifications(n);setAiStatus(s);setAutoDiscovery(d);setDiscoveryInterval(String(d.interval_hours||6));
     if(!fillReviewId){const approved=r.find(x=>x.status==='draft_approved');if(approved)setFillReviewId(String(approved.id));}
   }catch(e){setError(e.message)}
 }
 useEffect(()=>{refresh()},[]);
 async function run(action){
   setBusy(true);
   try {
     const id=Number(jobId);
     if(action==='tailor'){
       const r=await api('/ai/tailor-resume',{method:'POST',body:JSON.stringify({job_id:id})});
       setResumeDraft(r.draft);notify('Resume draft prepared — review before use.');
     } else if(action==='prepare'){
       const r=await api('/application-drafts/prepare',{method:'POST',body:JSON.stringify({job_id:id,answers:{}})});
       notify('Application review draft created.');
     } else if(action==='interview'){
       const r=await api('/agent/interview-plan',{method:'POST',body:JSON.stringify({job_id:id,focus:interviewFocus})});
       setInterviewPlan(r.plan);notify('Interview plan prepared.');
     } else if(action==='match'){
       const r=await api('/ai/explain-match',{method:'POST',body:JSON.stringify({job_id:id})});
       setMatchExplanation(r.explanation);notify('Match explanation prepared.');
     } else if(action==='browser'){
       const r=await api('/browser/open-naukri',{method:'POST',body:'{}'});
       notify(r.message || 'Browser opened.');
     } else if(action==='naukri-search'){
       const r=await api('/browser/search-naukri',{method:'POST',body:JSON.stringify({role:naukriRole,location:naukriLocation||'India'})});
       notify(r.message || 'Naukri search opened.');
     } else if(action==='import-naukri'){
       const r=await api('/browser/import-visible-jobs',{method:'POST',body:'{}'});
       setImportSummary(`Found ${r.found} visible listing(s): ${r.added} added, ${r.skipped} duplicate/ignored. ${r.note}`);
       notify(`Naukri import complete: ${r.added} added.`);
     } else if(action==='auto-toggle'){
       const r=await api('/browser/auto-discovery',{method:'PUT',body:JSON.stringify({enabled:!autoDiscovery?.enabled,interval_hours:Number(discoveryInterval)})});
       setAutoDiscovery(r);notify(r.message||'Automatic discovery settings saved.');
     } else if(action==='auto-run'){
       const r=await api('/browser/auto-discovery/run-now',{method:'POST',body:'{}'});
       setImportSummary(`Automatic search checked ${r.queries?.length||0} role/location search(es), found ${r.found||0}, added ${r.added||0}. ${r.message||''}`);
       notify(`Naukri discovery finished: ${r.added||0} new listing(s) added.`);
       if(onReload) await onReload();
     } else if(action==='fill'){
       const r=await api('/browser/fill-reviewed-fields',{method:'POST',body:JSON.stringify({
         review_id:Number(fillReviewId), fields:[{selector:fillSelector,profile_key:fillProfileKey}]
       })});
       notify(`Filled ${r.filled.length} field(s); ${r.blocked.length} blocked. Nothing submitted.`);
     } else if(action==='discover'){
       const r=await api('/discovery/feed',{method:'POST',body:JSON.stringify({feed_url:feedUrl})});
       notify(`Feed checked: ${r.added} added, ${r.skipped} skipped.`);
     }
     await refresh();
     if(action==='import-naukri' && onReload) await onReload();
   } catch(e){setError(e.message)}
   finally{setBusy(false)}
 }
 async function review(id,decision){
   try{await api(`/reviews/${id}`,{method:'POST',body:JSON.stringify({decision})});await refresh();notify('Review decision saved. No portal submission occurred.')}
   catch(e){setError(e.message)}
 }
 async function readNotification(id){
   try{await api(`/notifications/${id}/read`,{method:'POST',body:'{}'});await refresh()}
   catch(e){setError(e.message)}
 }
 return <div className="ai-workbench">
   <div className="feature-banner"><div><Badge tone="purple">AGENT TOOLBOX</Badge><h2>Prepare, verify and learn</h2><p>These tools prepare drafts and plans. They do not submit applications to Naukri.</p></div><div className="feature-symbol"><Sparkles size={29}/></div></div>
   <div className="tool-grid">
     <section className="panel tool-panel"><div className="panelhead"><div><h2>AI job-match explanation</h2><p>Explain evidence, unknowns and skill gaps for a saved job.</p></div><Sparkles size={20}/></div>
       <Field label="Target job"><select value={jobId} onChange={e=>setJobId(e.target.value)}>{jobs.map(j=><option value={j.id} key={j.id}>{j.title} — {j.company||'Company unspecified'}</option>)}</select></Field>
       <button className="primary" disabled={!jobId||busy} onClick={()=>run('match')}>Explain this match <Sparkles size={15}/></button>
       {matchExplanation&&<Field label="Match analysis" wide><textarea rows="9" value={matchExplanation} onChange={e=>setMatchExplanation(e.target.value)}/></Field>}
     </section>
     <section className="panel tool-panel"><div className="panelhead"><div><h2>Resume tailoring</h2><p>Use a saved job and your profile resume.</p></div><FileText size={20}/></div>
       <Field label="Target job"><select value={jobId} onChange={e=>setJobId(e.target.value)}>{jobs.map(j=><option value={j.id} key={j.id}>{j.title} — {j.company||'Company unspecified'}</option>)}</select></Field>
       <button className="primary" disabled={!jobId||busy} onClick={()=>run('tailor')}>Prepare resume draft <Sparkles size={15}/></button>
       {resumeDraft&&<Field label="Draft — review and edit before use" wide><textarea rows="11" value={resumeDraft} onChange={e=>setResumeDraft(e.target.value)}/></Field>}
     </section>
     <section className="panel tool-panel"><div className="panelhead"><div><h2>Interview & skill agent</h2><p>Create a focused preparation plan.</p></div><Activity size={20}/></div>
       <Field label="Preparation focus"><select value={interviewFocus} onChange={e=>setInterviewFocus(e.target.value)}><option>technical interview</option><option>HR interview</option><option>aptitude and pseudocode</option><option>project discussion</option><option>coding interview</option></select></Field>
       <button className="primary" disabled={!jobId||busy} onClick={()=>run('interview')}>Generate 7-day plan <Sparkles size={15}/></button>
       {interviewPlan&&<Field label="Preparation plan" wide><textarea rows="11" value={interviewPlan} onChange={e=>setInterviewPlan(e.target.value)}/></Field>}
     </section>
     <section className="panel tool-panel"><div className="panelhead"><div><h2>Profile-guided Naukri search</h2><p>Open an official Naukri search using your target role and preferred location.</p></div><Search size={20}/></div>
       <Field label="Target role"><input value={naukriRole} onChange={e=>setNaukriRole(e.target.value)} placeholder="e.g. Python Developer" list="naukri-role-options"/><datalist id="naukri-role-options">{(profile.target_roles||[]).map(r=><option value={r} key={r}/>)}</datalist></Field>
       <Field label="Preferred location"><input value={naukriLocation} onChange={e=>setNaukriLocation(e.target.value)} placeholder="e.g. Chennai, Remote, India" list="naukri-location-options"/><datalist id="naukri-location-options">{(profile.preferred_locations||[]).map(l=><option value={l} key={l}/>)}</datalist></Field>
       <button className="primary" disabled={!naukriRole.trim()||busy||!aiStatus?.browser_enabled} onClick={()=>run('naukri-search')}>Open matching Naukri search <ArrowUpRight size={15}/></button>
       <button className="secondary" disabled={busy||!aiStatus?.browser_enabled} onClick={()=>run('import-naukri')}>Import visible Naukri listings <RefreshCw size={15}/></button>
       {importSummary&&<p className="helptext">{importSummary}</p>}
       <p className="helptext">Manual import collects only currently rendered job cards. Automatic discovery uses a bounded set of visible search pages from your profile; it does not paginate, use hidden APIs, bypass CAPTCHA/MFA, or submit applications. Use only if permitted by Naukri's current terms.</p>
       <div className="panelhead" style={{marginTop:18}}><div><h2>Automatic Naukri discovery</h2><p>Search profile roles and locations on a schedule.</p></div><RefreshCw size={20}/></div>
       <Field label="Repeat search every"><select value={discoveryInterval} onChange={e=>setDiscoveryInterval(e.target.value)}><option value="1">1 hour</option><option value="3">3 hours</option><option value="6">6 hours</option><option value="12">12 hours</option><option value="24">24 hours</option></select></Field>
       <div className="status-row"><span>Schedule</span><Badge tone={autoDiscovery?.enabled?'green':''}>{autoDiscovery?.enabled?'Enabled':'Disabled'}</Badge></div>
       <div className="status-row"><span>Last run</span><span>{autoDiscovery?.last_run||'Not run yet'}</span></div>
       <div className="status-row"><span>Last result</span><span>{autoDiscovery?.last_status||'Not started'}{autoDiscovery?.last_added!=null?` · ${autoDiscovery.last_added} added`:''}</span></div>
       {autoDiscovery?.last_error&&<p className="helptext">Status detail: {autoDiscovery.last_error}</p>}
       <div className="button-row"><button className="primary" disabled={busy||!aiStatus?.browser_enabled} onClick={()=>run('auto-toggle')}>{autoDiscovery?.enabled?'Disable automatic discovery':'Enable automatic discovery'}</button><button className="secondary" disabled={busy||!aiStatus?.browser_enabled} onClick={()=>run('auto-run')}>Search now <Search size={15}/></button></div>
       <p className="helptext">Before enabling: open the local browser and sign in manually. The backend must remain running and your computer must stay awake for scheduled checks. Each cycle checks up to 6 role/location combinations and up to 25 visible listings per search page. New listings are deduplicated and appear in Job matches. If Naukri requests verification, complete it yourself and retry.</p>
     </section>
     <section className="panel tool-panel"><div className="panelhead"><div><h2>Job discovery from permitted feeds</h2><p>Import an RSS/Atom feed that explicitly permits automated access.</p></div><Search size={20}/></div>
       <Field label="Public feed URL"><input type="url" value={feedUrl} onChange={e=>setFeedUrl(e.target.value)} placeholder="https://example.com/jobs/feed.xml"/></Field>
       <button className="primary" disabled={!feedUrl||busy} onClick={()=>run('discover')}>Collect listings <ArrowUpRight size={15}/></button>
       <p className="helptext">Feed entries are unverified. Imported listings are deduplicated and ranked against your profile automatically.</p>
     </section>
     <section className="panel tool-panel"><div className="panelhead"><div><h2>Naukri browser</h2><p>Open a local browser for manual sign-in.</p></div><ShieldCheck size={20}/></div>
       <div className="browser-status"><span className={aiStatus?.browser_enabled?'dot':'status-off'}/><span>{aiStatus?.browser_enabled?'Local browser enabled':'Disabled by default'}</span></div>
       <button className="secondary" disabled={busy||!aiStatus?.browser_enabled} onClick={()=>run('browser')}>Open Naukri browser <ArrowUpRight size={15}/></button>
       <p className="helptext">Login is manual. The browser never sends credentials to the app or an LLM. Naukri form submission remains disabled.</p>
     </section>
     <section className="panel tool-panel"><div className="panelhead"><div><h2>Reviewed form filling</h2><p>Fill one explicitly mapped profile field in the open Naukri browser.</p></div><ShieldCheck size={20}/></div>
       <Field label="Approved draft"><select value={fillReviewId} onChange={e=>setFillReviewId(e.target.value)}><option value="">Choose an approved draft</option>{reviews.filter(r=>r.status==='draft_approved').map(r=><option key={r.id} value={r.id}>#{r.id} · {r.title}</option>)}</select></Field>
       <Field label="CSS selector for one text field"><input value={fillSelector} onChange={e=>setFillSelector(e.target.value)} placeholder={'input[name="name"]'}/></Field>
       <Field label="Verified profile field"><select value={fillProfileKey} onChange={e=>setFillProfileKey(e.target.value)}><option value="full_name">Full name</option><option value="degree">Degree</option><option value="graduation_year">Graduation year</option><option value="skills">Skills</option></select></Field>
       <button className="secondary" disabled={!fillReviewId||!aiStatus?.browser_enabled||busy} onClick={()=>run('fill')}>Fill selected field <ArrowUpRight size={15}/></button>
       <p className="helptext">Requires an approved draft and the active local browser on naukri.com. Password, OTP, contact and other sensitive fields are blocked. This never clicks Submit.</p>
     </section>
     <section className="panel tool-panel"><div className="panelhead"><div><h2>Application preparation</h2><p>Queue a draft for review before any external action.</p></div><ListChecks size={20}/></div>
       <Field label="Target job"><select value={jobId} onChange={e=>setJobId(e.target.value)}>{jobs.map(j=><option value={j.id} key={j.id}>{j.title} — {j.company||'Company unspecified'}</option>)}</select></Field>
       <button className="primary" disabled={!jobId||busy} onClick={()=>run('prepare')}>Prepare application draft <FileText size={15}/></button>
       <p className="helptext">Sensitive or uncertain fields must be reviewed manually. Approving a draft does not submit it.</p>
     </section>
     <section className="panel tool-panel"><div className="panelhead"><div><h2>AI and automation status</h2><p>Current configuration and safeguards.</p></div><ShieldCheck size={20}/></div>
       <div className="status-row"><span>LLM provider</span><Badge tone={aiStatus?.llm_configured?'green':''}>{aiStatus?.llm_configured?'Configured':'Fallback mode'}</Badge></div>
       <div className="status-row"><span>Browser</span><Badge tone={aiStatus?.browser_enabled?'green':''}>{aiStatus?.browser_enabled?'Enabled':'Disabled'}</Badge></div>
       <div className="status-row"><span>Auto-submit</span><Badge tone="red">Disabled</Badge></div>
       <p className="helptext">To enable AI drafts, configure LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in the backend environment.</p>
     </section>
   </div>
   <div className="tool-grid lower-grid">
     <section className="panel"><div className="panelhead"><div><h2>Draft review queue</h2><p>Review decisions apply to drafts only.</p></div><RefreshCw size={18} onClick={refresh}/></div>
       {reviews.length?reviews.map(r=><div className="review-item" key={r.id}><div><b>{r.title}</b><p>{r.company||'Company unspecified'} · {r.action.replaceAll('_',' ')}</p><Badge tone={r.status==='pending'?'purple':'green'}>{r.status}</Badge></div>{r.status==='pending'&&<div className="review-actions"><button className="secondary" onClick={()=>review(r.id,'reject')}>Reject</button><button className="primary" onClick={()=>review(r.id,'approve_draft')}>Approve draft</button></div>}</div>):<div className="empty"><p>No drafts waiting for review.</p></div>}
     </section>
     <section className="panel"><div className="panelhead"><div><h2>Notifications</h2><p>Job discovery and application reminders.</p></div><Activity size={18}/></div>
       {notifications.length?notifications.slice(0,8).map(n=><div className={'notification '+(n.read?'read':'')} key={n.id}><div><b>{n.title}</b><p>{n.body}</p><small>{n.created_at}</small></div>{!n.read&&<button className="linkbtn" onClick={()=>readNotification(n.id)}>Mark read</button>}</div>):<div className="empty"><p>No notifications yet.</p></div>}
     </section>
   </div>
 </div>
}
