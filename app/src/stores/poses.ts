import { computed } from 'vue'
import { defineStore } from 'pinia'
import posesData from '@/data/poses.json'
import tipsData from '@/data/category-tips.json'
import type { CategoryId, CategoryTips, Pose, PosesData, TipsData } from '@/types/pose'

/** 类目固定展示顺序（§2.1 A–J） */
export const CATEGORY_ORDER: CategoryId[] = [
  'ST', 'SIT', 'STREET', 'TRAVEL', 'HOME', 'CAFE', 'BACK', 'CLOSE', 'PROP', 'SCENE',
]

export interface CategoryInfo {
  id: CategoryId
  name: string
  count: number
}

/** 静态数据（构建期打包，单一事实来源 poses.json） */
const data = posesData as unknown as PosesData
const tips = (tipsData as unknown as TipsData).categories

export const usePosesStore = defineStore('poses', () => {
  const all: Pose[] = data.poses

  const byId = computed(() => new Map(all.map((p) => [p.id, p])))

  const categories = computed<CategoryInfo[]>(() =>
    CATEGORY_ORDER.map((id) => ({
      id,
      name: tips.find((t) => t.category === id)?.name ?? id,
      count: all.filter((p) => p.category === id).length,
    })),
  )

  const allTags = computed<string[]>(() => {
    const freq = new Map<string, number>()
    for (const p of all) for (const t of p.tags) freq.set(t, (freq.get(t) ?? 0) + 1)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t)
  })

  const allProps = computed<string[]>(() => {
    const set = new Set<string>()
    for (const p of all) for (const t of p.props ?? []) set.add(t)
    return [...set]
  })

  function get(id: string): Pose | undefined {
    return byId.value.get(id)
  }

  function byCategory(id: CategoryId): Pose[] {
    return all.filter((p) => p.category === id)
  }

  function tipsOf(id: CategoryId): CategoryTips | undefined {
    return tips.find((t) => t.category === id)
  }

  function categoryName(id: CategoryId): string {
    return tips.find((t) => t.category === id)?.name ?? id
  }

  return { all, categories, allTags, allProps, get, byCategory, tipsOf, categoryName }
})
