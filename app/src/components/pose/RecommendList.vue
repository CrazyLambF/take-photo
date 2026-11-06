<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Pose } from '@/types/pose'

/** 相关推荐：横向滑动的迷你卡（算法 v1 结果由父级传入） */
const props = defineProps<{ poses: Pose[] }>()
const router = useRouter()

function go(p: Pose): void {
  router.push(`/poses/${p.id}`)
}
</script>

<template>
  <div class="rec-list" role="list">
    <button v-for="p in props.poses" :key="p.id" type="button" class="rec" role="listitem" @click="go(p)">
      <img
        :src="p.images.cover ? `/${p.images.cover}` : '/poses/placeholder.svg'"
        :alt="p.name"
        loading="lazy"
        width="120"
        height="160"
      />
      <span class="n">{{ p.name }}</span>
      <span class="c">{{ p.id }}</span>
    </button>
  </div>
</template>

<style scoped>
.rec-list {
  display: flex;
  gap: var(--sp-3);
  overflow-x: auto;
  padding-bottom: var(--sp-2);
  scrollbar-width: none;
}

.rec-list::-webkit-scrollbar { display: none; }

.rec {
  flex: 0 0 auto;
  width: 108px;
  border: none;
  padding: 0;
  background: none;
  cursor: pointer;
  text-align: left;
}

.rec img {
  width: 108px;
  height: 144px;
  object-fit: cover;
  border-radius: var(--r-sm);
  background: var(--c-bg-soft);
  display: block;
}

.rec .n {
  display: block;
  margin-top: var(--sp-1);
  font-size: var(--fs-12);
  color: var(--c-ink);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rec .c {
  font-size: var(--fs-11);
  color: var(--c-ink-3);
}
</style>
