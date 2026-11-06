<script setup lang="ts">
import { computed } from 'vue'
import { usePosesStore } from '@/stores/poses'
import type { CategoryId } from '@/types/pose'

/** 构图小贴士（决策 §9-8）：灰绿卡，按品类取材 */
const props = defineProps<{ category: CategoryId }>()

const store = usePosesStore()
const tips = computed(() => store.tipsOf(props.category)?.tips ?? [])
</script>

<template>
  <aside class="tips">
    <h4 class="title">
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <path d="M12 3a6 6 0 0 1 3.6 10.8c-.6.5-.9 1-.9 1.7v.5h-5.4v-.5c0-.7-.3-1.2-.9-1.7A6 6 0 0 1 12 3z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
        <path d="M10 19h4M10.8 21h2.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      </svg>
      构图小贴士
    </h4>
    <ul>
      <li v-for="(t, i) in tips" :key="i">
        <b>{{ t.type === 'composition' ? '机位' : '光线' }}</b>
        <span>{{ t.text }}</span>
      </li>
    </ul>
  </aside>
</template>

<style scoped>
.tips {
  background: var(--c-sage-soft);
  border-radius: var(--r-md);
  padding: var(--sp-4);
}

.title {
  margin: 0 0 var(--sp-3);
  font-size: var(--fs-14);
  color: var(--c-sage);
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.tips ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--sp-2);
}

.tips li {
  display: grid;
  grid-template-columns: 36px 1fr;
  gap: var(--sp-2);
  font-size: var(--fs-13);
  line-height: 1.6;
}

.tips b {
  color: var(--c-sage);
  font-size: var(--fs-12);
}

.tips span { color: var(--c-ink); }
</style>
