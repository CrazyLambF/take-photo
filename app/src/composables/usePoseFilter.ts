import { computed, shallowRef, type Ref } from 'vue'
import type { CategoryId, Pose } from '@/types/pose'

/** 筛选状态：维度间 AND、维度内 OR（§5.3） */
export interface PoseFilters {
  category: CategoryId | ''
  light: string[]
  difficulty: number[]
  gear: string[]
  props: string[]
}

export const EMPTY_FILTERS: PoseFilters = {
  category: '',
  light: [],
  difficulty: [],
  gear: [],
  props: [],
}

export const LIGHT_OPTIONS = ['自然光', '黄金时刻', '逆光', '夜景', '人造光'] as const
export const GEAR_OPTIONS = ['phone', 'camera'] as const
export const GEAR_LABELS: Record<string, string> = { phone: '手机', camera: '相机' }

export function filterPoses(poses: Pose[], f: PoseFilters, query = ''): Pose[] {
  const q = query.trim().toLowerCase()
  return poses.filter((p) => {
    if (f.category && p.category !== f.category) return false
    if (f.light.length && !f.light.some((l) => p.light.includes(l))) return false
    if (f.difficulty.length && !f.difficulty.includes(p.difficulty)) return false
    if (f.gear.length && !f.gear.some((g) => p.gear.includes(g as 'phone' | 'camera'))) return false
    if (f.props.length && !f.props.some((t) => (p.props ?? []).includes(t))) return false
    if (q) {
      const hay = [p.name, ...p.tags, ...p.light].join(' ').toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
}

export function activeFilterCount(f: PoseFilters): number {
  let n = 0
  if (f.category) n += 1
  n += f.light.length + f.difficulty.length + f.gear.length + f.props.length
  return n
}

/**
 * 筛选逻辑组合：filters 为唯一可变状态，filtered 全程 computed 派生。
 * @param source 数据源（通常为 posesStore.all 的 Ref）
 */
export function usePoseFilter(source: Ref<Pose[]>, initialQuery = '') {
  const filters = shallowRef<PoseFilters>({ ...EMPTY_FILTERS })
  const query = shallowRef(initialQuery)

  const filtered = computed(() => filterPoses(source.value, filters.value, query.value))
  const activeCount = computed(() => activeFilterCount(filters.value))

  function patch(partial: Partial<PoseFilters>): void {
    filters.value = { ...filters.value, ...partial }
  }

  function reset(): void {
    filters.value = { ...EMPTY_FILTERS }
  }

  return { filters, query, filtered, activeCount, patch, reset }
}
