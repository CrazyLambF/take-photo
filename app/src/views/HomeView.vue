<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import PageContainer from '@/components/layout/PageContainer.vue'
import PoseWaterfall from '@/components/pose/PoseWaterfall.vue'
import { usePosesStore, CATEGORY_ORDER } from '@/stores/poses'
import type { CategoryId, Pose } from '@/types/pose'

/**
 * 首页 · 发现（§3.1）：今日推荐（每日轮换 + 换一批，决议 #14）→
 * 十类入口 → 主题合集（决议 #13：窗光与生活感/黄金时刻）→ 瀑布流（决议 #19）。
 */
const store = usePosesStore()
const router = useRouter()

/** 今日推荐：按日期轮换 3 个类目，步长 3 保证跨类目；换一批在同 3 类内轮换（决议 #14 保留策略） */
const dayNumber = Math.floor(Date.now() / 86_400_000)
const offset = shallowRef(0)
const swapping = shallowRef(false)

const dailyPicks = computed<Pose[]>(() => {
  const start = dayNumber % 10
  const cats = [CATEGORY_ORDER[start % 10], CATEGORY_ORDER[(start + 3) % 10], CATEGORY_ORDER[(start + 6) % 10]]
  return cats.map((c, i) => {
    const pool = store.byCategory(c)
    return pool[(dayNumber + offset.value * 3 + i) % pool.length]
  })
})

function shuffle(): void {
  swapping.value = true
  offset.value += 1
  window.setTimeout(() => (swapping.value = false), 420)
}

/** 主题合集（决议 #13）：光线·场景主题，点击进入图库带筛选 */
const COLLECTIONS = [
  { title: '窗光与生活感', desc: '居家 · 咖啡店 · 自然光', query: { light: '自然光', cats: 'HOME,CAFE' } },
  { title: '黄金时刻', desc: '日落前一小时 · 金色逆光', query: { light: '黄金时刻' } },
] as const

function goCollection(q: Record<string, string>): void {
  router.push({ path: '/poses', query: q })
}

/** 卡片流：首屏 24 张，触底 +12（决议 #19 滚动无限加载） */
const PAGE = 12
const shown = shallowRef(24)
const feed = computed<Pose[]>(() => store.all.slice(0, shown.value))
const finished = computed(() => shown.value >= store.all.length)

function loadMore(): void {
  shown.value = Math.min(shown.value + PAGE, store.all.length)
}

const catTiles = computed(() => store.categories)

function goCat(id: CategoryId): void {
  router.push({ path: '/poses', query: { cat: id } })
}
</script>

<template>
  <PageContainer>
    <header class="hero">
      <h1>今天用什么姿势<em>出片</em>？</h1>
      <p>100 个机位 · 每天挑 3 个练一练</p>
    </header>

    <section class="section" aria-labelledby="daily-h">
      <div class="sec-head">
        <h2 id="daily-h">今日推荐</h2>
        <button type="button" class="shuffle" :class="{ spin: swapping }" @click="shuffle">换一批</button>
      </div>
      <div class="daily" :class="{ swapping }">
        <button v-for="p in dailyPicks" :key="p.id" type="button" class="pick" @click="router.push(`/poses/${p.id}`)">
          <img :src="p.images.cover ? `/${p.images.cover}` : '/poses/placeholder.svg'" :alt="p.name" loading="lazy" width="320" height="426" />
          <span class="pn">{{ p.name }}</span>
          <span class="pc">{{ p.id }}</span>
        </button>
      </div>
    </section>

    <section class="section" aria-labelledby="cats-h">
      <div class="sec-head"><h2 id="cats-h">十类入口</h2></div>
      <div class="cats">
        <button v-for="c in catTiles" :key="c.id" type="button" class="cat" @click="goCat(c.id)">
          <b>{{ c.id }}</b>
          <span>{{ c.name }}</span>
          <small>{{ c.count }} 个</small>
        </button>
      </div>
    </section>

    <section class="section" aria-labelledby="col-h">
      <div class="sec-head"><h2 id="col-h">主题合集</h2></div>
      <div class="cols">
        <button v-for="c in COLLECTIONS" :key="c.title" type="button" class="col" @click="goCollection({ ...c.query })">
          <b>{{ c.title }}</b>
          <span>{{ c.desc }}</span>
        </button>
      </div>
    </section>

    <section class="section" aria-labelledby="feed-h">
      <div class="sec-head"><h2 id="feed-h">慢慢逛</h2></div>
      <PoseWaterfall :poses="feed" :finished="finished" @load-more="loadMore" />
    </section>
  </PageContainer>
