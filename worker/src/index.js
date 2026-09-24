// bhr-dispatch - starts the Bristow-Hall site's update right after each data release.
// (v3.60, 21 September 2026, collection 278; Anthony: "MAKE SURE THAT THERE ARE NO ERRORS IN THE LIVE UPDATING FUNCTION
// ... AND THAT OUR LIVE UPDATING IS SCHEDULED ON DATA RELEASE DATES AND TIMES"; "MAKE SURE THERE ARE NEVER ANY ERRORS
// AGAIN WITH THE GITHUB AND THE AUTO UPDATING")
//
// The update is a GitHub Actions run (update.yml in anthonythomashall3-rgb/bristow-hall-live, about three minutes).
// GitHub's own scheduler could not be relied on to start it: its firings came two to four hours late on 18 and 19
// September and stopped after 19 September 17:10Z. This Worker runs every five minutes on Cloudflare's Cron Triggers.
// It reads the release slots the site publishes (/run_slots.json, written by s2/run_slots.py from the release calendar)
// and the time of the build the site carries. When a slot has passed since that build and no run is under way, it starts
// the workflow. A run that ends without bringing the site past the slot is retried after eight minutes, three starts at
// most for one slot; after that it waits for the next slot. The phone hears of a failed run and of a slot given up, each
// at most once a day. When run_slots.json cannot be read, or lists no future slot, it uses its own weekday times:
// 08:50, 09:35, 10:20 and 17:05 on weekdays, New York time. Every check writes a heartbeat (last_tick) that the
// status page shows and that every workflow run reads: if the Worker stops, the workflow says so. GitHub's own schedule is
// the second line. Nothing depends on the Mac (Anthony, 21 September 2026: "DONT RELY ON THE MAC AT ALL").
//
//
// 22 September 2026 (collection 306; Anthony: "I NEED TO KNOW IF EVERY UPDATE WORKS SUCCESSFULLY OR NOT ... I SHOULD NEVER
// GET A NOTIFICATION THAT THE AUTOMATIC UPDATING FEATURE HAS FAILED"): every run now sends its own message (ops/notify.py,
// success or failure), so this Worker no longer sends the once-a-day "the update failed". It speaks only about what a run
// cannot say itself, once per slot or per run: a run that ended without sending its message (cancelled, timed out, or
// failed before it could); a slot whose three starts all failed; a run stuck for more than 25 minutes; a slot that could
// not be started at all.
//
// Secrets (Cloudflare dashboard > Workers & Pages > bhr-dispatch > Settings > Variables and Secrets):
//   GH_TOKEN     a fine-grained GitHub token for anthonythomashall3-rgb/bristow-hall-live, Actions: Read and write
//   NTFY_TOPIC   the phone alert topic (the site's own; set from the Mac's local.env without being shown)
// KV namespace STATE (BHR_DISPATCH_STATE): the heartbeat and which alerts were already sent.
// Opening the Worker's URL shows what it would do now and its last heartbeat; it starts nothing and never calls GitHub.

// the deployed code's version: every workflow run compares it with the repository's copy of this file, so a starter
// redeployed from an old clone is caught (22 September 2026, collection 306)
const VERSION = '2026-09-24b (bristow-hall-live)';
const REPO = 'anthonythomashall3-rgb/bristow-hall-live';
const WORKFLOW = 'update.yml';
const SITE = 'https://bhrrealtime.pages.dev';
const MAX_PER_SLOT = 3;                  // starts for one slot, then wait for the next slot
const MAX_PER_DAY = 10;                  // starts in one New York day: a fault that repeats must not burn the month's Actions minutes
const RETRY_GAP_MS = 8 * 60000;          // after a run ends without moving the site, wait this long before the next start
// used only when run_slots.json cannot be read or lists no future slot (22 September 2026: the release-driven schedule is
// in that file; these are the common release windows, and nothing on weekends)
const WEEKDAY_TIMES = ['08:50', '09:35', '10:20', '17:05'];
const SATURDAY_TIMES = [];
const SLOT_RE = /^\d{4}-\d\d-\d\d \d\d:\d\d$/;
const ACTIVE = ['queued', 'in_progress', 'pending', 'waiting', 'requested'];
const STUCK_MS = 55 * 60000;              // longer than the job's own 50-minute limit: queued for a runner, or GitHub itself stuck
const GATE_STEP = 'check what was built before letting it out';     // the checks: a run that failed here was HELD
const NOTIFY_STEP = 'tell Anthony how the update went';   // the workflow step that sends each run's own message
// a named client: the site answers 403 to anonymous scripted user agents (Python's default, found 21 September 2026)
const HDR = { 'cache-control': 'no-cache', 'user-agent': 'bhr-dispatch' };

