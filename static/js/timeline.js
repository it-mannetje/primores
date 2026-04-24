/* ═══════════════════════════════════════════════════════
   Canon Primores — Tijdlijn renderer
   ═══════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const START_YEAR   = 1975;
  const END_YEAR     = 2027;
  const CARD_W       = 152;
  const CARD_GAP     = 6;
  const LANE_H_P     = 160;   // Primores lane height
  const LANE_H       = 130;   // person lane height
  const ROW_H        = 116;   // height per event row within a lane
  const RULER_H      = 36;
  const LEFT_PAD     = 16;

  const MONTHS_NL = ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec'];
  const MONTHS_LONG = ['januari','februari','maart','april','mei','juni',
                       'juli','augustus','september','oktober','november','december'];

  let pxPerYear = 110;
  let allEvents = [];
  let visiblePersons = new Set(['all']);

  // ── DOM refs ──────────────────────────────────────────
  const tlScroll  = document.getElementById('tlScroll');
  const tlLabels  = document.getElementById('tlLabels');
  const tlRuler   = document.getElementById('tlRuler');
  const tlCanvas  = document.getElementById('tlCanvas');
  const modal     = document.getElementById('eventModal');
  const modalContent = document.getElementById('modalContent');
  const modalClose   = document.getElementById('modalClose');

  // ── Utilities ─────────────────────────────────────────

  function dateToX(year, month, day) {
    const y = (year  - START_YEAR);
    const m = month ? (month - 1) / 12 : 0;
    const d = day   ? (day - 1)   / 365 : 0;
    return LEFT_PAD + (y + m + d) * pxPerYear;
  }

  function totalWidth() {
    return LEFT_PAD + (END_YEAR - START_YEAR + 1) * pxPerYear + LEFT_PAD;
  }

  function formatDate(year, month, day) {
    let s = String(year);
    if (month) s = MONTHS_LONG[month - 1] + ' ' + s;
    if (day)   s = day + ' ' + s;
    return s;
  }

  function formatShortDate(year, month, day) {
    let s = String(year);
    if (month) s = MONTHS_NL[month - 1] + ' ' + s;
    if (day)   s = day + ' ' + s;
    return s;
  }

  // ── Row assignment (collision avoidance) ──────────────

  function assignRows(events) {
    const rows = [];  // rows[r] = last occupied endX
    for (const ev of events) {
      const x = dateToX(ev.date_year, ev.date_month, ev.date_day);
      let row = rows.findIndex(endX => x >= endX + CARD_GAP);
      if (row === -1) { row = rows.length; rows.push(0); }
      rows[row] = x + CARD_W;
      ev._x   = x;
      ev._row = row;
    }
    return events;
  }

  // ── Ruler ─────────────────────────────────────────────

  function buildRuler() {
    tlRuler.innerHTML = '';
    tlRuler.style.width = totalWidth() + 'px';

    for (let y = START_YEAR; y <= END_YEAR; y++) {
      const x = dateToX(y, null, null);
      const isDec  = y % 10 === 0;
      const is5    = y % 5  === 0;
      const cls    = isDec ? 'decade' : is5 ? '5year' : 'year';
      const showLbl = isDec || (is5 && pxPerYear >= 70) || (pxPerYear >= 130);

      const tick = document.createElement('div');
      tick.className = `ruler-tick ruler-tick--${cls}`;
      tick.style.left = x + 'px';

      const line = document.createElement('div');
      line.className = 'ruler-line';
      tick.appendChild(line);

      if (showLbl || isDec) {
        const lbl = document.createElement('span');
        lbl.className = 'ruler-tick-label';
        lbl.textContent = y;
        tick.appendChild(lbl);
      }

      tlRuler.appendChild(tick);
    }
  }

  // ── Gridlines on canvas ───────────────────────────────

  function buildGridlines(canvasH) {
    document.querySelectorAll('.tl-gridline').forEach(el => el.remove());

    for (let y = START_YEAR; y <= END_YEAR; y++) {
      const x = dateToX(y, null, null);
      const isDec = y % 10 === 0;
      const is5   = y % 5  === 0;
      if (!isDec && !is5 && pxPerYear < 50) continue;
      const cls = isDec ? 'decade' : is5 ? '5year' : 'year';

      const line = document.createElement('div');
      line.className = `tl-gridline tl-gridline--${cls}`;
      line.style.cssText = `left:${x}px; height:${canvasH}px;`;
      tlCanvas.appendChild(line);
    }
  }

  // ── Lane height calculation ────────────────────────────

  function laneHeight(events, baseH, rowH) {
    if (!events.length) return baseH;
    const maxRow = Math.max(...events.map(e => e._row));
    return Math.max(baseH, (maxRow + 1) * rowH + 10);
  }

  // ── Render all lanes ──────────────────────────────────

  function render() {
    const w = totalWidth();

    // Group events
    const primoresEvs = allEvents
      .filter(e => e.is_primores)
      .sort(sortByDate);
    const byPerson = {};
    MEMBERS.forEach(m => byPerson[m.name] = []);
    allEvents.filter(e => !e.is_primores).forEach(e => {
      if (byPerson[e.person_name]) byPerson[e.person_name].push(e);
    });

    assignRows(primoresEvs);
    MEMBERS.forEach(m => assignRows(byPerson[m.name]));

    // Compute total canvas height
    let totalH = laneHeight(primoresEvs, LANE_H_P, ROW_H);
    MEMBERS.forEach(m => {
      totalH += laneHeight(byPerson[m.name], LANE_H, ROW_H);
    });

    tlCanvas.style.width  = w + 'px';
    tlCanvas.style.height = totalH + 'px';

    buildRuler();
    buildGridlines(totalH);

    // Render Primores lane
    const primLane = document.getElementById('lane-Primores');
    const primH = laneHeight(primoresEvs, LANE_H_P, ROW_H);
    primLane.style.width  = w + 'px';
    primLane.style.height = primH + 'px';
    primLane.innerHTML = '';
    primoresEvs.forEach(ev => primLane.appendChild(makeCard(ev, true)));

    // Render person lanes
    let labelIdx = 1; // 0 = primores label
    MEMBERS.forEach((m, i) => {
      const laneEl = document.getElementById('lane-' + m.name.replace(/ /g, '_'));
      const events = byPerson[m.name];
      const h = laneHeight(events, LANE_H, ROW_H);

      laneEl.style.width  = w + 'px';
      laneEl.style.height = h + 'px';
      laneEl.innerHTML    = '';

      const hidden = !visiblePersons.has('all') && !visiblePersons.has(m.name);
      laneEl.style.opacity = hidden ? '.25' : '1';

      events.forEach(ev => laneEl.appendChild(makeCard(ev, false)));

      // Sync label height
      const lblEls = tlLabels.querySelectorAll('.tl-label');
      if (lblEls[i + 1]) {
        lblEls[i + 1].style.height = h + 'px';
      }
    });

    // Sync Primores label height
    const priLbl = tlLabels.querySelector('.tl-label--primores');
    if (priLbl) priLbl.style.height = primH + 'px';

    // Sync scroll
    syncLabelScroll();
  }

  function sortByDate(a, b) {
    if (a.date_year  !== b.date_year)                 return a.date_year  - b.date_year;
    if ((a.date_month||0) !== (b.date_month||0))      return (a.date_month||0) - (b.date_month||0);
    return (a.date_day||0) - (b.date_day||0);
  }

  // ── Make event card ───────────────────────────────────

  function makeCard(ev, isPrimores) {
    const top  = ev._row * ROW_H + 8;
    const card = document.createElement('div');
    card.className = isPrimores ? 'tl-event tl-event--primores' : 'tl-event';
    card.style.cssText = `left:${ev._x}px; top:${top}px; --mc:${ev.color}`;
    card.setAttribute('tabindex', '0');
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', ev.title);

    const dateStr = formatShortDate(ev.date_year, ev.date_month, ev.date_day);

    card.innerHTML = `
      <div class="tl-event-date">${dateStr}</div>
      ${ev.photo_url ? `<img class="tl-event-img" src="${ev.photo_url}" alt="" loading="lazy">` : ''}
      <div class="tl-event-title">${ev.title}</div>
    `;

    card.addEventListener('click',  () => openModal(ev));
    card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') openModal(ev); });
    return card;
  }

  // ── Modal ─────────────────────────────────────────────

  function openModal(ev) {
    const dateStr = formatDate(ev.date_year, ev.date_month, ev.date_day);
    modalContent.innerHTML = `
      <div class="modal-person" style="color:${ev.color}">${ev.person_name}</div>
      <h2 class="modal-title">${ev.title}</h2>
      <div class="modal-date">${dateStr}</div>
      ${ev.photo_url ? `<img class="modal-photo" src="${ev.photo_url}" alt="${ev.title}">` : ''}
      ${ev.description ? `<p class="modal-desc">${ev.description.replace(/\n/g,'<br>')}</p>` : ''}
    `;
    modal.hidden = false;
    document.getElementById('modalClose').focus();
  }

  function closeModal() { modal.hidden = true; }

  modalClose.addEventListener('click', closeModal);
  modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  // ── Scroll sync (labels ↔ timeline) ───────────────────

  function syncLabelScroll() {
    tlLabels.scrollTop = tlScroll.scrollTop;
  }

  tlScroll.addEventListener('scroll', () => {
    tlLabels.scrollTop = tlScroll.scrollTop;
  });

  // ── Zoom ──────────────────────────────────────────────

  document.getElementById('zoomIn').addEventListener('click', () => {
    pxPerYear = Math.min(pxPerYear * 1.3, 600);
    render();
  });

  document.getElementById('zoomOut').addEventListener('click', () => {
    pxPerYear = Math.max(pxPerYear / 1.3, 30);
    render();
  });

  document.getElementById('zoomReset').addEventListener('click', () => {
    pxPerYear = 110;
    render();
  });

  // ── Person filters ────────────────────────────────────

  document.getElementById('personFilters').addEventListener('click', e => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    const person = btn.dataset.person;

    if (person === 'all') {
      visiblePersons = new Set(['all']);
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    } else if (person === 'primores') {
      visiblePersons = new Set(['primores']);
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    } else {
      document.querySelector('[data-person="all"]').classList.remove('active');
      document.querySelector('[data-person="primores"]').classList.remove('active');
      if (visiblePersons.has('all') || visiblePersons.has('primores')) {
        visiblePersons = new Set([person]);
      } else {
        if (visiblePersons.has(person)) visiblePersons.delete(person);
        else visiblePersons.add(person);
      }
      btn.classList.toggle('active', visiblePersons.has(person));
      if (visiblePersons.size === 0) {
        visiblePersons.add('all');
        document.querySelector('[data-person="all"]').classList.add('active');
      }
    }
    render();
  });

  // ── Scroll to current era ─────────────────────────────

  function scrollToYear(year) {
    const x = dateToX(year, null, null);
    tlScroll.scrollLeft = Math.max(0, x - 120);
  }

  // ── Load & init ───────────────────────────────────────

  fetch('/api/events')
    .then(r => r.json())
    .then(data => {
      allEvents = data;
      render();
      // Scroll to show earliest event or ~1990
      const minYear = allEvents.length
        ? Math.min(...allEvents.map(e => e.date_year))
        : 1990;
      scrollToYear(Math.max(minYear - 2, START_YEAR));
    })
    .catch(err => console.error('Kon evenementen niet laden:', err));

})();