</template>

<style scoped>
.hero h1 {
  font-family: var(--font-serif);
  font-size: var(--fs-28);
  margin: 0 0 var(--sp-1);
}

.hero h1 em {
  font-style: normal;
  color: var(--c-accent-deep);
}

.hero p {
  margin: 0 0 var(--sp-2);
  color: var(--c-ink-3);
  font-size: var(--fs-13);
}

.section { margin-top: var(--sp-8); }

.sec-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--sp-3);
}

.sec-head h2 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: var(--fs-22);
}

.shuffle {
  border: 1px solid var(--c-line);
  background: var(--c-surface);
  color: var(--c-ink-2);
  border-radius: var(--r-full);
  font-size: var(--fs-13);
  padding: var(--sp-1) var(--sp-3);
  min-height: 32px;
  cursor: pointer;
}

.shuffle.spin { animation: spin .42s var(--ease-spring); }

@keyframes spin {
  50% { transform: rotate(180deg) scale(.9); }
  100% { transform: rotate(360deg); }
}

.daily {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-3);
  transition: opacity var(--dur-slow) var(--ease-out), transform var(--dur-slow) var(--ease-out);
}

.daily.swapping { opacity: .25; transform: translateY(6px); }

.pick {
  border: none;
  padding: 0;
  background: none;
  cursor: pointer;
  text-align: left;
}

.pick img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: var(--r-md);
  background: var(--c-bg-soft);
  display: block;
}

.pick .pn {
  display: block;
  margin-top: var(--sp-1);
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--c-ink);
}

.pick .pc { font-size: var(--fs-11); color: var(--c-ink-3); }

.cats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--sp-2);
}

@media (min-width: 768px) { .cats { grid-template-columns: repeat(5, 1fr); } }
@media (min-width: 1200px) { .cats { grid-template-columns: repeat(10, 1fr); } }

.cat {
  border: 1px solid var(--c-line);
  background: var(--c-surface);
  border-radius: var(--r-md);
  padding: var(--sp-3);
  text-align: left;
  cursor: pointer;
  display: grid;
  gap: 2px;
  transition: transform var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out);
}

.cat:hover { transform: translateY(-2px); border-color: var(--c-line-strong); }

.cat b {
  font-family: var(--font-serif);
  font-size: var(--fs-18);
  color: var(--c-accent-deep);
}

.cat span { font-size: var(--fs-13); color: var(--c-ink); font-weight: 600; }
.cat small { font-size: var(--fs-11); color: var(--c-ink-3); }

.cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-3);
}

.col {
  border: none;
  border-radius: var(--r-lg);
  background: linear-gradient(135deg, var(--c-accent-soft), var(--c-sage-soft));
  padding: var(--sp-5);
  text-align: left;
  cursor: pointer;
  display: grid;
  gap: var(--sp-1);
  min-height: 96px;
  align-content: center;
  transition: transform var(--dur-fast) var(--ease-out);
}

.col:hover { transform: translateY(-2px); }

.col b {
  font-family: var(--font-serif);
  font-size: var(--fs-20);
  color: var(--c-ink);
}

.col span { font-size: var(--fs-12); color: var(--c-ink-2); }
</style>