const FMT = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23', weekday: 'short',
});
function nyParts(date) {
  const p = {};
  for (const x of FMT.formatToParts(date)) p[x.type] = x.value;
  const hour = p.hour === '24' ? '00' : p.hour;
  return { day: `${p.year}-${p.month}-${p.day}`, hm: `${hour}:${p.minute}`,
           wd: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(p.weekday) };
}
function ny(date) { const p = nyParts(date); return `${p.day} ${p.hm}`; }
// 'YYYY-MM-DD HH:MM' in New York -> the instant (23 September 2026, collection 356): guess it as UTC, read the guess in New York,
// move by the difference; two passes settle it on either side of a clock change
function nyDate(s) {
  const target = new Date(`${s.replace(' ', 'T')}:00Z`); let t = target.getTime();
  for (let k = 0; k < 2; k++) t -= new Date(`${ny(new Date(t)).replace(' ', 'T')}:00Z`) - target;
  return new Date(t);
}
// THE DEAD-MAN (23 September 2026, collection 356; risks register R9: "no successful run in three days raises the alarm"). Whatever
// the cause - runs failing without a word, the workflow disabled, the month's minutes spent, starts that GitHub accepts and never
// runs - a site that has carried the same build for more than three days while release slots have passed since it, the newest
// more than two hours ago, has stopped updating. A holiday weekend alone never trips it: the newest missed slot must be two hours
// old, and a run takes minutes.
const DEAD_MS = 72 * 3600000, DEAD_SLOT_MS = 2 * 3600000;
function deadman(s, now) {
  if (!s.built || !s.due || s.built >= s.due) return null;
  const b = nyDate(s.built), d = nyDate(s.due);
  if (now - b <= DEAD_MS || now - d <= DEAD_SLOT_MS) return null;
  return `The site has carried the build of ${s.built} (New York) for ${Math.floor((now - b) / 3600000)} hours; the newest release slot, ${s.due}, passed ${Math.round((now - d) / 60000)} minutes ago without a build.`;
}

// the built-in slots for yesterday, today and tomorrow (New York dates)
function fallbackSlots(now) {
  const out = [];
  for (const k of [-1, 0, 1]) {
    const p = nyParts(new Date(now.getTime() + k * 86400000));
    const times = p.wd >= 1 && p.wd <= 5 ? WEEKDAY_TIMES : (p.wd === 6 ? SATURDAY_TIMES : []);
    for (const t of times) out.push(`${p.day} ${t}`);
  }
  return out.sort();
}

async function siteState(now) {
  let slots = null, built = null, source = 'run_slots.json';
  try {
    const r = await fetch(`${SITE}/run_slots.json?t=${now.getTime()}`, { headers: HDR });
    const j = JSON.parse(await r.text());            // an unknown path answers 200 with the home page: parse, never trust r.ok
    if (Array.isArray(j.slots)) slots = j.slots.map(s => s && s.ny).filter(s => SLOT_RE.test(s || ''));
    if (SLOT_RE.test(j.built_at || '')) built = j.built_at;
  } catch (e) { /* read below */ }
  if (!built) {
    try {
      const r = await fetch(`${SITE}/detector/bhs_state.json?t=${now.getTime()}`, { headers: HDR });
      const m = (await r.text()).match(/"built_at"\s*:\s*"(\d{4}-\d\d-\d\d \d\d:\d\d)"/);
      if (m) built = m[1];
    } catch (e) { /* unknown */ }
  }
  const nowNY = ny(now);
  if (!slots || !slots.some(s => s > nowNY)) { slots = fallbackSlots(now); source = 'built-in weekday times'; }
  slots = [...new Set(slots)].sort();
  const passed = slots.filter(s => s <= nowNY);
  return { now: nowNY, built, due: passed.length ? passed[passed.length - 1] : null,
           next: slots.find(s => s > nowNY) || null, source };
}

