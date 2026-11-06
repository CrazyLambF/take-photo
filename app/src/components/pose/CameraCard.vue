<script setup lang="ts">
import type { PoseCamera } from '@/types/pose'

/** 机位卡：焦段 / 机位 / 构图 / 参数 四行（§5.2），空字段自动隐藏 */
const props = defineProps<{ camera: PoseCamera }>()

const ROWS = [
  { key: 'focal', label: '焦段' },
  { key: 'angle', label: '机位' },
  { key: 'framing', label: '构图' },
  { key: 'settings', label: '参数' },
] as const

const rows = ROWS
  .map((r) => ({ label: r.label, text: props.camera[r.key] ?? '' }))
  .filter((r) => r.text)
</script>

<template>
  <dl class="camera-card">
    <div v-for="r in rows" :key="r.label" class="row">
      <dt>{{ r.label }}</dt>
      <dd>{{ r.text }}</dd>
    </div>
  </dl>
</template>

<style scoped>
.camera-card {
  margin: 0;
  background: var(--c-surface-2);
  border-radius: var(--r-md);
  padding: var(--sp-4);
  display: grid;
  gap: var(--sp-2);
}

.row {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: var(--sp-3);
  font-size: var(--fs-14);
  line-height: 1.55;
}

dt {
  color: var(--c-accent-deep);
  font-weight: 600;
  font-size: var(--fs-13);
}

dd {
  margin: 0;
  color: var(--c-ink);
}
</style>
