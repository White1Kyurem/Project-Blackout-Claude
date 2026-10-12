/* ==========================================================================
   Project Blackout PVP – interactions (shared by all pages)
   ========================================================================== */
(() => {
  'use strict';

  const cfg = Object.assign(
    {
      ip: '', port: '', map: '', maxPlayers: '', discord: '',
      restartTimes: [], timezone: '', mods: [], battlemetricsId: '',
    },
    window.BLACKOUT_CONFIG || {}
  );
  const address = cfg.port ? `${cfg.ip}:${cfg.port}` : cfg.ip;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const hasValue = (v) => (Array.isArray(v) ? v.length > 0 : v !== undefined && v !== null && v !== '');

  /* ---------- Write config values into the page ---------- */
  const values = { ...cfg, address };
  $$('[data-cfg]').forEach((el) => {
    const value = values[el.dataset.cfg];
    if (hasValue(value)) el.textContent = value;
  });
  $$('[data-cfg-href]').forEach((el) => {
    const value = values[el.dataset.cfgHref];
    if (value) el.href = value;
  });
  $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });

  // blocks that only make sense when a config value is set (hidden in the HTML by default)
  $$('[data-requires]').forEach((el) => {
    el.hidden = !hasValue(cfg[el.dataset.requires]);
  });
  // …and fallbacks that are only needed while a value is missing
  $$('[data-unless]').forEach((el) => {
    el.hidden = hasValue(cfg[el.dataset.unless]);
  });

  $$('[data-players]').forEach((el) => {
    if (cfg.maxPlayers) el.textContent = cfg.maxPlayers;
  });

  /* ---------- Toast ---------- */
  const toastEl = $('.toast');
  let toastTimer;
  function toast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('is-visible'), 2400);
  }

  /* ---------- Clipboard ---------- */
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      let ok = false;
      try { ok = document.execCommand('copy'); } catch { ok = false; }
      ta.remove();
      return ok;
    }
  }

  $$('[data-copy-ip]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const ok = await copyText(address);
      toast(ok ? `IP copied: ${address}` : `Server IP: ${address}`);
    });
  });

  // copy the text of another element, e.g. the ticket templates on the support page
  $$('[data-copy-target]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const source = $(btn.dataset.copyTarget);
      if (!source) return;
      const ok = await copyText(source.innerText.trim());
      toast(ok ? 'Template copied' : 'Copy failed – select the text manually');
    });
  });

  /* ---------- Navigation ---------- */
  const nav = $('#nav');
  const toggle = $('.nav__toggle');

  if (nav && toggle) {
    const onScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });

    const setMenu = (open) => {
      nav.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    };
    toggle.addEventListener('click', () => setMenu(!nav.classList.contains('is-open')));
    $$('.nav__menu a').forEach((a) => a.addEventListener('click', () => setMenu(false)));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) {
        setMenu(false);
        toggle.focus();
      }
    });
    document.addEventListener('click', (e) => {
      if (nav.classList.contains('is-open') && !nav.contains(e.target)) setMenu(false);
    });
  }

  /* ---------- Table of contents: highlight the current section ---------- */
  $$('[data-toc]').forEach((toc) => {
    const links = $$('a[href^="#"]', toc);
    const byId = new Map(links.map((a) => [a.getAttribute('href').slice(1), a]));
    if (!('IntersectionObserver' in window)) return;
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        links.forEach((a) => a.classList.remove('is-active'));
        const link = byId.get(entry.target.id);
        if (!link) return;
        link.classList.add('is-active');
        // keep the active chip visible in the horizontal mobile TOC
        const list = link.closest('ol');
        if (list && list.scrollWidth > list.clientWidth) {
          list.scrollTo({ left: link.offsetLeft - 16, behavior: reduceMotion ? 'auto' : 'smooth' });
        }
      });
    }, { rootMargin: '-25% 0px -65% 0px' });
    byId.forEach((_, id) => {
      const section = document.getElementById(id);
      if (section) spy.observe(section);
    });
  });

  /* ---------- Search filter (rules, FAQ) ---------- */
  $$('[data-filter]').forEach((input) => {
    const scope = $(input.dataset.filter);
    if (!scope) return;
    const items = $$('[data-filter-item]', scope);
    const groups = $$('[data-filter-group]', scope);
    const empty = $('[data-filter-empty]', scope);

    input.addEventListener('input', () => {
      const terms = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      let visible = 0;
      items.forEach((item) => {
        const match = terms.every((t) => item.textContent.toLowerCase().includes(t));
        item.hidden = !match;
        if (match) visible += 1;
        // open matching FAQ entries while searching, close them again afterwards
        if (item.tagName === 'DETAILS') {
          if (terms.length && match) {
            if (!item.open) item.dataset.autoOpen = '';
            item.open = true;
          } else if ('autoOpen' in item.dataset) {
            item.open = false;
            delete item.dataset.autoOpen;
          }
        }
      });
      groups.forEach((group) => {
        group.hidden = !$$('[data-filter-item]', group).some((i) => !i.hidden);
      });
      if (empty) empty.hidden = visible > 0;
    });
  });

  /* ---------- Rules: copy a direct link to a rule ---------- */
  $$('.rule-item__num').forEach((link) => {
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      const hash = link.getAttribute('href');
      const target = $(hash);
      history.replaceState(null, '', hash);
      $$('.rule-item.is-target').forEach((el) => el.classList.remove('is-target'));
      if (target) target.classList.add('is-target');
      const ok = await copyText(window.location.href);
      toast(ok ? `Link to rule ${link.textContent.trim()} copied` : `Rule ${link.textContent.trim()}`);
    });
  });

  /* ---------- Tabs ---------- */
  $$('[data-tabs]').forEach((wrap) => {
    const tabs = $$('[role="tab"]', wrap);
    const select = (tab, focus) => {
      tabs.forEach((t) => {
        const active = t === tab;
        t.setAttribute('aria-selected', String(active));
        t.tabIndex = active ? 0 : -1;
        const panel = document.getElementById(t.getAttribute('aria-controls'));
        if (panel) panel.hidden = !active;
      });
      if (focus) tab.focus();
    };
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => select(tab, false));
      tab.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
        select(next, true);
      });
    });
    select(tabs.find((t) => t.getAttribute('aria-selected') === 'true') || tabs[0], false);
  });

  /* ---------- Mod list ---------- */
  $$('[data-mods-list]').forEach((list) => {
    list.textContent = '';
    (cfg.mods || []).forEach((mod) => {
      const li = document.createElement('li');
      if (mod.url) {
        const a = document.createElement('a');
        a.href = mod.url;
        a.target = '_blank';
        a.rel = 'noopener';
        a.textContent = mod.name;
        li.appendChild(a);
      } else {
        li.textContent = mod.name;
      }
      list.appendChild(li);
    });
  });

  /* ---------- Restart countdown ---------- */
  const restarts = (cfg.restartTimes || [])
    .map((label) => {
      const [h, m] = String(label).split(':').map(Number);
      return { label, sec: h * 3600 + (m || 0) * 60 };
    })
    .filter((r) => Number.isFinite(r.sec))
    .sort((a, b) => a.sec - b.sec);

  if (restarts.length) {
    let tz = cfg.timezone || undefined;
    try {
      new Intl.DateTimeFormat('en-GB', { timeZone: tz });
    } catch {
      tz = undefined; // unknown time zone → fall back to the visitor's local time
    }

    // seconds since midnight in the server's time zone
    const serverSeconds = () => {
      const parts = new Intl.DateTimeFormat('en-GB', {
        timeZone: tz, hourCycle: 'h23', hour: '2-digit', minute: '2-digit', second: '2-digit',
      }).formatToParts(new Date());
      const get = (type) => Number((parts.find((p) => p.type === type) || {}).value || 0);
      return (get('hour') % 24) * 3600 + get('minute') * 60 + get('second');
    };
    const secondsUntil = (r, now) => ((r.sec - now + 86400) % 86400) || 86400;
    const pad = (n) => String(n).padStart(2, '0');
    const clock = (s) => `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
    const localFmt = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' });

    let tzName = '';
    try {
      tzName = (new Intl.DateTimeFormat('en-GB', { timeZone: tz, timeZoneName: 'short' })
        .formatToParts(new Date()).find((p) => p.type === 'timeZoneName') || {}).value || '';
    } catch { tzName = ''; }
    $$('[data-restart-tz]').forEach((el) => { el.textContent = tzName; });

    const countdownEls = $$('[data-restart-countdown]');
    const nextEls = $$('[data-restart-next]');
    const listEls = $$('[data-restart-list]');
    let lastNext = null;

    const tick = () => {
      const now = serverSeconds();
      let next = restarts[0];
      restarts.forEach((r) => {
        if (secondsUntil(r, now) < secondsUntil(next, now)) next = r;
      });
      const remaining = secondsUntil(next, now);
      countdownEls.forEach((el) => { el.textContent = clock(remaining); });

      if (next !== lastNext) {
        lastNext = next;
        nextEls.forEach((el) => { el.textContent = next.label; });
        listEls.forEach((list) => {
          list.textContent = '';
          restarts.forEach((r) => {
            const li = document.createElement('li');
            li.className = 'schedule__item' + (r === next ? ' is-next' : '');
            const time = document.createElement('span');
            time.className = 'schedule__time';
            time.textContent = r.label;
            li.appendChild(time);
            // show the visitor's local time when it differs from server time
            const local = localFmt.format(new Date(Date.now() + secondsUntil(r, now) * 1000));
            if (local !== r.label) {
              const loc = document.createElement('span');
              loc.className = 'schedule__local';
              loc.textContent = `${local} your time`;
              li.appendChild(loc);
            }
            list.appendChild(li);
          });
        });
      }
    };
    tick();
    setInterval(tick, 1000);
  }

  /* ---------- Reveal on scroll ---------- */
  const revealEls = $$('.reveal');
  // stagger elements that share the same parent
  revealEls.forEach((el) => {
    const siblings = Array.from(el.parentElement.children).filter((c) => c.classList.contains('reveal'));
    const index = siblings.indexOf(el);
    if (siblings.length > 1 && index > 0) el.style.setProperty('--delay', `${Math.min(index, 5) * 0.08}s`);
  });

  if ('IntersectionObserver' in window && !reduceMotion) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('is-visible'));
  }

  /* ---------- Hero: rain & lightning (home page) ---------- */
  const hero = $('.hero');
  const canvas = $('.hero__rain');
  const flash = $('.hero__flash');
  let heroVisible = true;

  if (hero && 'IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      heroVisible = entry.isIntersecting;
    }).observe(hero);
  }

  if (canvas && canvas.getContext && !reduceMotion) {
    const ctx = canvas.getContext('2d');
    const WIND = 0.22;
    const LAYERS = [
      { alpha: 0.10, width: 1, speed: [9, 13], len: [10, 18] },
      { alpha: 0.18, width: 1, speed: [13, 18], len: [16, 26] },
      { alpha: 0.28, width: 1.4, speed: [18, 24], len: [24, 36] },
    ];
    let w = 0;
    let h = 0;
    let drops = [];

    const rand = (min, max) => min + Math.random() * (max - min);

    const makeDrop = (layer, anywhere) => ({
      layer,
      x: rand(-100, w + 100),
      y: anywhere ? rand(0, h) : rand(-h * 0.25, -20),
      speed: rand(...LAYERS[layer].speed),
      len: rand(...LAYERS[layer].len),
    });

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(420, Math.round((w * h) / 6500));
      drops = Array.from({ length: count }, (_, i) => makeDrop(i % LAYERS.length, true));
    };

    const frame = () => {
      requestAnimationFrame(frame);
      if (!heroVisible || document.hidden) return;
      ctx.clearRect(0, 0, w, h);
      ctx.lineCap = 'round';
      LAYERS.forEach((layer, li) => {
        ctx.strokeStyle = `rgba(214, 205, 255, ${layer.alpha})`;
        ctx.lineWidth = layer.width;
        ctx.beginPath();
        for (const d of drops) {
          if (d.layer !== li) continue;
          ctx.moveTo(d.x, d.y);
          ctx.lineTo(d.x - d.len * WIND, d.y + d.len);
          d.y += d.speed;
          d.x -= d.speed * WIND;
          if (d.y > h + 40) Object.assign(d, makeDrop(li, false));
        }
        ctx.stroke();
      });
    };

    resize();
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 150);
    });
    requestAnimationFrame(frame);
  }

  if (flash && !reduceMotion) {
    const strike = () => {
      if (heroVisible && !document.hidden) {
        flash.classList.remove('is-flashing');
        void flash.offsetWidth; // restart the animation
        flash.classList.add('is-flashing');
      }
      setTimeout(strike, 5000 + Math.random() * 9000);
    };
    setTimeout(strike, 2200);
  }

  /* ---------- Gallery lightbox ---------- */
  const lightbox = $('.lightbox');
  const items = $$('[data-lightbox]');
  if (lightbox && items.length && typeof lightbox.showModal === 'function') {
    const img = $('.lightbox__img', lightbox);
    const caption = $('.lightbox__caption', lightbox);
    let current = 0;

    const show = (index) => {
      current = (index + items.length) % items.length;
      const item = items[current];
      img.src = item.dataset.src;
      img.alt = $('img', item).alt;
      caption.textContent = item.dataset.caption || '';
    };

    items.forEach((item, i) => {
      item.addEventListener('click', () => {
        show(i);
        lightbox.showModal();
      });
    });

    $('.lightbox__close', lightbox).addEventListener('click', () => lightbox.close());
    $('.lightbox__nav--prev', lightbox).addEventListener('click', () => show(current - 1));
    $('.lightbox__nav--next', lightbox).addEventListener('click', () => show(current + 1));
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) lightbox.close();
    });
    lightbox.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') show(current - 1);
      if (e.key === 'ArrowRight') show(current + 1);
    });
  }

  /* ---------- Live status via BattleMetrics (optional) ---------- */
  if (cfg.battlemetricsId) {
    const dots = $$('[data-status-dot]');
    const texts = $$('[data-status-text]');
    const players = $$('[data-players]');
    $$('[data-players-label]').forEach((el) => { el.textContent = 'Players'; });

    const refresh = async () => {
      try {
        const res = await fetch(`https://api.battlemetrics.com/servers/${encodeURIComponent(cfg.battlemetricsId)}`);
        if (!res.ok) throw new Error(res.status);
        const { data } = await res.json();
        const a = data.attributes;
        const online = a.status === 'online';
        dots.forEach((dot) => {
          dot.classList.toggle('is-online', online);
          dot.classList.toggle('is-offline', !online);
        });
        texts.forEach((t) => { t.textContent = online ? 'Online' : 'Offline'; });
        players.forEach((p) => { p.textContent = `${a.players ?? 0} / ${a.maxPlayers ?? cfg.maxPlayers}`; });
      } catch {
        dots.forEach((dot) => dot.classList.remove('is-online', 'is-offline'));
        texts.forEach((t) => { t.textContent = 'Unknown'; });
      }
    };

    refresh();
    setInterval(refresh, 60000);
  }
})();