function gh(env, path, init = {}) {
  return fetch(`https://api.github.com${path}`, {
    ...init,
    headers: { 'Authorization': `Bearer ${env.GH_TOKEN}`, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'bhr-dispatch', ...(init.headers || {}) },
  });
}

async function kvGet(env, k) { try { return env.STATE ? await env.STATE.get(k) : null; } catch (e) { return null; } }
async function kvPut(env, k, v, ttl) {
  try { if (env.STATE) await env.STATE.put(k, v, ttl ? { expirationTtl: Math.max(60, ttl) } : undefined); } catch (e) { /* best effort */ }
}

async function ntfy(env, title, msg) {
  if (!env.NTFY_TOPIC) return false;
  try {
    const r = await fetch(`https://ntfy.sh/${env.NTFY_TOPIC}`, { method: 'POST', body: msg,
      headers: { 'Title': `Bristow-Hall: ${title}`, 'Priority': 'high' } });
    return r.ok;
  } catch (e) { return false; }
}

// one alert per key per ttl seconds (the key is remembered in KV); without KV, at most one an hour
async function alertOnce(env, key, ttl, title, msg, now) {
  if (env.STATE) {
    if (await kvGet(env, `alert:${key}`)) return false;
    await kvPut(env, `alert:${key}`, now.toISOString(), ttl);
  } else if (nyParts(now).hm.slice(3) >= '05') return false;
  const ok = await ntfy(env, title, msg);
  if (!ok && env.STATE) { try { await env.STATE.delete(`alert:${key}`); } catch (e) { /* next tick */ } }   // not sent: try again next tick
  return ok;
}

// did the run send its own message? If not, say what we know, once per run
async function runInfo(env, run) {
  const known = await kvGet(env, `runchk:${run.id}`);
  if (known) { try { return JSON.parse(known); } catch (e) { return { state: known }; } }
  let sent = false, ran = 0, held = false;
  try {
    const j = await (await gh(env, `/repos/${REPO}/actions/runs/${run.id}/jobs`)).json();
    for (const job of j.jobs || []) for (const st of job.steps || []) {
      if (st.name === NOTIFY_STEP && st.conclusion === 'success') sent = true;
      if (st.name === GATE_STEP && st.conclusion === 'failure') held = true;
      if (st.conclusion && st.conclusion !== 'skipped') ran++;
    }
  } catch (e) { ran = 1; /* unknown: treat as not sent */ }
  const info = { state: sent ? 'sent' : (ran ? 'silent' : 'superseded'), held, fresh: true };
  await kvPut(env, `runchk:${run.id}`, JSON.stringify({ state: info.state, held }), 7 * 86400);
  return info;
}

// did the run send its own message? If not, say what we know, once per run
async function silentRun(env, run, s, now) {
  const info = await runInfo(env, run);
  if (!info.fresh) return info;
  const sent = info.state === 'sent', ran = info.state !== 'superseded';
  // a run GitHub cancelled before any step ran (a newer start took its place in the queue) is not a failure
  if (!sent && ran)
    await ntfy(env, 'an update run ended without its own report',
      `A run (${run.event}, started ${ny(new Date(run.created_at))} New York time) ended ${run.conclusion} without sending its message: https://github.com/${REPO}/actions/runs/${run.id}. The site carries the build of ${s.built || '(unreadable)'}; ${s.built && s.due && s.built >= s.due ? 'it is current' : 'the Worker starts the next try itself'}.`);
  return info;
}

