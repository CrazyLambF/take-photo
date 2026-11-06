/* ============================================================
   摆拍手册 PoseGuide · 共享交互/动效 app.js
   职责：主题切换 / 进场 reveal（含 stagger）/ 页面转场 /
        收藏心标 / 对比浮条 / Toast / 骨架屏卡片 / 图标库
   全部动效读取 tokens.css 的时长与缓动令牌；
   prefers-reduced-motion 下自动降级（tokens.css 兜底 + JS 判定）。
   ============================================================ */
(function () {
  'use strict';
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const D = window.PG_DATA;

  /* ---------- 图标（自绘 SVG，统一 24 viewBox / 1.8 描边） ---------- */
  const S = (inner, extra) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra || ''}>${inner}</svg>`;
  const ICONS = {
    search:  S('<circle cx="11" cy="11" r="7"/><path d="m20.3 20.3-3.9-3.9"/>'),
    heart:   S('<path d="M12 20.4 5 13.2a4.8 4.8 0 0 1 6.7-6.8l.3.3.3-.3a4.8 4.8 0 0 1 6.7 6.8Z"/>'),
    compare: S('<rect x="3" y="4" width="7.5" height="16" rx="1.5"/><rect x="13.5" y="4" width="7.5" height="10" rx="1.5"/>'),
    share:   S('<path d="M12 3v12"/><path d="m7.5 7.5 4.5-4.5 4.5 4.5"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/>'),
    bookmark:S('<path d="M7 3.5h10a1 1 0 0 1 1 1V21l-6-3.6L6 21V4.5a1 1 0 0 1 1-1Z"/>'),
    sliders: S('<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2.2"/><circle cx="9" cy="17" r="2.2"/>'),
    close:   S('<path d="M6 6l12 12M18 6 6 18"/>'),
    chevL:   S('<path d="m14.5 5.5-6.5 6.5 6.5 6.5"/>'),
    chevR:   S('<path d="m9.5 5.5 6.5 6.5-6.5 6.5"/>'),
    arrowL:  S('<path d="M19 12H5"/><path d="m11 6-6 6 6 6"/>'),
    camera:  S('<path d="M4 8.5A2.5 2.5 0 0 1 6.5 6h1.6l1.2-1.8h5.4L15.9 6h1.6A2.5 2.5 0 0 1 20 8.5v8A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5Z"/><circle cx="12" cy="12.5" r="3.4"/>'),
    sparkle: S('<path d="M12 3.5 13.8 9l5.5 1.8-5.5 1.8L12 18.2l-1.8-5.6L4.7 10.8 10.2 9Z"/>'),
    bulb:    S('<path d="M9.5 18h5M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.8.6 1.2 1.3 1.3 2.1h4.4c.1-.8.5-1.5 1.3-2.1A6 6 0 0 0 12 3Z"/>'),
    sun:     S('<circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5 5l1.7 1.7M17.3 17.3 19 19M19 5l-1.7 1.7M6.7 17.3 5 19"/>'),
    moon:    S('<path d="M20 13.5A8.2 8.2 0 0 1 10.5 4a8.2 8.2 0 1 0 9.5 9.5Z"/>'),
    refresh: S('<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 3.5V8h-4.5"/>'),
    compass: S('<circle cx="12" cy="12" r="8.5"/><path d="m15.2 8.8-1.8 4.6-4.6 1.8 1.8-4.6Z"/>'),
    grid:    S('<rect x="4" y="4" width="7" height="7" rx="1.6"/><rect x="13" y="4" width="7" height="7" rx="1.6"/><rect x="4" y="13" width="7" height="7" rx="1.6"/><rect x="13" y="13" width="7" height="7" rx="1.6"/>'),
    user:    S('<circle cx="12" cy="8.2" r="3.7"/><path d="M5 20a7 7 0 0 1 14 0"/>'),
    check:   S('<path d="m5 12.5 4.5 4.5L19 7.5"/>'),
    plus:    S('<path d="M12 5v14M5 12h14"/>'),
    zoom:    S('<circle cx="11" cy="11" r="7"/><path d="m20.3 20.3-3.9-3.9M8.2 11h5.6M11 8.2v5.6"/>'),
    expand:  S('<path d="M9 4H4v5M15 4h5v5M9 20H4v-5M15 20h5v-5"/>'),
  };
  const I = (name, size) => {
    let svg = ICONS[name];
    if (size) svg = svg.replace('<svg', `<svg width="${size}" height="${size}"`);
    return svg;
  };

  /* ---------- 主题（P0：跟随系统 + 手动切换，localStorage 持久化） ---------- */
  const THEME_KEY = 'pg-theme';
  function applyTheme(t) {
    document.documentElement.dataset.theme = t;
    $$('[data-theme-toggle]').forEach(b => {
      b.innerHTML = I(t === 'dark' ? 'sun' : 'moon', 19);
      b.setAttribute('aria-label', t === 'dark' ? '切换到浅色模式' : '切换到深色模式');
    });
  }
  function toggleTheme() {
    const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem(THEME_KEY, t);
    applyTheme(t);
    toast(t === 'dark' ? '已切换深色模式' : '已切换浅色模式');
  }

  /* ---------- Toast ---------- */
  let toastTimer;
  function toast(msg) {
    let el = $('.toast');
    if (!el) { el = document.createElement('div'); el.className = 'toast'; el.setAttribute('role', 'status'); document.body.appendChild(el); }
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 2000);
  }

  /* ---------- 进场 reveal（卡片流/分区进入；stagger 由 data-stagger 容器分配） ---------- */
  let io = null;
  function observeReveal(root) {
    const els = $$('[data-reveal]:not(.in)', root || document);
    if (!els.length) return;
    if (REDUCED || !('IntersectionObserver' in window)) { els.forEach(e => e.classList.add('in')); return; }
    if (!io) {
      io = new IntersectionObserver((ents) => {
        for (const en of ents) {
          if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
        }
      }, { rootMargin: '0px 0px -6% 0px', threshold: 0.05 });
    }
    els.forEach(e => io.observe(e));
  }
  function assignStagger(root) {
    $$('[data-stagger]', root || document).forEach(box => {
      Array.from(box.children).forEach((el, i) => {
        el.setAttribute('data-reveal', '');
        el.style.setProperty('--rd', Math.min(i * 45, 420) + 'ms');
      });
    });
    observeReveal(root);
  }

  /* ---------- 页面转场（内部链接：短暂离场 → 跳转；进场由 reveal 承担） ---------- */
  function initNav() {
    $$('a[data-nav]').forEach(a => {
      a.addEventListener('click', (e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        if (e.target.closest('[data-fav],[data-compare-add],[data-toast]')) return;
        const href = a.getAttribute('href');
        if (!href || href.startsWith('#')) return;
        e.preventDefault();
        if (REDUCED) { location.href = href; return; }
        document.body.classList.add('page-leave');
        setTimeout(() => { location.href = href; }, 170);
      });
    });
  }

  /* ---------- 收藏（localStorage；心标弹跳微交互） ---------- */
  const FAV_KEY = 'pg-favs';
  let favs = new Set(JSON.parse(localStorage.getItem(FAV_KEY) || '[]'));
  function syncFavUI(id, popEl) {
    const on = favs.has(id);
    $$(`[data-fav="${id}"]`).forEach(b => {
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', String(on));
      if (popEl && b === popEl && !REDUCED) { b.classList.remove('pop'); void b.offsetWidth; b.classList.add('pop'); }
    });
    updateFavBadge();
    document.dispatchEvent(new CustomEvent('pg:fav', { detail: { id, on } }));
  }
  function toggleFav(id, btn) {
    if (favs.has(id)) { favs.delete(id); toast('已取消收藏'); }
    else { favs.add(id); toast('已收藏，可在「收藏与清单」查看'); }
    localStorage.setItem(FAV_KEY, JSON.stringify([...favs]));
    syncFavUI(id, btn);
  }
  function updateFavBadge() {
    $$('[data-fav-badge]').forEach(b => {
      b.textContent = favs.size;
      b.hidden = favs.size === 0;
    });
  }

  /* ---------- 对比浮条（§3.2：已选 n/3） ---------- */
  const CMP_KEY = 'pg-compare';
  let cmp = JSON.parse(localStorage.getItem(CMP_KEY) || '[]');
  function ensureCompareBar() {
    if ($('.compare-bar')) return;
    const bar = document.createElement('div');
    bar.className = 'compare-bar';
    bar.innerHTML = `<span class="cmp-count">已选 <b data-cmp-n>0</b>/3</span>
      <button class="cmp-clear" data-cmp-clear>清空</button>
      <button class="btn" data-cmp-go>进入对比</button>`;
    document.body.appendChild(bar);
    bar.addEventListener('click', (e) => {
      if (e.target.closest('[data-cmp-clear]')) { cmp = []; localStorage.setItem(CMP_KEY, '[]'); updateCompareUI(); toast('已清空对比列表'); }
      else if (e.target.closest('[data-cmp-go]')) { toast('对比页为 P1 功能，本轮原型未包含（见待确认清单）'); }
    });
  }
  function updateCompareUI() {
    ensureCompareBar();
    const bar = $('.compare-bar');
    $('[data-cmp-n]', bar).textContent = cmp.length;
    bar.classList.toggle('show', cmp.length > 0);
    $$('[data-compare-add]').forEach(b => {
      const on = cmp.includes(b.dataset.compareAdd);
      b.classList.toggle('added', on);
      b.setAttribute('aria-pressed', String(on));
    });
  }
  function toggleCompare(id) {
    if (cmp.includes(id)) { cmp = cmp.filter(x => x !== id); toast('已移出对比'); }
    else if (cmp.length >= 3) { toast('最多同时对比 3 个姿势'); return; }
    else { cmp.push(id); toast(`已加入对比（${cmp.length}/3）`); }
    localStorage.setItem(CMP_KEY, JSON.stringify(cmp));
    updateCompareUI();
    document.dispatchEvent(new CustomEvent('pg:compare', { detail: { id, count: cmp.length } }));
  }

  /* ---------- 全局点击委托 ---------- */
  document.addEventListener('click', (e) => {
    const favBtn = e.target.closest('[data-fav]');
    if (favBtn) { e.preventDefault(); e.stopPropagation(); toggleFav(favBtn.dataset.fav, favBtn); return; }
    const cmpBtn = e.target.closest('[data-compare-add]');
    if (cmpBtn) { e.preventDefault(); e.stopPropagation(); toggleCompare(cmpBtn.dataset.compareAdd); return; }
    const t = e.target.closest('[data-toast]');
    if (t) { e.preventDefault(); e.stopPropagation(); toast(t.dataset.toast); return; }
    if (e.target.closest('[data-theme-toggle]')) { toggleTheme(); return; }
  });

  /* ---------- 骨架屏卡片（§5.1：卡片进入时骨架屏） ---------- */
  function skeletonCards(n) {
    let html = '';
    for (let i = 0; i < n; i++) {
      html += `<div class="card sk-card" aria-hidden="true">
        <div class="card-cover skeleton"></div>
        <div class="sk-line w60 skeleton"></div>
      </div>`;
    }
    return html;
  }

  /* ---------- 姿势卡渲染（§5.1 卡片要素） ---------- */
  function dots(d) {
    return `<span class="dots" role="img" aria-label="难度 ${d} / 3">${[1, 2, 3].map(i => `<i class="${i <= d ? 'f' : ''}"></i>`).join('')}</span>`;
  }
  function poseCard(p, opts) {
    opts = opts || {};
    const cat = D.CAT_MAP[p.cat];
    return `<article class="card ${opts.feature ? 'card--feature' : ''}">
      <a class="card-link" href="detail.html?id=${p.id}" data-nav aria-label="${p.name}，${cat.name}，难度 ${p.diff} 级，查看详情">
        <div class="card-cover" role="img" aria-label="${p.name}（${p.steps[0]}）示例占位图">${D.poseSVG(p, 'cover')}</div>
        ${p.ai ? `<span class="badge-ai">${I('sparkle', 11)}AI 示意</span>` : ''}
      </a>
      <button class="heart ${favs.has(p.id) ? 'on' : ''}" data-fav="${p.id}" aria-pressed="${favs.has(p.id)}" aria-label="收藏「${p.name}」">${I('heart', 18)}</button>
      <button class="card-compare ${cmp.includes(p.id) ? 'added' : ''}" data-compare-add="${p.id}" aria-pressed="${cmp.includes(p.id)}" aria-label="将「${p.name}」加入对比" title="加入对比">${I('compare', 17)}</button>
      <div class="card-info">
        <div class="card-name">${p.name}</div>
        <div class="card-meta">${dots(p.diff)}<span class="card-scene">${p.tags[0]}</span>${p.tags[1] ? `<span class="card-scene">${p.tags[1]}</span>` : ''}</div>
      </div>
    </article>`;
  }

  /* ---------- 启动 ---------- */
  function boot() {
    if (!localStorage.getItem(THEME_KEY) && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.dataset.theme = 'dark';
    }
    applyTheme(document.documentElement.dataset.theme || 'light');
    initNav();
    assignStagger();
    updateFavBadge();
    updateCompareUI();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  /* ---------- 导出 ---------- */
  window.PG = {
    REDUCED, I, toast, dots, poseCard, skeletonCards,
    observeReveal, assignStagger, syncFavUI, favs, cmpHas: (id) => cmp.includes(id),
    data: D,
  };
})();
