import { shallowRef } from 'vue'
import { defineStore } from 'pinia'

export interface ListItem {
  id: string
  done: boolean
}

/** 收藏 + 待拍清单（决策 #3：localStorage 持久化，纯前端） */
export const useFavoritesStore = defineStore('favorites', () => {
  const favorites = shallowRef<string[]>([])
  const list = shallowRef<ListItem[]>([])

  function has(id: string): boolean {
    return favorites.value.includes(id)
  }

  function toggleFavorite(id: string): boolean {
    if (has(id)) {
      favorites.value = favorites.value.filter((x) => x !== id)
      return false
    }
    favorites.value = [...favorites.value, id]
    return true
  }

  function inList(id: string): boolean {
    return list.value.some((x) => x.id === id)
  }

  function addToList(id: string): void {
    if (!inList(id)) list.value = [...list.value, { id, done: false }]
  }

  function removeFromList(id: string): void {
    list.value = list.value.filter((x) => x.id !== id)
  }

  function toggleDone(id: string): void {
    list.value = list.value.map((x) => (x.id === id ? { ...x, done: !x.done } : x))
  }

  function clearAll(): void {
    favorites.value = []
    list.value = []
  }

  return { favorites, list, has, toggleFavorite, inList, addToList, removeFromList, toggleDone, clearAll }
}, {
  persist: true,
})
