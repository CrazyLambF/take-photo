import { shallowRef } from 'vue'
import { defineStore } from 'pinia'

/** 对比：上限 3 个（决策 #23），持久化 */
export const useCompareStore = defineStore('compare', () => {
  const ids = shallowRef<string[]>([])
  const MAX = 3

  function has(id: string): boolean {
    return ids.value.includes(id)
  }

  /** @returns 操作后结果信息，供 Toast 提示 */
  function toggle(id: string): { added: boolean; full: boolean } {
    if (has(id)) {
      ids.value = ids.value.filter((x) => x !== id)
      return { added: false, full: false }
    }
    if (ids.value.length >= MAX) return { added: false, full: true }
    ids.value = [...ids.value, id]
    return { added: true, full: false }
  }

  function remove(id: string): void {
    ids.value = ids.value.filter((x) => x !== id)
  }

  function clear(): void {
    ids.value = []
  }

  return { ids, has, toggle, remove, clear }
}, {
  persist: true,
})
