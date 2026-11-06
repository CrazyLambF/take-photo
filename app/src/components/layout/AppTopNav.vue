<script setup lang="ts">
/** 顶部导航（平板/桌面 ≥768px 形态，§3.2）：logo + 4 入口 + 搜索框常驻 */
const NAV = [
  { to: '/', label: '首页' },
  { to: '/poses', label: '姿势库' },
  { to: '/collections', label: '收藏与清单' },
  { to: '/profile', label: '我的' },
] as const
</script>

<template>
  <header class="topnav">
    <div class="topnav-inner">
      <RouterLink to="/" class="logo">摆拍手册<small>PoseGuide</small></RouterLink>
      <nav class="nav" aria-label="主导航">
        <RouterLink v-for="n in NAV" :key="n.to" :to="n.to" class="nav-link">{{ n.label }}</RouterLink>
      </nav>
      <RouterLink to="/search" class="search" aria-label="搜索姿势">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2" />
          <path d="m16.5 16.5 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
        <span>搜索姿势 / 标签</span>
      </RouterLink>
    </div>
  </header>
</template>

<style scoped>
.topnav {
  position: fixed;
  inset-inline: 0;
  top: 0;
  z-index: var(--z-nav);
  height: var(--topnav-h);
  background: color-mix(in srgb, var(--c-surface) 88%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--c-line);
}

.topnav-inner {
  max-width: var(--container-max);
  height: 100%;
  margin-inline: auto;
  padding-inline: var(--sp-6);
  display: flex;
  align-items: center;
  gap: var(--sp-8);
}

.logo {
  font-family: var(--font-serif);
  font-size: var(--fs-20);
  font-weight: 700;
  color: var(--c-ink);
  text-decoration: none;
  letter-spacing: .02em;
}

.logo small {
  font-family: var(--font-sans);
  font-size: var(--fs-11);
  font-weight: 400;
  color: var(--c-ink-3);
  margin-left: var(--sp-2);
  letter-spacing: .12em;
}

.nav {
  display: flex;
  gap: var(--sp-2);
  margin-inline: auto;
}

.nav-link {
  padding: var(--sp-2) var(--sp-4);
  border-radius: var(--r-full);
  font-size: var(--fs-15);
  color: var(--c-ink-2);
  text-decoration: none;
  transition: color var(--dur-fast) var(--ease-out), background-color var(--dur-fast) var(--ease-out);
}

.nav-link:hover {
  color: var(--c-ink);
  background: var(--c-bg-soft);
}

.nav-link.router-link-exact-active,
.nav-link.is-active {
  color: var(--c-accent-deep);
  background: var(--c-accent-soft);
  font-weight: 600;
}

.search {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 200px;
  padding: var(--sp-2) var(--sp-4);
  border: 1px solid var(--c-line);
  border-radius: var(--r-full);
  background: var(--c-surface-2);
  color: var(--c-ink-3);
  font-size: var(--fs-13);
  text-decoration: none;
  transition: border-color var(--dur-fast) var(--ease-out);
}

.search:hover {
  border-color: var(--c-line-strong);
}
</style>
