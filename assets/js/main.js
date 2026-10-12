/* ==========================================================================
   Project Blackout PVP – interactions
   ========================================================================== */
(() => {
  'use strict';

  const cfg = Object.assign(
    { ip: '', port: '', map: '', maxPlayers: '', discord: '', battlemetricsId: '' },
    window.BLACKOUT_CONFIG || {}
  );
  const address = cfg.port ? `${cfg.ip}:${cfg.port}` : cfg.ip;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------- Write config values into the page ---------- */
  const values = { ...cfg, address };
  $$('[data-cfg]').forEach((el) => {
    const value = values[el.dataset.cfg];
    if (value !== undefined && value !== '') el.textContent = value;
  });
  $$('[data-cfg-href]').forEach((el) => {
    const value = values[el.dataset.cfgHref];
    if (value) el.href = value;
  });
  $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });

  const playersEl = $('[data-players]');
  if (playersEl && cfg.maxPlayers) playersEl.textContent = cfg.maxPlayers;

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

  /* ---------- Copy IP ---------- */
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

  /* ---------- Navigation ---------- */
  const nav = $('#nav');
  const toggle = $('.nav__toggle');

  const onScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 24);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  function setMenu(open) {
    nav.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  }
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

  // highlight the active menu item while scrolling
  const navLinks = $$('.nav__link');
  const linkFor = new Map(navLinks.map((a) => [a.getAttribute('href').slice(1), a]));
  if ('IntersectionObserver' in window) {
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((a) => a.removeAttribute('aria-current'));
        const link = linkFor.get(entry.target.id);
        if (link) link.setAttribute('aria-current', 'true');
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    $$('main section[id]').forEach((s) => spy.observe(s));
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

  /* ---------- Hero: rain & lightning ---------- */
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

    function makeDrop(layer, anywhere) {
      return {
        layer,
        x: rand(-100, w + 100),
        y: anywhere ? rand(0, h) : rand(-h * 0.25, -20),
        speed: rand(...LAYERS[layer].speed),
        len: rand(...LAYERS[layer].len),
      };
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(420, Math.round((w * h) / 6500));
      drops = Array.from({ length: count }, (_, i) => makeDrop(i % LAYERS.length, true));
    }

    function frame() {
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
    }

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

    function show(index) {
      current = (index + items.length) % items.length;
      const item = items[current];
      img.src = item.dataset.src;
      img.alt = $('img', item).alt;
      caption.textContent = item.dataset.caption || '';
    }

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
    const liveEl = $('[data-live]');
    const dot = $('[data-status-dot]');
    const text = $('[data-status-text]');
    const label = $('[data-players-label]');
    liveEl.hidden = false;
    label.textContent = 'Players';

    async function refresh() {
      try {
        const res = await fetch(`https://api.battlemetrics.com/servers/${encodeURIComponent(cfg.battlemetricsId)}`);
        if (!res.ok) throw new Error(res.status);
        const { data } = await res.json();
        const a = data.attributes;
        const online = a.status === 'online';
        dot.classList.toggle('is-online', online);
        dot.classList.toggle('is-offline', !online);
        text.textContent = online ? 'Online' : 'Offline';
        playersEl.textContent = `${a.players ?? 0} / ${a.maxPlayers ?? cfg.maxPlayers}`;
      } catch {
        dot.classList.remove('is-online', 'is-offline');
        text.textContent = 'Unknown';
      }
    }

    refresh();
    setInterval(refresh, 60000);
  }
})();
