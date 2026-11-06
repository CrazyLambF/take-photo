<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageContainer from '@/components/layout/PageContainer.vue'
import PoseWaterfall from '@/components/pose/PoseWaterfall.vue'
import { usePosesStore } from '@/stores/poses'
import { useSettingsStore } from '@/stores/settings'
import { EMPTY_FILTERS, filterPoses } from '@/composables/usePoseFilter'

/** 搜索（§5.3）：名称/标签匹配、历史、热门标签 */
defineOptions({ name: 'SearchView' })

const store = usePosesStore()
const settings = useSettingsStore()
const route = useRoute()
const router = useRouter()

const q = shallowRef((Array.isArray(route.query.q) ? route.query.q[0] : route.query.q) ?? '')

const results = computed(() => (q.value.trim() ? filterPoses(store.all, { ...EMPTY_FILTERS }, q.value) : []))

function search(v: string): void {
  q.value = v
  settings.addHistory(v)
  router.replace({ query: v.trim() ? { q: v.trim() } : {} })
}

const hotTags = computed(() => store.allTags.slice(0, 12))

watch(() => route.query.q, (v) => {
  if (typeof v === 'string' && v !== q.value) q.value = v
})
</script>

<template>
  <PageContainer>
    <form class="bar" role="search" @submit.prevent="search(q)">
      <input
        v-model="q"
        type="search"
        placeholder="搜索姿势名称 / 标签，如「回眸」「窗」"
        aria-label="搜索姿势"
        autofocus
      />
      <button type="submit" class="go">搜索</button>
    </form>

    <section v-if="!q.trim()" class="section" aria-labelledby="hist-h">
      <div class="sec-head">
        <h2 id="hist-h">搜索历史</h2>
        <button v-if="settings.searchHistory.length" type="button" class="txt" @click="settings.clearHistory()">清空</button>
      </div>
      <div v-if="settings.searchHistory.length" class="tags">
        <span v-for="h in settings.searchHistory" :key="h" class="tag hist">
          <button type="button" @click="search(h)">{{ h }}</button>
          <button type="button" :aria-label="`删除历史 ${h}`" @click="settings.removeHistory(h)">✕</button>
        </span>
      </div>
      <p v-else class="empty-line">暂无历史</p>
    </section>

    <section v-if="!q.trim()" class="section" aria-labelledby="hot-h">
      <div class="sec-head"><h2 id="hot-h">热门标签</h2></div>
      <div class="tags">
        <button v-for="t in hotTags" :key="t" type="button" class="tag hot" @click="search(t)"># {{ t }}</button>
      </div>
    </section>

    <section v-else class="section" aria-label="搜索结果">
      <p class="count" role="status">「{{ q }}」命中 {{ results.length }} 个姿势</p>
      <PoseWaterfall v-if="results.length" :poses="results" :finished="true" />
      <p v-else class="empty-line">没有找到相关姿势，换个关键词试试</p>
    </section>
  </PageContainer>
</template>

<style scoped>
.bar {
  display: flex;
  gap: var(--sp-2);
  margin-bottom: var(--sp-4);
}

.bar input {
  flex: 1;
  min-height: 44px;
  border: 1px solid var(--c-line-strong);
  border-radius: var(--r-full);
  background: var(--c-surface);
  padding: 0 var(--sp-4);
  font-size: var(--fs-15);
  color: var(--c-ink);
}

.bar input:focus {
  outline: 2px solid var(--c-accent);
  outline-offset: 1px;
}

.go {
  min-height: 44px;
  border: none;
  border-radius: var(--r-full);
  background: var(--c-accent);
  color: var(--c-on-accent);
  font-weight: 700;
  padding: 0 var(--sp-5);
  cursor: pointer;
}

.sec-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.sec-head h2 {
  margin: 0 0 var(--sp-3);
  font-size: var(--fs-16);
}

.txt {
  border: none;
  background: none;
  color: var(--c-ink-3);
  font-size: var(--fs-12);
  cursor: pointer;
}

.section { margin-bottom: var(--sp-6); }

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.tag {
  border: 1px solid var(--c-line);
  background: var(--c-surface);
  border-radius: var(--r-full);
  font-size: var(--fs-13);
  color: var(--c-ink-2);
  padding: 4px var(--sp-3);
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  cursor: pointer;
}

.tag.hot { color: var(--c-accent-deep); background: var(--c-accent-soft); border-color: transparent; }

.tag.hist button {
  border: none;
  background: none;
  cursor: pointer;
  color: inherit;
  font-size: inherit;
  padding: 0;
}

.count {
  color: var(--c-ink-3);
  font-size: var(--fs-13);
  margin: 0 0 var(--sp-3);
}

.empty-line {
  color: var(--c-ink-3);
  font-size: var(--fs-14);
}
</style>
