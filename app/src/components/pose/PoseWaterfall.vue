<script setup lang="ts">
import { ref, watch } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'
import PoseCard from './PoseCard.vue'
import type { Pose } from '@/types/pose'

/**
 * 瀑布流卡片流（决议 #19）：CSS multi-column 实现，触底自动加载。
 * 哨兵进入视口 → emit load-more；父级追加数据后重置哨兵。
 */
const props = defineProps<{ poses: Pose[]; finished?: boolean; loading?: boolean }>()
const emit = defineEmits<{ 'load-more': [] }>()

const sentinel = ref<HTMLElement | null>(null)
let lastCount = -1

const { stop } = useIntersectionObserver(
  sentinel,
  ([entry]) => {
    if (entry?.isIntersecting && !props.finished && !props.loading && props.poses.length !== lastCount) {
      lastCount = props.poses.length
      emit('load-more')
    }
  },
  { rootMargin: '600px 0px' },
)

watch(
  () => props.finished,
  (done) => {
    if (done) stop()
  },
)
</script>

<template>
  <div>
    <div class="waterfall">
      <PoseCard v-for="p in poses" :key="p.id" :pose="p" />
    </div>
    <div ref="sentinel" class="sentinel" aria-hidden="true" />
    <p v-if="loading" class="hint" role="status" aria-live="polite">加载中…</p>
    <p v-else-if="finished" class="hint">已经到底啦 · 共 {{ poses.length }} 个姿势</p>
  </div>
</template>

<style scoped>
.waterfall {
  columns: 2;
  column-gap: var(--sp-3);
}

@media (min-width: 768px) {
  .waterfall { columns: 3; }
}

@media (min-width: 1200px) {
  .waterfall { columns: 5; }
}

.sentinel {
  height: 1px;
}

.hint {
  text-align: center;
  color: var(--c-ink-3);
  font-size: var(--fs-13);
  padding: var(--sp-4) 0;
}
</style>
