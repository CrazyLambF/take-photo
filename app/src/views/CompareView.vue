<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageContainer from '@/components/layout/PageContainer.vue'
import { usePosesStore } from '@/stores/poses'
import { asset, placeholder } from '@/utils/asset'
import type { Pose } from '@/types/pose'

/** 对比页（§5.4 / P1）：2–3 个姿势并排对比 */
defineOptions({ name: 'CompareView' })

const store = usePosesStore()
const route = useRoute()
const router = useRouter()

const ids = computed<string[]>(() => {
  const raw = Array.isArray(route.query.ids) ? route.query.ids[0] : route.query.ids
  return (raw ?? '').split(',').filter(Boolean).slice(0, 3)
})

const poses = computed<Pose[]>(() => ids.value.map((id) => store.get(id)).filter((p): p is Pose => p !== undefined))

function removeOne(id: string): void {
  const next = ids.value.filter((x) => x !== id)
  router.replace({ query: next.length ? { ids: next.join(',') } : {} })
}

function goLibrary(): void {
  router.push('/poses')
}

const ROWS = [
  { key: 'difficulty', label: '难度' },
  { key: 'light', label: '光线' },
  { key: 'focal', label: '焦段' },
  { key: 'angle', label: '机位' },
  { key: 'framing', label: '构图' },
  { key: 'body', label: '姿势要点' },
] as const

function cell(pose: Pose, key: (typeof ROWS)[number]['key']): string {
  switch (key) {
    case 'difficulty': return ['入门', '进阶', '挑战'][pose.difficulty - 1]
    case 'light': return pose.light.join(' / ')
    case 'focal': return pose.camera.focal || '—'
    case 'angle': return pose.camera.angle || '—'
    case 'framing': return pose.camera.framing
    case 'body': return pose.pose.body
  }
}
</script>

<template>
  <PageContainer>
    <header class="head">
      <h1>姿势对比</h1>
      <button type="button" class="txt" @click="goLibrary">＋ 去姿势库添加</button>
    </header>

    <div v-if="poses.length >= 2" class="grid" :style="{ '--n': poses.length }">
      <div v-for="p in poses" :key="p.id" class="col">
        <button type="button" class="rm" :aria-label="`移除 ${p.id}`" @click="removeOne(p.id)">✕</button>
        <RouterLink :to="`/poses/${p.id}`">
          <img :src="p.images.cover ? asset(p.images.cover) : placeholder()" :alt="p.name" width="320" height="426" />
        </RouterLink>
        <h2>
          <RouterLink :to="`/poses/${p.id}`">{{ p.name }}</RouterLink>
        </h2>
        <dl>
          <div v-for="r in ROWS" :key="r.key" class="row">
            <dt>{{ r.label }}</dt>
            <dd>{{ cell(p, r.key) }}</dd>
          </div>
        </dl>
      </div>
    </div>

    <div v-else class="empty">
      <p>在姿势库或详情页点「⇄ 对比」，选 2–3 个姿势来并排比较</p>
      <button type="button" class="cta" @click="goLibrary">去姿势库</button>
    </div>
  </PageContainer>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: var(--sp-4);
}

.head h1 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: var(--fs-28);
}

.txt {
  border: none;
  background: none;
  color: var(--c-accent-deep);
  cursor: pointer;
  font-size: var(--fs-13);
}

.grid {
  display: grid;
  grid-template-columns: repeat(var(--n, 2), 1fr);
  gap: var(--sp-3);
}

@media (max-width: 767px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

.col {
  background: var(--c-surface);
  border-radius: var(--r-lg);
  padding: var(--sp-3);
  position: relative;
  box-shadow: var(--shadow-1);
}

.rm {
  position: absolute;
  top: var(--sp-2);
  right: var(--sp-2);
  z-index: 1;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--r-full);
  background: color-mix(in srgb, var(--c-ink) 60%, transparent);
  color: var(--c-bg);
  cursor: pointer;
}

.col img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: var(--r-md);
  background: var(--c-bg-soft);
  display: block;
}

.col h2 {
  margin: var(--sp-2) 0;
  font-size: var(--fs-16);
}

.col h2 a { color: var(--c-ink); text-decoration: none; }

.col dl { margin: 0; display: grid; gap: var(--sp-2); }

.row { display: grid; grid-template-columns: 64px 1fr; gap: var(--sp-2); }

dt { font-size: var(--fs-12); color: var(--c-ink-3); }

dd {
  margin: 0;
  font-size: var(--fs-13);
  line-height: 1.55;
  color: var(--c-ink);
}

.empty {
  text-align: center;
  padding: var(--sp-16) 0;
  color: var(--c-ink-3);
}

.cta {
  margin-top: var(--sp-3);
  border: 1px solid var(--c-line-strong);
  background: var(--c-surface);
  border-radius: var(--r-full);
  padding: var(--sp-2) var(--sp-5);
  color: var(--c-accent-deep);
  cursor: pointer;
}
</style>
