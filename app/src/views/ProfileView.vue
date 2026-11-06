<script setup lang="ts">
import { useSettingsStore, type ThemeMode } from '@/stores/settings'
import { useFavoritesStore } from '@/stores/favorites'
import { useCompareStore } from '@/stores/compare'
import { showToast } from 'vant'
import 'vant/es/toast/style'
import PageContainer from '@/components/layout/PageContainer.vue'

/** 我的（§3.1）：设置（深色模式/清理缓存）、关于、隐私声明 */
const settings = useSettingsStore()
const fav = useFavoritesStore()
const compare = useCompareStore()

const THEMES: { value: ThemeMode; label: string }[] = [
  { value: 'auto', label: '跟随系统' },
  { value: 'light', label: '浅色' },
  { value: 'dark', label: '深色' },
]

function clearCache(): void {
  fav.clearAll()
  compare.clear()
  settings.clearHistory()
  showToast('已清空本地缓存数据')
}
</script>

<template>
  <PageContainer>
    <header class="head"><h1>我的</h1></header>

    <section class="card" aria-labelledby="theme-h">
      <h2 id="theme-h">外观</h2>
      <div class="themes" role="radiogroup" aria-label="主题模式">
        <button
          v-for="t in THEMES"
          :key="t.value"
          type="button"
          role="radio"
          class="theme-btn"
          :class="{ on: settings.theme === t.value }"
          :aria-checked="settings.theme === t.value"
          @click="settings.setTheme(t.value)"
        >{{ t.label }}</button>
      </div>
    </section>

    <section class="card" aria-labelledby="data-h">
      <h2 id="data-h">数据</h2>
      <p class="desc">收藏 {{ fav.favorites.length }} 条 · 清单 {{ fav.list.length }} 条 · 对比 {{ compare.ids.length }} 条。清除后不可恢复。</p>
      <button type="button" class="danger" @click="clearCache">清除本地缓存</button>
    </section>

    <section class="card" aria-labelledby="about-h">
      <h2 id="about-h">关于</h2>
      <p class="desc">摆拍手册 PoseGuide · v1.0 内测<br />100 个机位与摆拍姿势 · 内容持续打磨中</p>
    </section>

    <section class="card" aria-labelledby="priv-h">
      <h2 id="priv-h">隐私声明</h2>
      <p class="desc">所有数据（收藏/清单/设置）仅保存在你的浏览器本地，不上传服务器。上线后将同步发布完整隐私声明（§6.4）。</p>
    </section>
  </PageContainer>
</template>

<style scoped>
.head h1 {
  margin: 0 0 var(--sp-4);
  font-family: var(--font-serif);
  font-size: var(--fs-28);
}

.card {
  background: var(--c-surface);
  border-radius: var(--r-lg);
  padding: var(--sp-4) var(--sp-5);
  margin-bottom: var(--sp-3);
  box-shadow: var(--shadow-1);
}

.card h2 {
  margin: 0 0 var(--sp-3);
  font-size: var(--fs-16);
}

.desc {
  margin: 0 0 var(--sp-3);
  font-size: var(--fs-13);
  color: var(--c-ink-2);
  line-height: 1.7;
}

.themes {
  display: flex;
  gap: var(--sp-2);
}

.theme-btn {
  flex: 1;
  min-height: 44px;
  border: 1px solid var(--c-line);
  background: var(--c-surface-2);
  border-radius: var(--r-sm);
  font-size: var(--fs-14);
  color: var(--c-ink-2);
  cursor: pointer;
}

.theme-btn.on {
  border-color: var(--c-accent);
  background: var(--c-accent-soft);
  color: var(--c-accent-deep);
  font-weight: 700;
}

.danger {
  border: 1px solid var(--c-danger);
  background: none;
  color: var(--c-danger);
  border-radius: var(--r-full);
  min-height: 40px;
  padding: 0 var(--sp-5);
  font-size: var(--fs-14);
  cursor: pointer;
}
</style>