const TOKEN_HELP = "Make a new one at github.com > Settings > Developer settings > Fine-grained tokens (this repository only; Actions: Read and write) and put it in the Worker's secret GH_TOKEN (Cloudflare > Workers & Pages > bhr-dispatch > Settings > Variables and Secrets).";

async function tokenCheck(env, now) {
  // once a day (09:00 New York): is the token still accepted, and how long has it left?
  try {
    const r = await gh(env, `/repos/${REPO}`);
    if (r.status === 401 || r.status === 403 || r.status === 404) {
      await alertOnce(env, 'token-refused', 86000, "the update starter's GitHub token",
        `GitHub refuses the token the Cloudflare Worker bhr-dispatch uses to start the site's update (${r.status}). ${TOKEN_HELP}`, now);
      return `refused (${r.status})`;
    }
    const exp = r.headers.get('github-authentication-token-expiration');
    if (!exp) return 'accepted; no expiry date';
    const left = Math.floor((new Date(exp.replace(' UTC', 'Z').replace(' ', 'T')) - now) / 86400000);
    if (left <= 30)
      await alertOnce(env, 'token-expiry', 86000, "the update starter's GitHub token",
        `The GitHub token the Cloudflare Worker bhr-dispatch uses to start the site's update expires on ${exp} (${left} days). ${TOKEN_HELP}`, now);
    return `accepted; expires ${exp} (${left} days)`;
  } catch (e) { return `not checked (${e})`; }
}

