<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useCompareStore } from '@/stores/compare'

/** 对比浮条：任意列表页加入对比后出现，「已选 n/3」（§3.2 全局能力） */
const compare = useCompareStore()
const router = useRouter()

function goCompare(): void {
  if (compare.ids.length >= 2) {
    router.push({ path: '/compare', query: { ids: compare.ids.join(',') } })
  }
}
</script>

<template>
  <Transition name="bar">
    <div v-if="compare.ids.length" class="compare-bar" role="region" aria-label="对比栏">
      <span class="count">已选 {{ compare.ids.length }}/3</span>
      <div class="ids">
        <span v-for="id in compare.ids" :key="id" class="id-chip">
          {{ id }}
          <button type="button" :aria-label="`移除 ${id}`" @click="compare.remove(id)">✕</button>
        </span>
      </div>
      <button type="button" class="ghost" @click="compare.clear()">清空</button>
      <button type="button" class="go" :disabled="compare.ids.length < 2" @click="goCompare">
        去对比
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.compare-bar {
  position: fixed;
  z-index: var(--z-compare);
  left: 50%;
  transform: translateX(-50%);
  bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom) + var(--sp-2));
  width: min(680px, calc(100% - var(--sp-6)));
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  background: var(--c-ink);
  color: var(--c-bg);
  border-radius: var(--r-full);
  padding: var(--sp-2) var(--sp-3) var(--sp-2) var(--sp-4);
  box-shadow: var(--shadow-2);
}

@media (min-width: 768px) {
  .compare-bar {
    bottom: var(--sp-4);
  }
}

.count {
  font-size: var(--fs-13);
  font-weight: 700;
  white-space: nowrap;
}

.ids {
  display: flex;
  gap: var(--sp-1);
  flex: 1;
  overflow: hidden;
}

.id-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: color-mix(in srgb, var(--c-bg) 18%, transparent);
  border-radius: var(--r-full);
  font-size: var(--fs-11);
  padding: 2px var(--sp-2);
  white-space: nowrap;
}

.id-chip button {
  border: none;
  background: none;
  color: inherit;
  cursor: pointer;
  font-size: var(--fs-11);
  padding: 2px;
}

.ghost {
  border: none;
  background: none;
  color: color-mix(in srgb, var(--c-bg) 75%, transparent);
  font-size: var(--fs-13);
  cursor: pointer;
  white-space: nowrap;
}

.go {
  border: none;
  background: var(--c-accent);
  color: var(--c-on-accent);
  font-size: var(--fs-13);
  font-weight: 700;
  border-radius: var(--r-full);
  padding: var(--sp-2) var(--sp-4);
  cursor: pointer;
  white-space: nowrap;
}

.go:disabled {
  opacity: .45;
  cursor: not-allowed;
}

.bar-enter-active,
.bar-leave-active {
  transition: transform var(--dur-slow) var(--ease-spring), opacity var(--dur-base) var(--ease-out);
}

.bar-enter-from,
.bar-leave-to {
  transform: translateX(-50%) translateY(24px);
  opacity: 0;
}
</style>
