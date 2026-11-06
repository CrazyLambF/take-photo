<script setup lang="ts">
/** 底部 Tabbar（移动 <768px 形态，§3.2）：4 个常驻入口，≥44px 触点 + safe-area */
const TABS = [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/poses', label: '姿势库', icon: 'grid' },
  { to: '/collections', label: '收藏', icon: 'heart' },
  { to: '/profile', label: '我的', icon: 'user' },
] as const
</script>

<template>
  <nav class="tabbar" aria-label="底部导航">
    <RouterLink v-for="t in TABS" :key="t.to" :to="t.to" class="tab" :aria-label="t.label">
      <svg v-if="t.icon === 'home'" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-4.5v-5.5h-5V21H5a1 1 0 0 1-1-1z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
      </svg>
      <svg v-else-if="t.icon === 'grid'" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="4" y="4" width="7" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8" />
        <rect x="13" y="4" width="7" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8" />
        <rect x="4" y="13" width="7" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8" />
        <rect x="13" y="13" width="7" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8" />
      </svg>
      <svg v-else-if="t.icon === 'heart'" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 20s-7-4.6-7-9.5A3.8 3.8 0 0 1 12 7.6a3.8 3.8 0 0 1 7 2.9C19 15.4 12 20 12 20z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
      </svg>
      <svg v-else viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="8.5" r="3.5" fill="none" stroke="currentColor" stroke-width="1.8" />
        <path d="M5 20a7 7 0 0 1 14 0" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      </svg>
      <span>{{ t.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.tabbar {
  position: fixed;
  inset-inline: 0;
  bottom: 0;
  z-index: var(--z-nav);
  height: calc(var(--tabbar-h) + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: color-mix(in srgb, var(--c-surface) 92%, transparent);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--c-line);
}

.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-height: 44px;
  color: var(--c-ink-3);
  text-decoration: none;
  font-size: var(--fs-11);
  transition: color var(--dur-fast) var(--ease-out);
}

.tab svg {
  width: 24px;
  height: 24px;
}

.tab.router-link-exact-active {
  color: var(--c-accent-deep);
  font-weight: 600;
}
</style>
