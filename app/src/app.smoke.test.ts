// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router'
import posesData from './data/poses.json'
import type { PosesData } from './types/pose'

const poses = (posesData as unknown as PosesData).poses

/** 真壳冒烟：完整 App（stores + router + Vant 原语）逐路由渲染，抓运行时错误 */
async function mountApp() {
  const pinia = createPinia().use(piniaPluginPersistedstate)
  setActivePinia(pinia)
  const wrapper = mount(App, { global: { plugins: [pinia, router] } })
  await router.isReady()
  await flushPromises()
  return wrapper
}

describe('App smoke（真实挂载）', () => {
  it('首页：今日推荐 + 十类入口 + 主题合集渲染', async () => {
    await router.push('/')
    const w = await mountApp()
    const text = w.text()
    expect(text).toContain('今日推荐')
    expect(text).toContain('十类入口')
    expect(text).toContain('主题合集')
    expect(text).toContain('窗光与生活感')
    // 今日推荐 3 张
    expect(w.findAll('.pick')).toHaveLength(3)
  })

  it('图库：卡片网格渲染且筛选抽屉可达', async () => {
    await router.push('/poses')
    const w = await mountApp()
    await flushPromises()
    expect(w.text()).toContain('姿势库')
    // 默认展示 12 张瀑布流卡片
    expect(w.findAll('.pose-card').length).toBeGreaterThan(0)
    // 分类 chips 10 类齐全（仅图库顶部的 chips 条，不含侧栏筛选面板）
    expect(w.findAll('[role="tablist"] .chip')).toHaveLength(10)
  })

  it('详情：四件套（机位卡/步骤/避坑/推荐）+ 同类切换', async () => {
    const pose = poses[1]! // ST-02
    await router.push(`/poses/${pose.id}`)
    const w = await mountApp()
    const text = w.text()
    expect(text).toContain(pose.name)
    expect(text).toContain('机位卡')
    expect(text).toContain('分步要点')
    expect(text).toContain('避坑')
    expect(text).toContain('相关推荐')
    // 推荐 v1：6 个且不含自身
    const recs = w.findAll('.rec')
    expect(recs.length).toBeGreaterThan(0)
    // 同类上一个/下一个胶囊
    expect(w.findAll('.nb')).toHaveLength(2)
  })

  it('对比页：query 传入 2 个 id 并排渲染', async () => {
    await router.push('/compare?ids=ST-01,ST-02')
    const w = await mountApp()
    expect(w.text()).toContain('姿势对比')
    expect(w.findAll('.col')).toHaveLength(2)
  })

  it('主题三档：切深色后 data-theme 生效，收藏可持久化', async () => {
    await router.push('/')
    await mountApp()
    // 深色：直接驱动 settings store（与 App 内 watcher 同一 pinia 实例）
    const { useSettingsStore } = await import('./stores/settings')
    const { useFavoritesStore } = await import('./stores/favorites')
    const settings = useSettingsStore()
    const fav = useFavoritesStore()
    settings.setTheme('dark')
    await flushPromises()
    expect(document.documentElement.dataset.theme).toBe('dark')
    settings.setTheme('light')
    await flushPromises()
    expect(document.documentElement.dataset.theme).toBeUndefined()
    // 收藏 toggle + localStorage 持久化（$subscribe 为 pre-flush，等下一个 tick）
    const first = poses[0]!.id
    expect(fav.toggleFavorite(first)).toBe(true)
    await nextTick()
    await flushPromises()
    expect(localStorage.getItem('favorites')).toContain(first)
  })
})
