<script setup lang="ts">
import { nextTick, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEventListener } from '@vueuse/core'

/**
 * 可收缩悬浮球（决议 #20）：范围外功能入口收纳。
 * 单击展开为纵向菜单（spring 特效），ESC/路由切换收起，焦点管理齐备。
 */
const open = ref(false)
const route = useRoute()
const router = useRouter()
const menuRef = useTemplateRef<HTMLElement>('menu')

const ITEMS = [
  { key: 'search', label: '搜索', to: '/search' },
  { key: 'collections', label: '收藏', to: '/collections' },
  { key: 'compare', label: '对比', to: '/compare' },
  { key: 'top', label: '回顶部', to: '' },
] as const

function toggle(): void {
  open.value = !open.value
  if (open.value) {
    nextTick(() => menuRef.value?.querySelector<HTMLElement>('button')?.focus())
  }
}

function onItem(to: string): void {
  open.value = false
  if (to) router.push(to)
  else window.scrollTo({ top: 0, behavior: 'smooth' })
}

useEventListener(document, 'keydown', (e: KeyboardEvent) => {
  if (e.key === 'Escape' && open.value) {
    open.value = false
    ;(document.activeElement as HTMLElement | null)?.blur()
  }
})

watch(() => route.fullPath, () => {
  open.value = false
})
</script>

<template>
  <div class="fab-wrap">
    <Transition name="pop">
      <div v-if="open" ref="menu" class="menu" role="menu" aria-label="快捷入口">
        <button
          v-for="it in ITEMS"
          :key="it.key"
          type="button"
          role="menuitem"
          class="item"
          @click="onItem(it.to)"
        >{{ it.label }}</button>
      </div>
    </Transition>
    <button
      type="button"
      class="fab"
      :aria-expanded="open"
      aria-label="快捷入口菜单"
      @click="toggle"
    >
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" :class="{ x: open }">
        <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.fab-wrap {
  position: fixed;
  right: var(--sp-4);
  bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom) + var(--sp-10));
  z-index: var(--z-drawer);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--sp-2);
}

@media (min-width: 768px) {
  .fab-wrap { bottom: var(--sp-10); }
}

.fab {
  width: 52px;
  height: 52px;
  border: none;
  border-radius: var(--r-full);
  background: var(--c-accent);
  color: var(--c-on-accent);
  display: grid;
  place-items: center;
  cursor: pointer;
  box-shadow: var(--shadow-2);
  transition: transform var(--dur-base) var(--ease-spring), background-color var(--dur-fast) var(--ease-out);
}

.fab:hover { transform: scale(1.06); }

.fab svg { transition: transform var(--dur-base) var(--ease-spring); }

.fab svg.x { transform: rotate(45deg); }

.menu {
  display: grid;
  gap: var(--sp-1);
  background: var(--c-surface);
  border: 1px solid var(--c-line);
  border-radius: var(--r-md);
  padding: var(--sp-2);
  box-shadow: var(--shadow-2);
  transform-origin: bottom right;
}

.item {
  border: none;
  background: none;
  color: var(--c-ink);
  font-size: var(--fs-14);
  padding: var(--sp-2) var(--sp-5);
  border-radius: var(--r-sm);
  cursor: pointer;
  min-height: 40px;
  text-align: left;
  white-space: nowrap;
}

.item:hover { background: var(--c-bg-soft); }

.pop-enter-active { transition: transform var(--dur-base) var(--ease-spring), opacity var(--dur-fast) var(--ease-out); }
.pop-leave-active { transition: transform var(--dur-fast) var(--ease-inout), opacity var(--dur-fast) var(--ease-inout); }
.pop-enter-from,
.pop-leave-to { transform: scale(.7) translateY(8px); opacity: 0; }
</style>
