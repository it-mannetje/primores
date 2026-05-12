/* ═══════════════════════════════════════════════════════
   Canon Primores — Tijdlijn renderer
   ═══════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const START_YEAR   = 1975;
  const END_YEAR     = 2027;
  const CARD_W       = 152;
  const CARD_GAP     = 6;
  const LANE_H_P     = 200;   // Primores lane height
  const LANE_H       = 165;   // person lane height
  const ROW_H        = 155;   // height per event row within a lane
  const RULER_H      = 36;
  const LEFT_PAD     = 16;

  const MONTHS_NL = ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec'];
  const MONTHS_LONG = ['januari','februari','maart','april','mei','juni',
                       'juli','augustus','september','oktober','november','december'];

  let pxPerYear = 110;
  let allEvents = [];
  let visiblePersons = new Set(['all']);
  let membersWithEvents = new Set();

  // ── DOM refs ──────────────────────────────────────────
  const tlScroll  = document.getElementById('tlScroll');
  const tlLabels  = document.getElementById('tlLabels');
  const tlRuler   = document.getElementById('tlRuler');
  const tlCanvas  = document.getElementById('tlCanvas');
  const tlScrubber   = document.getElementById('tlScrubber');
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

    // Primores events
    const primoresEvs = allEvents.filter(e => e.is_primores).sort(sortByDate);
    assignRows(primoresEvs);

    // All person events visible under current filter, laid out as one flat pool
    const personEvs = allEvents
      .filter(e => !e.is_primores && membersWithEvents.has(e.person_name))
      .filter(e => visiblePersons.has('all') || visiblePersons.has(e.person_name))
      .sort(sortByDate);
    assignRows(personEvs);

    const primH   = laneHeight(primoresEvs, LANE_H_P, ROW_H);
    const personH = laneHeight(personEvs, LANE_H, ROW_H);
    const primoresHidden = !visiblePersons.has('all') && !visiblePersons.has('primores');
    const totalH  = (primoresHidden ? 0 : primH) + (personEvs.length ? personH : 0);

    tlCanvas.style.width  = w + 'px';
    tlCanvas.style.height = Math.max(totalH, LANE_H) + 'px';

    buildRuler();
    buildGridlines(Math.max(totalH, LANE_H));

    // Render Primores lane
    const primLane = document.getElementById('lane-Primores');
    primLane.style.width   = w + 'px';
    primLane.style.height  = primH + 'px';
    primLane.style.display = primoresHidden ? 'none' : '';
    primLane.innerHTML = '';
    primoresEvs.forEach(ev => primLane.appendChild(makeCard(ev, true)));

    // Render all person events in one flat lane
    const flatLane = document.getElementById('lane-flat');
    flatLane.style.width   = w + 'px';
    flatLane.style.height  = personH + 'px';
    flatLane.style.display = personEvs.length ? '' : 'none';
    flatLane.innerHTML = '';
    personEvs.forEach(ev => flatLane.appendChild(makeCard(ev, false)));

    syncLabelScroll();
    buildScrubber();
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
    const avatarInner = ev.avatar_url
      ? `<img src="${ev.avatar_url}" alt="${ev.person_name}">`
      : ev.person_name[0];

    card.innerHTML = `
      <div class="tl-corner-avatar" style="--mc:${ev.color}">${avatarInner}</div>
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
      <div class="modal-date">${ev.location_name ? `📍 ${ev.location_name} &nbsp;·&nbsp; ` : ''}${dateStr}</div>
      ${ev.photo_url ? `<img class="modal-photo" src="${ev.photo_url}" alt="${ev.title}">` : ''}
      ${ev.description ? `<p class="modal-desc">${ev.description.replace(/\n/g,'<br>')}</p>` : ''}
      ${ev.url ? `<a class="modal-url" href="${ev.url}" target="_blank" rel="noopener noreferrer">🔗 Meer informatie</a>` : ''}
    `;
    modal.hidden = false;
    document.getElementById('modalClose').focus();
  }

  function closeModal() { modal.hidden = true; }

  modalClose.addEventListener('click', closeModal);
  modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  // ── Scrubber / mini-map navigator ────────────────────

  function buildScrubber() {
    const W = tlScrubber.clientWidth;
    if (W === 0) return;
    const tW = totalWidth();

    tlScrubber.innerHTML = '';

    // Decade / 5-year ticks + labels
    for (let y = START_YEAR; y <= END_YEAR; y++) {
      if (y % 5 !== 0) continue;
      const x = dateToX(y, null, null) / tW * W;
      const isDec = y % 10 === 0;

      const tick = document.createElement('div');
      tick.className = 'tl-scrub-tick' + (isDec ? ' tl-scrub-tick--decade' : '');
      tick.style.left = x + 'px';
      tlScrubber.appendChild(tick);

      if (isDec || (y % 5 === 0 && pxPerYear >= 80)) {
        const lbl = document.createElement('span');
        lbl.className = 'tl-scrub-label';
        lbl.style.left = x + 'px';
        lbl.textContent = y;
        tlScrubber.appendChild(lbl);
      }
    }

    // Event dots — one dot per event, colored by person
    allEvents.forEach(ev => {
      const x = dateToX(ev.date_year, ev.date_month, ev.date_day) / tW * W;
      const dot = document.createElement('div');
      dot.className = 'tl-scrub-dot';
      dot.style.left = x + 'px';
      dot.style.background = ev.is_primores ? '#B91C1C' : ev.color;
      tlScrubber.appendChild(dot);
    });

    // Viewport indicator (added last so it sits on top)
    const vp = document.createElement('div');
    vp.className = 'tl-scrub-viewport';
    tlScrubber.appendChild(vp);
    updateScrubberViewport();
  }

  function updateScrubberViewport() {
    const vp = tlScrubber.querySelector('.tl-scrub-viewport');
    if (!vp) return;
    const W  = tlScrubber.clientWidth;
    const tW = totalWidth();
    const left  = tlScroll.scrollLeft / tW * W;
    const width = Math.min(tlScroll.clientWidth / tW * W, W);
    vp.style.left  = left + 'px';
    vp.style.width = width + 'px';
  }

  // Click or drag to navigate
  (function () {
    let dragging = false;

    function scrubTo(clientX) {
      const rect  = tlScrubber.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      tlScroll.scrollLeft = ratio * totalWidth() - tlScroll.clientWidth / 2;
    }

    tlScrubber.addEventListener('mousedown', e => {
      dragging = true;
      scrubTo(e.clientX);
    });
    document.addEventListener('mousemove', e => {
      if (dragging) scrubTo(e.clientX);
    });
    document.addEventListener('mouseup', () => { dragging = false; });

    // Touch support
    tlScrubber.addEventListener('touchstart', e => {
      dragging = true;
      scrubTo(e.touches[0].clientX);
    }, { passive: true });
    document.addEventListener('touchmove', e => {
      if (dragging) scrubTo(e.touches[0].clientX);
    }, { passive: true });
    document.addEventListener('touchend', () => { dragging = false; });
  })();

  window.addEventListener('resize', () => { buildScrubber(); });

  // ── Scroll sync (labels ↔ timeline) ───────────────────

  function syncLabelScroll() {
    if (tlLabels) tlLabels.scrollTop = tlScroll.scrollTop;
  }

  tlScroll.addEventListener('scroll', () => {
    if (tlLabels) tlLabels.scrollTop = tlScroll.scrollTop;
    updateScrubberViewport();
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

  // ── Avatar filter ─────────────────────────────────────

  function updateAvatarStates() {
    document.querySelectorAll('.avatar-chip').forEach(chip => {
      const person = chip.dataset.person;
      const active = visiblePersons.has('all') || visiblePersons.has(person);
      chip.classList.toggle('active',   active);
      chip.classList.toggle('inactive', !active);
    });
  }

  document.getElementById('avatarFilter').addEventListener('click', e => {
    const chip = e.target.closest('.avatar-chip');
    if (!chip) return;
    const person = chip.dataset.person;

    if (person === 'all') {
      visiblePersons = new Set(['all']);
    } else {
      if (visiblePersons.has('all')) {
        // First individual toggle: make explicit set of everyone, then remove clicked
        visiblePersons = new Set([...MEMBERS.map(m => m.name), 'primores']);
        visiblePersons.delete(person);
      } else {
        if (visiblePersons.has(person)) visiblePersons.delete(person);
        else visiblePersons.add(person);
        if (visiblePersons.size === 0) visiblePersons = new Set(['all']);
      }
    }

    updateAvatarStates();
    render();
  });

  // ── Scroll to current era ─────────────────────────────

  function scrollToYear(year) {
    const x = dateToX(year, null, null);
    tlScroll.scrollLeft = Math.max(0, x - tlScroll.clientWidth / 2);
  }



  // ── Load & init ───────────────────────────────────────

  fetch('/api/events')
    .then(r => r.json())
    .then(data => {
      allEvents = data;
      membersWithEvents = new Set(allEvents.filter(e => !e.is_primores).map(e => e.person_name));
      document.querySelectorAll('.avatar-chip[data-person]').forEach(chip => {
        const p = chip.dataset.person;
        if (p !== 'all' && p !== 'primores' && !membersWithEvents.has(p)) {
          chip.style.display = 'none';
        }
      });
      render();
      // Scroll to show earliest event or ~1990
      const minYear = allEvents.length
        ? Math.min(...allEvents.map(e => e.date_year))
        : 1990;
      scrollToYear(Math.max(minYear - 2, START_YEAR));
    })
    .catch(err => console.error('Kon evenementen niet laden:', err));

})();
