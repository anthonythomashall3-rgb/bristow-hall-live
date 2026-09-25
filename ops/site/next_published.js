/* THE NEXT-PUBLISHED DAYS ROLL FORWARD BY THEMSELVES (ops/site/next_published.js; 22 September 2026, collection 306).
   Anthony: "if new data is supposed to come sep 27, and then sep 27 passes and its data has been updated, then it should
   say the next time the data updates". The site is built at the release slots, and a day it prints as "next" can pass
   before the next build. This reads /ops/release_calendar.json (written at every update run by ops/calendar_build.py
   from FRED's release calendars and the agencies' clock times) and, by the reader's own clock:
     - on the data page, a "Next published" day that has gone by becomes the next scheduled release, with its time (ET);
     - on the front page, each reading's "next release" does the same;
     - the data page says when the site next updates itself (from /run_slots.json).
   It never replaces a day the build gave that is still ahead (it only adds that day's clock time). If anything fails,
   the page stays exactly as it was built. */
(function () {
  'use strict';
  if (!window.fetch || !window.Intl) return;
  var TZ = 'America/New_York';
  var FD = new Intl.DateTimeFormat('en-US', {timeZone: TZ, month: 'short', day: 'numeric', year: 'numeric'});
  var FW = new Intl.DateTimeFormat('en-US', {timeZone: TZ, weekday: 'short', month: 'short', day: 'numeric'});
  var FT = new Intl.DateTimeFormat('en-US', {timeZone: TZ, hour: 'numeric', minute: '2-digit'});
  var FI = new Intl.DateTimeFormat('en-CA', {timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit'});
  var FH = new Intl.DateTimeFormat('en-GB', {timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'});
  function norm(s) { return String(s || '').toLowerCase().replace(/\s+/g, ' ').trim(); }
  function nyDay(ms) { return FI.format(new Date(ms)); }
  function nyStamp(ms) { return nyDay(ms) + ' ' + FH.format(new Date(ms)); }
  function label(t, known, tnote) {
    var d = new Date(Date.parse(t.utc));
    // the day and the clock time only; whose hour it is stays in the calendar file, not on the page (Anthony, 22 September
    // 2026: "DONT INCLUDE ANY WORDS AND JUST GIVE US THE TIME")
    return FD.format(d) + (known ? ', ' + FT.format(d) + ' ET' : '') + (t.expected ? ' (expected)' : '');
  }
  // the data page's cell: the day as the build prints it, the clock time on a second line in the page's small grey
  function fill(cell, t, known, note, tnote) {
    var d = new Date(Date.parse(t.utc));
    cell.textContent = FD.format(d);
    var bits = [];
    if (known) bits.push(FT.format(d) + ' ET');
    // whose hour it is (the market close, a morning we read at, a derived series) is NOT printed: the cell carries the day
    // and the clock time only (Anthony, 22 September 2026); the calendar file keeps time_note for the record
    // "expected": past the last day the agency has published, projected from its own pattern; it becomes the agency's day
    // as soon as FRED lists it (the calendar is rebuilt at every update)
    if (t.expected) bits.push('expected');
    if (note) bits.push(note);
    if (bits.length) {
      var u = document.createElement('div');
      u.className = 'u';
      u.textContent = bits.join(', ');
      cell.appendChild(u);
    }
  }
  // the entry to show for a row, or null to leave the build's text as it is. Adds .note when the last release is not on
  // the site yet: the agency has not posted it (the update's own check says so), or the site has not updated since.
  function choose(r, buildDay, now, builtAt) {
    var times = r.times || [], nxt = null, prev = null, i;
    for (i = 0; i < times.length; i++) {
      if (Date.parse(times[i].utc) > now) { if (!nxt) nxt = times[i]; } else prev = times[i];
    }
    // audit-0924 (24 Sep 2026; Anthony: the day it is next published, exact dates only, no sentences): a release that has
    // gone by is never shown as due or pending - the next one is. A late feed is the checks' business, not the page's.
    if (!nxt) return null;
    var today = nyDay(now), passedToday = false;
    for (i = 0; i < times.length; i++) {
      if (times[i].ny.slice(0, 10) === today && Date.parse(times[i].utc) <= now) passedToday = true;
    }
    if (!buildDay || buildDay < today || (buildDay === today && passedToday)) return { t: nxt };   // the build's day has gone by
    if (buildDay === nxt.ny.slice(0, 10)) return { t: nxt };                                        // the same day: add its time
    if (!nxt.expected && nxt.ny.slice(0, 10) < buildDay) return { t: nxt };      // the agency's own nearer day wins over the build's
    for (i = 0; i < times.length; i++) { if (times[i].ny.slice(0, 10) === buildDay) return { t: times[i] }; }
    return null;                                                                          // the build knows a later day
  }
  function get(url) {
    return fetch(url + (url.indexOf('?') < 0 ? '?' : '&') + 't=' + Date.now(), {cache: 'no-store'})
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  var now = Date.now();
  get('/ops/release_calendar.json').then(function (cal) {
    var byIds = {};
    (cal.rows || []).forEach(function (r) { byIds[norm(r.ids)] = r; });
    // the data page
    var tb = document.getElementById('dtab');
    if (tb && tb.tHead && tb.tBodies.length) {
      // the values' long unit lines may wrap, so the table fits a laptop screen and "Next published" is not cut off
      var css = document.createElement('style');
      css.textContent = '#dtab .v{white-space:normal}';
      document.head.appendChild(css);
      var ths = tb.tHead.querySelectorAll('th'), col = -1, i;
      for (i = 0; i < ths.length; i++) { if (ths[i].getAttribute('data-k') === 'next') col = i; }
      if (col >= 0) {
        Array.prototype.forEach.call(tb.tBodies[0].rows, function (tr) {
          var r = byIds[norm(tr.getAttribute('data-ids'))];
          if (!r || !tr.cells[col]) return;
          var pick = choose(r, tr.getAttribute('data-next') || '', now, cal.built_at);
          if (!pick) return;
          fill(tr.cells[col], pick.t, r.time_known, pick.note, r.time_note);
          tr.cells[col].title = 'Scheduled: ' + (r.source || '') + '. Updated by your clock: the next release after now.';
          tr.setAttribute('data-next', pick.t.ny.slice(0, 10));
        });
      }
    }
    // the front page's readings: the first tile is the indicator, the rest follow H.tiles in order
    try {
      var tiles = document.querySelectorAll('#tiles .tile');
      /* global H */
      var HT = (typeof H !== 'undefined' && H && H.tiles) ? H.tiles : null;
      if (HT && tiles.length === HT.length + 1) {
        HT.forEach(function (t, k) {
          var r = byIds[norm(t.sid)];
          var sub = tiles[k + 1].querySelector('.sub');
          if (!r || !sub || !t.next) return;
          var pick = choose(r, t.next, now, cal.built_at);
          if (!pick) return;
          var lab = label(pick.t, r.time_known, r.time_note), note = pick.note || '';
          sub.textContent = String(t.sub || '') + '; next release ' + lab;
        });
      }
    } catch (e) { /* the front page stays as built */ }
  }).catch(function () { /* the page stays as built */ });
  // audit-0924 (24 Sep 2026): no 'This page updates itself...' sentence on the data page (Anthony: no explanatory sentences)
  var leg = null;
  if (leg) {
    get('/run_slots.json').then(function (rs) {
      var stamp = nyStamp(now), next = null, i, s = rs.slots || [];
      for (i = 0; i < s.length; i++) { if (s[i].ny > stamp) { next = s[i]; break; } }
      if (!next) return;
      var t = Date.parse(next.utc), day = nyDay(t) === nyDay(now) ? 'today' : FW.format(new Date(t));
      var p = document.createElement('p');
      p.className = 'dleg';
      p.id = 'ops-next-update';
      p.textContent = 'This page updates itself after each release. Next update: ' + day + ', ' + FT.format(new Date(t)) +
        ' ET' + (rs.built_at ? ' (the page now carries the build of ' + rs.built_at + ' ET).' : '.');
      leg.parentNode.insertBefore(p, leg.nextSibling);
    }).catch(function () { /* nothing to add */ });
  }
})();
