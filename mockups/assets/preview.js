/* ============================================================
   摆拍手册 PoseGuide · 原型预览工具 preview.js
   每页左下角「390 预览」：以 390×844 iframe 加载当前页，
   媒体查询随 iframe 视口生效 → 无需开发者工具即可评估移动档。
   embed=1 时（iframe 内部）不注入，避免递归。
   ============================================================ */
(function () {
  'use strict';
  const q = new URLSearchParams(location.search);
  if (q.has('embed')) return;

  const CSS = `
  .pgp-bar{position:fixed;left:16px;bottom:16px;z-index:9001;display:flex;gap:8px;font-family:-apple-system,"PingFang SC","Segoe UI","Microsoft YaHei",sans-serif}
  .pgp-btn{display:inline-flex;align-items:center;gap:7px;height:40px;padding:0 15px;border-radius:999px;
    background:#221B14;color:#F5EEE4;font-size:13px;font-weight:600;box-shadow:0 6px 20px rgba(30,20,10,.25);
    cursor:pointer;border:0;transition:transform .15s ease}
  .pgp-btn:active{transform:scale(.95)}
  .pgp-btn svg{width:15px;height:15px}
  .pgp-hint{display:inline-flex;align-items:center;height:40px;padding:0 14px;border-radius:999px;background:rgba(255,255,255,.92);
    color:#5C5145;font-size:12px;box-shadow:0 6px 20px rgba(30,20,10,.12)}
  .pgp-overlay{position:fixed;inset:0;z-index:9000;background:rgba(20,14,8,.62);backdrop-filter:blur(6px);
    display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .24s ease}
  .pgp-overlay.show{opacity:1}
  .pgp-device{background:#17130E;border-radius:52px;padding:11px;box-shadow:0 30px 80px rgba(0,0,0,.5);transform-origin:center}
  .pgp-device iframe{width:390px;height:844px;border:0;border-radius:42px;background:#FAF7F1;display:block}
  .pgp-close{position:fixed;top:18px;right:18px;width:44px;height:44px;border-radius:50%;border:0;cursor:pointer;
    background:rgba(255,255,255,.94);color:#221B14;font-size:20px;box-shadow:0 6px 20px rgba(0,0,0,.3)}
  @media (max-width:640px){.pgp-bar{display:none}.pgp-hint{display:none}}
  @media (prefers-reduced-motion:reduce){.pgp-overlay{transition:none}}
  `;
  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);

  const bar = document.createElement('div');
  bar.className = 'pgp-bar';
  bar.innerHTML = `
    <button class="pgp-btn" id="pgpMobile" aria-label="以 390×844 移动视口预览当前页">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="7" y="2.5" width="10" height="19" rx="2.6"/><path d="M10.5 5h3"/></svg>
      390 预览
    </button>
    <span class="pgp-hint">直接缩放窗口可验证 768 / 1200 断点</span>`;
  document.body.appendChild(bar);

  let overlay = null, device = null;

  function fit() {
    if (!device) return;
    const s = Math.min((innerHeight - 72) / 866, (innerWidth - 56) / 412, 1);
    device.style.transform = `scale(${s})`;
  }
  function open() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.className = 'pgp-overlay';
    overlay.innerHTML = `<div class="pgp-device"><iframe src="${location.pathname.split('/').pop()}?embed=1" title="移动端 390px 预览"></iframe></div>
      <button class="pgp-close" aria-label="关闭移动预览">✕</button>`;
    document.body.appendChild(overlay);
    device = overlay.querySelector('.pgp-device');
    fit();
    requestAnimationFrame(() => overlay.classList.add('show'));
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay || e.target.closest('.pgp-close')) close();
    });
    document.addEventListener('keydown', esc);
    addEventListener('resize', fit);
    document.documentElement.style.overflow = 'hidden';
  }
  function close() {
    if (!overlay) return;
    const el = overlay;
    el.classList.remove('show');
    document.documentElement.style.overflow = '';
    document.removeEventListener('keydown', esc);
    removeEventListener('resize', fit);
    setTimeout(() => el.remove(), 240);
    overlay = null; device = null;
  }
  function esc(e) { if (e.key === 'Escape') close(); }

  bar.querySelector('#pgpMobile').addEventListener('click', open);
})();
