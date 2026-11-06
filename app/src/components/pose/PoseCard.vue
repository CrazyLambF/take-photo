<script setup lang="ts">
import { computed } from 'vue'
import { useFavoritesStore } from '@/stores/favorites'
import { usePosesStore } from '@/stores/poses'
import { asset, placeholder } from '@/utils/asset'
import type { Pose } from '@/types/pose'

/**
 * 姿势卡：封面 + 心标收藏 + 名称/类目/难度。
 * 数据流：pose 由父级传入；收藏/导航为全局能力，直接走 Pinia 与 router。
 */
const props = defineProps<{ pose: Pose }>()

const store = usePosesStore()
const fav = useFavoritesStore()

const categoryName = computed(() => {
  const short = store.categoryName(props.pose.category).split(' ·')[0]
  return short
})

const coverSrc = computed(() =>
  props.pose.images.cover ? asset(props.pose.images.cover) : placeholder(),
)
</script>

<template>
  <article class="pose-card">
    <RouterLink :to="`/poses/${pose.id}`" class="cover" :aria-label="`查看姿势 ${pose.name}`">
      <img :src="coverSrc" :alt="pose.name" loading="lazy" decoding="async" width="480" height="640" />
    </RouterLink>
    <button
      class="heart"
      type="button"
      :class="{ active: fav.has(pose.id) }"
      :aria-pressed="fav.has(pose.id)"
      :aria-label="fav.has(pose.id) ? '取消收藏' : '收藏'"
      @click.stop="fav.toggleFavorite(pose.id)"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 20s-7-4.6-7-9.5A3.8 3.8 0 0 1 12 7.6a3.8 3.8 0 0 1 7 2.9C19 15.4 12 20 12 20z" :fill="fav.has(pose.id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
      </svg>
    </button>
    <footer class="meta">
      <h3 class="name">
        <RouterLink :to="`/poses/${pose.id}`">{{ pose.name }}</RouterLink>
      </h3>
      <div class="sub">
        <span class="chip">{{ categoryName }}</span>
        <span class="diff" :aria-label="`难度 ${pose.difficulty}`">
          <i v-for="n in 3" :key="n" :class="{ on: n <= pose.difficulty }" />
        </span>
      </div>
    </footer>
  </article>
</template>

<style scoped>
.pose-card {
  position: relative;
  break-inside: avoid;
  margin-bottom: var(--sp-3);
  background: var(--c-surface);
  border-radius: var(--r-md);
  overflow: hidden;
  box-shadow: var(--shadow-1);
}

.cover {
  display: block;
  aspect-ratio: 3 / 4;
  background: var(--c-bg-soft);
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.heart {
  position: absolute;
  top: var(--sp-2);
  right: var(--sp-2);
  width: 36px;
  height: 36px;
  border: none;
  border-radius: var(--r-full);
  background: color-mix(in srgb, var(--c-surface) 78%, transparent);
  color: var(--c-ink-2);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: transform var(--dur-base) var(--ease-spring), color var(--dur-fast) var(--ease-out);
}

.heart svg { width: 20px; height: 20px; }

.heart.active { color: var(--c-accent); }

.heart:active { transform: scale(1.25); }

.meta {
  padding: var(--sp-2) var(--sp-3) var(--sp-3);
}

.name { margin: 0; font-size: var(--fs-14); font-weight: 600; }

.name a { color: var(--c-ink); text-decoration: none; }

.sub {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--sp-1);
}

.chip {
  font-size: var(--fs-11);
  color: var(--c-ink-2);
  background: var(--c-bg-soft);
  border-radius: var(--r-full);
  padding: 1px var(--sp-2);
}

.diff { display: inline-flex; gap: 3px; }

.diff i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--c-line-strong);
}

.diff i.on { background: var(--c-accent); }
</style>
