import { shallowRef } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'auto' | 'light' | 'dark'

/** 设置：主题 / 搜索历史（持久化） */
export const useSettingsStore = defineStore('settings', () => {
  const theme = shallowRef<ThemeMode>('auto')
  const searchHistory = shallowRef<string[]>([])
  const HISTORY_MAX = 8

  function setTheme(mode: ThemeMode): void {
    theme.value = mode
  }

  function addHistory(q: string): void {
    const v = q.trim()
    if (!v) return
    searchHistory.value = [v, ...searchHistory.value.filter((x) => x !== v)].slice(0, HISTORY_MAX)
  }

  function removeHistory(q: string): void {
    searchHistory.value = searchHistory.value.filter((x) => x !== q)
  }

  function clearHistory(): void {
    searchHistory.value = []
  }

  function resetAll(): void {
    theme.value = 'auto'
    searchHistory.value = []
  }

  return { theme, searchHistory, setTheme, addHistory, removeHistory, clearHistory, resetAll }
}, {
  persist: true,
})
