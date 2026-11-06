<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageContainer from '@/components/layout/PageContainer.vue'
import PoseWaterfall from '@/components/pose/PoseWaterfall.vue'
import FilterPanel from '@/components/common/FilterPanel.vue'
import { usePosesStore } from '@/stores/poses'
import { usePoseFilter } from '@/composables/usePoseFilter'
import { useAppBreakpoints } from '@/composables/useAppBreakpoints'
import type { CategoryId } from '@/types/pose'

/**
 * 姿势库（§3.1）：分类 chips ＋ 多维筛选（移动端底部抽屉 / ≥768px 侧栏，§3.3-5）
 * ＋瀑布流滚动加载（决议 #19）。
 */
defineOptions({ name: 'PoseLibraryView' })

const store = usePosesStore()
const route = useRoute()
const router = useRouter()
const { isMobile } = useAppBreakpoints()

const { filters, filtered, activeCount, patch, reset } = usePoseFilter(
  computed(() => store.all),
)

const PAGE = 12
const shown = shallowRef(PAGE)
const result = computed(() => filtered.value.slice(0, shown.value))
const finished = computed(() => shown.value >= filtered.value.length)

function loadMore(): void {
  shown.value = Math.min(shown.value + PAGE, filtered.value.length)
}

/** 路由入口：/poses?cat=ST&light=自然光&cats=HOME,CAFE（主题合集落地） */
function applyRouteQuery(): void {
  const q = route.query
  const cat = (Array.isArray(q.cat) ? q.cat[0] : q.cat) as CategoryId | undefined
  const light = (Array.isArray(q.light) ? q.light[0] : q.light) as string | undefined
  const cats = (Array.isArray(q.cats) ? q.cats[0] : q.cats) as string | undefined
  if (cat && store.categories.some((c) => c.id === cat)) patch({ category: cat })
  if (light) patch({ light: [light] })
  if (cats) {
    // 主题合集多类目：转成无类目 + 保留值域外过滤会丢语义，这里逐条入栈用 light 维度承载
    // （合集仅两个：窗光=HOME+CAFE / 黄金时刻=光线维度）
    if (cats === 'HOME,CAFE') patch({ category: '', light: ['自然光'] })
  }
  shown.value = PAGE
}

watch(() => route.query, applyRouteQuery, { immediate: true })

watch(filters, () => {
  shown.value = PAGE
  // 筛选变化同步到地址栏（可分享）
  const q: Record<string, string> = {}
  if (filters.value.category) q.cat = filters.value.category
  if (filters.value.light.length === 1) q.light = filters.value.light[0]
  router.replace({ query: q })
})

const drawerOpen = shallowRef(false)
</script>

<template>
  <PageContainer>
    <header class="head">
      <h1>姿势库</h1>
      <span class="count" role="status">{{ filtered.length }} 个姿势</span>
      <button v-if="isMobile" type="button" class="filter-btn" :aria-label="`筛选，${activeCount} 项生效`" @click="drawerOpen = true">
        筛选<span v-if="activeCount" class="badge">{{ activeCount }}</span>
      </button>
    </header>

    <div class="chips" role="tablist" aria-label="分类">
      <button
        v-for="c in store.categories"
        :key="c.id"
        type="button"
        class="chip"
        :class="{ on: filters.category === c.id }"
        :aria-pressed="filters.category === c.id"
        @click="patch({ category: filters.category === c.id ? '' : c.id })"
      >{{ c.name.split(' ·')[0] }}</button>
    </div>

    <div class="body" :class="{ 'with-side': !isMobile }">
      <aside v-if="!isMobile" class="side" aria-label="筛选">
        <FilterPanel v-model="filters" />
      </aside>
      <div class="main">
        <PoseWaterfall :poses="result" :finished="finished" @load-more="loadMore" />
        <div v-if="!filtered.length" class="empty">
          <p>没有符合筛选的姿势</p>
          <button type="button" class="relax" @click="reset()">放宽条件</button>
        </div>
      </div>
    </div>

    <van-popup v-if="isMobile" :show="drawerOpen" position="bottom" round :style="{ maxHeight: '78dvh' }">
      <div class="drawer">
        <h3>筛选</h3>
        <div class="drawer-body">
          <FilterPanel v-model="filters" />
        </div>
        <div class="drawer-foot">
          <button type="button" class="ghost" @click="reset()">重置</button>
          <button type="button" class="primary" @click="drawerOpen = false">查看 {{ filtered.length }} 个结果</button>
        </div>
      </div>
    </van-popup>
  </PageContainer>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-bottom: var(--sp-3);
}

.head h1 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: var(--fs-28);
}

.count { color: var(--c-ink-3); font-size: var(--fs-13); }

.filter-btn {
  margin-left: auto;
  border: 1px solid var(--c-line);
  background: var(--c-surface);
  border-radius: var(--r-full);
  padding: var(--sp-1) var(--sp-3);
  min-height: 36px;
  font-size: var(--fs-13);
  color: var(--c-ink-2);
  cursor: pointer;
}

.badge {
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  margin-left: 4px;
  border-radius: var(--r-full);
  background: var(--c-accent);
  color: var(--c-on-accent);
  font-size: var(--fs-11);
}

.chips {
  display: flex;
  gap: var(--sp-2);
  overflow-x: auto;
  padding-bottom: var(--sp-2);
  scrollbar-width: none;
  position: sticky;
  top: 0;
  z-index: var(--z-chips);
  background: var(--c-bg);
}

.chips::-webkit-scrollbar { display: none; }

.chip {
  flex: 0 0 auto;
  border: 1px solid var(--c-line);
  background: var(--c-surface);
  color: var(--c-ink-2);
  border-radius: var(--r-full);
  padding: 6px var(--sp-3);
  font-size: var(--fs-13);
  min-height: 34px;
  cursor: pointer;
}

.chip.on {
  background: var(--c-ink);
  border-color: var(--c-ink);
  color: var(--c-bg);
  font-weight: 600;
}

.body.with-side {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: var(--sp-6);
  align-items: start;
}

.side {
  position: sticky;
  top: calc(var(--topnav-h) + var(--sp-4));
  max-height: calc(100dvh - var(--topnav-h) - var(--sp-8));
  overflow: auto;
}

.empty {
  text-align: center;
  padding: var(--sp-16) 0;
  color: var(--c-ink-3);
}

.relax {
  margin-top: var(--sp-3);
  border: 1px solid var(--c-line-strong);
  background: var(--c-surface);
  border-radius: var(--r-full);
  padding: var(--sp-2) var(--sp-5);
  color: var(--c-accent-deep);
  cursor: pointer;
}

.drawer { padding: var(--sp-4); }

.drawer h3 {
  margin: 0 0 var(--sp-3);
  font-family: var(--font-serif);
  font-size: var(--fs-18);
}

.drawer-body { max-height: 52dvh; overflow: auto; }

.drawer-foot {
  display: flex;
  gap: var(--sp-3);
  padding-top: var(--sp-3);
}

.drawer-foot button {
  flex: 1;
  min-height: 44px;
  border-radius: var(--r-full);
  font-size: var(--fs-15);
  cursor: pointer;
}

.ghost {
  border: 1px solid var(--c-line);
  background: var(--c-surface);
  color: var(--c-ink-2);
}

.primary {
  border: none;
  background: var(--c-accent);
  color: var(--c-on-accent);
  font-weight: 700;
}
</style>
