/**
 * 相关推荐算法 v1（决策 #24 定案，规格见 mockups/设计说明.md §8.1）
 * 内容基线加权 + 多样性重排；可解释、冷启动安全、平局按 id 稳定排序（可复现）。
 */
import type { Pose } from '@/types/pose'

const WEIGHTS = {
  sameCategory: 10,
  sharedTag: 3,
  maxSharedTags: 3,
  sameLight: 2,
  sameScene: 2,
  difficultyClose: 1,
  /** 收藏行为分上限（冷启动为 0，不改变初版结果） */
  saveMax: 5,
} as const

/** 场景类标签（与 §2.3 标签体系的「场景」维度对应） */
const SCENE_TAGS = new Set(['旅行', '居家', '街拍', '夜', '雨', '雪', '海', '野餐', '机场', '地铁', '咖啡'])

export interface RecommendOptions {
  limit?: number
  /** 最终结果中同分类的最大数量（多样性约束） */
  maxPerCategory?: number
  /** 姿势 id → 收藏次数（上线后接入；冷启动传空） */
  saves?: Record<string, number>
}

export function scorePair(target: Pose, cand: Pose, saves: Record<string, number> = {}): number {
  if (target.id === cand.id) return -1
  let score = 0
  if (cand.category === target.category) score += WEIGHTS.sameCategory
  const shared = cand.tags.filter((t) => target.tags.includes(t)).slice(0, WEIGHTS.maxSharedTags)
  score += shared.length * WEIGHTS.sharedTag
  if (cand.light.some((l) => target.light.includes(l))) score += WEIGHTS.sameLight
  const sceneShared = shared.some((t) => SCENE_TAGS.has(t))
  if (sceneShared) score += WEIGHTS.sameScene
  if (Math.abs(cand.difficulty - target.difficulty) <= 1) score += WEIGHTS.difficultyClose
  score += Math.min(WEIGHTS.saveMax, (saves[cand.id] ?? 0) * 0.5)
  return score
}

/**
 * 推荐主入口：全库打分 → (score desc, id asc) 稳定排序 → 贪心选取并保证
 * 同分类 ≤ maxPerCategory（默认 3/6），不足时放宽继续取满 limit。
 */
export function recommendPoses(target: Pose, pool: Pose[], options: RecommendOptions = {}): Pose[] {
  const { limit = 6, maxPerCategory = 3, saves = {} } = options
  const scored = pool
    .map((cand) => ({ pose: cand, score: scorePair(target, cand, saves) }))
    .filter((x) => x.score >= 0)
    .sort((a, b) => b.score - a.score || (a.pose.id < b.pose.id ? -1 : 1))

  const picked: Pose[] = []
  const catCount = new Map<string, number>()
  for (const { pose } of scored) {
    if (picked.length >= limit) break
    const used = catCount.get(pose.category) ?? 0
    if (used >= maxPerCategory) continue
    catCount.set(pose.category, used + 1)
    picked.push(pose)
  }
  // 兜底：多样性约束导致不足时，忽略分类上限补足（保持稳定顺序）
  if (picked.length < limit) {
    const chosen = new Set(picked.map((p) => p.id))
    for (const { pose } of scored) {
      if (picked.length >= limit) break
      if (!chosen.has(pose.id)) picked.push(pose)
    }
  }
  return picked
}