// act=false (a browser opening the Worker's URL): say what would be done; nothing is started and GitHub is not called
async function decide(env, now, act) {
  const s = await siteState(now);
  const out = { ...s, token: env.GH_TOKEN ? 'set' : 'MISSING', decision: '' };
  const hm = s.now.slice(11), day = s.now.slice(0, 10);
  if (act && env.GH_TOKEN && hm >= '09:00' && hm < '09:05') out.token = await tokenCheck(env, now);
  // the site's schedule could not be read: the starter runs on its fallback times and says so, once a day
  if (act && (s.source !== 'run_slots.json' || !s.built))
    await alertOnce(env, `slotlist:${day}`, 86400, "the update starter cannot read the site's schedule",
      `The Worker could not read ${SITE}/run_slots.json (${s.built ? 'no future slot listed' : 'no build time'}); it starts runs at its fallback times (weekdays 08:50, 09:35, 10:20, 17:05 New York) until the next build publishes the list again.`, now);
  // EVERY FINISHED RUN ON MAIN IS LOOKED AT ONCE, whatever the site shows (22 September 2026, collection 306): a run that could
  // not send its own message is reported here, and a new version's run that GitHub dropped from the queue is started again
  let runs = null;
  if (act && env.GH_TOKEN) {
    const r = await gh(env, `/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?branch=main&per_page=20`);
    if (r.ok) {
      runs = (await r.json()).workflow_runs || [];
      const recent = runs.filter(x => x.status === 'completed' && now - new Date(x.updated_at) < 2 * 86400000).slice(0, 6);
      for (const run of recent) if (run.conclusion !== 'success') await silentRun(env, run, s, now);
      // A NEW VERSION'S RUN THAT GITHUB DROPPED FROM ITS QUEUE (a newer start took its place before any step ran) is started
      // again, unless a later run has already done the work: every run checks out main as it stands, so a later run that
      // sent its own message ran the new code. The newest push is looked at, not only the newest run (a GitHub firing that
      // found the site current can be newer than the dropped push).
      const active0 = runs.find(x => ACTIVE.includes(x.status));
      const push = runs.find(x => x.event === 'push');
      if (push && !active0 && push.status === 'completed' && push.conclusion === 'cancelled' && !(await kvGet(env, `pushrec:${push.id}`))) {
        const info = await runInfo(env, push);
        if (info.state === 'superseded') {
          let covered = null;
          for (const x of runs) {                          // newest first: only the runs created after the push
            if (x.id === push.id) break;
            if (x.status === 'completed' && (await runInfo(env, x)).state === 'sent') { covered = x; break; }
          }
          if (covered) {
            await kvPut(env, `pushrec:${push.id}`, `covered by run ${covered.id}`, 7 * 86400);
          } else {
            const d0 = await gh(env, `/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ref: 'main', inputs: { mode: 'full', origin: 'push-recovery', slot: '' } }) });
            if (d0.status === 204) {
              await kvPut(env, `pushrec:${push.id}`, now.toISOString(), 7 * 86400);
              out.decision = `a new version's run was dropped from GitHub's queue; started it again`;
              return out;
            }
            // refused: the next tick tries again, and the slot logic below still runs (and alerts if a slot cannot be started)
            out.restart_refused = `a new version's run was dropped from GitHub's queue; starting it again was refused (${d0.status})`;
          }
        }
      }
    } else {
      await alertOnce(env, `gh-list-${r.status}`, 3500, 'the update starter cannot reach GitHub',
        `GitHub answered ${r.status} to the list of runs. The Worker tries again every five minutes; GitHub's own schedule is the second line.`, now);
    }
  }
  if (!s.due) { out.decision = 'no slot has passed in the listed window'; return out; }
  if (s.built && s.built >= s.due) { out.decision = `current: the site carries the build of ${s.built}, after the ${s.due} slot`; return out; }
  const behind = `behind: the site carries the build of ${s.built || '(unreadable)'}, before the ${s.due} slot`;
  const dm = deadman(s, now);
  if (dm) {
    out.deadman = dm;
    if (act) await alertOnce(env, `deadman:${day}`, 86400, 'the site has stopped updating',
      `${dm} The Worker keeps starting runs every five minutes; GitHub's own schedule is the second line. Runs: https://github.com/${REPO}/actions . Status: https://bhr-dispatch.anthonythomashall3.workers.dev`, now);
  }
  if (!env.GH_TOKEN) { out.decision = `${behind}; no GitHub token is set, so nothing can be started from here`; return out; }
  if (!act) { out.decision = `${behind}; the next five-minute check starts a run unless one is under way`; return out; }
  if (runs === null) { out.decision = `${behind}; the list of runs could not be read`; return out; }
  const active = runs.find(x => ACTIVE.includes(x.status));
  if (active) {
    out.decision = `${behind}; a run is under way (${active.status}, started ${ny(new Date(active.created_at))})`;
    const age = now - new Date(active.run_started_at || active.created_at);
    if (age > STUCK_MS)
      await alertOnce(env, `stuck:${active.id}`, 86400, 'an update run is stuck',
        `The run started ${ny(new Date(active.created_at))} New York time has been ${active.status} for ${Math.round(age / 60000)} minutes (they take 2-4; GitHub stops a run at 50). The site still carries the build of ${s.built || '(unreadable)'}. https://github.com/${REPO}/actions/runs/${active.id}`, now);
    return out;
  }
  // the runs that tried this slot, newest first; a GitHub firing that found nothing to do is not a try (it ends "success"
  // at once, and a run that did the work and succeeded would have brought the site past the slot)
  const since = runs.filter(x => ny(new Date(x.created_at)) >= s.due && !(x.event === 'schedule' && x.conclusion === 'success'));
  // a run the checks HELD is not started again for the same slot: the same data would be held again (the run sent its own
  // message); the next slot, or a fix, moves it on
  if (since.length && since[0].conclusion !== 'success') {
    const info = await runInfo(env, since[0]);
    if (info.held) { out.decision = `${behind}; the checks held the run for this slot - waiting for the next slot (${s.next})`; return out; }
  }
  if (since.length >= MAX_PER_SLOT) {
    out.decision = `${behind}; ${since.length} runs since the slot have not brought the site past it - waiting for the next slot (${s.next})`;
    await alertOnce(env, `gaveup:${s.due}`, 86400, 'the update did not reach the site',
      `${out.decision}. Each run sent its own message; the last: https://github.com/${REPO}/actions/runs/${since[0].id} (${since[0].conclusion}). The site still carries the build of ${s.built || '(unreadable)'}.`, now);
    return out;
  }
  if (since.length) {
    const retryAt = new Date(new Date(since[0].updated_at).getTime() + RETRY_GAP_MS);
    if (now < retryAt) { out.decision = `${behind}; the run for this slot ended ${since[0].conclusion}; the next start is due after ${ny(retryAt)}`; return out; }
  }
  const started = parseInt(await kvGet(env, `starts:${day}`) || '0', 10);
  if (started >= MAX_PER_DAY) {
    out.decision = `${behind}; ${started} starts today already - no more until tomorrow (a fault that repeats must not use up the month's minutes)`;
    await alertOnce(env, `daycap:${day}`, 86400, 'the update starter stopped for today',
      `${out.decision}. Every run sent its own message; the last: https://github.com/${REPO}/actions/runs/${(since[0] || runs[0] || {}).id}. A push to main, or a run started by hand, still goes.`, now);
    return out;
  }
  const d = await gh(env, `/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ref: 'main', inputs: { mode: 'full', origin: 'slot', slot: s.due } }),
  });
  if (d.status === 204) {
    await kvPut(env, `starts:${day}`, String(started + 1), 2 * 86400);
    out.decision = `${behind}; started a run for the ${s.due} slot (start ${since.length + 1} of ${MAX_PER_SLOT})`;
    return out;
  }
  out.decision = `${behind}; GitHub refused to start the run: ${d.status} ${(await d.text()).slice(0, 200)}`;
  // once per slot and status: the next five-minute check tries again by itself, and GitHub's own schedule is the second line
  await alertOnce(env, `dispatch-${d.status}:${s.due}`, 86400, 'the update could not be started',
    `${out.decision}. The Worker keeps trying every five minutes and GitHub's own schedule is the second line.`, now);
  return out;
}

export default {
  async scheduled(event, env, ctx) {
    const now = new Date(event.scheduledTime);
    ctx.waitUntil(decide(env, now, true)
      .catch(async e => {   // v3.67 (22 September 2026, collection 295): a crash of the starter is alerted, once in six hours, not only logged
        const msg = `ERROR ${String(e && e.stack || e).slice(0, 500)}`;
        try { await alertOnce(env, `worker-error:${ny(now).slice(0, 10)}`, 21600, 'the update starter crashed', msg, now); } catch (e2) { /* best effort */ }
        return { now: ny(now), decision: msg };
      })
      .then(async o => {
        o.tick_utc = new Date().toISOString();
        console.log(JSON.stringify(o));
        await kvPut(env, 'last_tick', JSON.stringify(o));       // the heartbeat the status page, the Mac and the workflow read
      }));
  },
  async fetch(request, env) {
    // ?simulate_now=<ISO time> (23 September 2026, collection 356): the drill for the dead-man and the slot logic - what the
    // Worker would decide at that moment on the site as it stands; like every page view it starts nothing and sends nothing
    let sim = null;
    try { sim = new URL(request.url).searchParams.get('simulate_now'); } catch (e) { sim = null; }
    const when = sim && !isNaN(Date.parse(sim)) ? new Date(sim) : new Date();
    const o = await decide(env, when, false);
    if (sim) o.simulated_now = when.toISOString();
    let last = null, age = null;
    try { last = JSON.parse(await kvGet(env, 'last_tick')); age = Math.round((Date.now() - Date.parse(last.tick_utc)) / 60000); } catch (e) { /* none yet */ }
    return new Response(JSON.stringify({ worker: 'bhr-dispatch', version: VERSION, what: 'starts the Bristow-Hall update at the release slots', ...o,
      last_tick: last, last_tick_minutes_ago: age, heartbeat: age === null ? 'none recorded yet' : (age <= 15 ? 'ok' : 'LATE') }, null, 1),
      { headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
  },
};
