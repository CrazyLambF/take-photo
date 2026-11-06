<script setup lang="ts">
import { watch } from 'vue'
import { usePreferredDark } from '@vueuse/core'
import AppTopNav from '@/components/layout/AppTopNav.vue'
import AppTabbar from '@/components/layout/AppTabbar.vue'
import CompareBar from '@/components/common/CompareBar.vue'
import FabMenu from '@/components/common/FabMenu.vue'
import { useSettingsStore } from '@/stores/settings'
import { useAppBreakpoints } from '@/composables/useAppBreakpoints'

const settings = useSettingsStore()
const { isMobile } = useAppBreakpoints()
const prefersDark = usePreferredDark()

/** 主题三档：auto 跟随系统，light/dark 手动（§3.3-6） */
function applyTheme(): void {
  const dark = settings.theme === 'dark' || (settings.theme === 'auto' && prefersDark.value)
  if (dark) document.documentElement.dataset.theme = 'dark'
  else delete document.documentElement.dataset.theme
}

watch([() => settings.theme, prefersDark], applyTheme, { immediate: true })
</script>

<template>
  <div class="app-shell">
    <AppTopNav v-if="!isMobile" />
    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <KeepAlive :include="['PoseDetailView', 'SearchView', 'CompareView']">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>
    <AppTabbar v-if="isMobile" />
    <CompareBar />
    <FabMenu />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100dvh;
  background: var(--c-bg);
  color: var(--c-ink);
}

.app-main {
  /* 移动端给底部 Tabbar 留出空间（含 safe-area） */
  padding-bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom));
}

@media (min-width: 768px) {
  .app-main {
    padding-top: var(--topnav-h);
    padding-bottom: var(--sp-16);
  }
}
</style>
