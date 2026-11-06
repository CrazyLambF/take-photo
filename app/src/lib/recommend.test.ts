import { describe, expect, it } from 'vitest'
import { recommendPoses, scorePair } from './recommend'
import type { Pose } from '@/types/pose'

function fakePose(id: string, category: Pose['category'], difficulty: 1 | 2 | 3, tags: string[], light = ['自然光']): Pose {
  return {
    id, name: id, category, difficulty, people: 1, gear: ['phone'], light,
    camera: { focal: '', angle: '', framing: '' },
    pose: { body: '' }, steps: [], mistakes: [], images: {}, tags,
  }
}

describe('scorePair', () => {
  it('同分类得分高于异分类', () => {
    const target = fakePose('ST-01', 'ST', 1, ['回眸', '全身'])
    const same = fakePose('ST-02', 'ST', 2, ['回眸'], ['自然光'])
    const other = fakePose('HOME-01', 'HOME', 1, ['回眸'], ['自然光'])
    expect(scorePair(target, same)).toBeGreaterThan(scorePair(target, other))
  })
  it('自身得分为 -1（排除）', () => {
    const target = fakePose('ST-01', 'ST', 1, [])
    expect(scorePair(target, target)).toBe(-1)
  })
  it('行为分计入且封顶', () => {
    const target = fakePose('ST-01', 'ST', 1, [])
    const cand = fakePose('ST-02', 'ST', 1, [])
    expect(scorePair(target, cand, { 'ST-02': 100 })).toBeLessThanOrEqual(
      scorePair(target, cand) + 5 + 0.5,
    )
  })
})

describe('recommendPoses', () => {
  const target = fakePose('ST-01', 'ST', 1, ['回眸'])
  const pool = [
    fakePose('ST-02', 'ST', 1, ['回眸']),
    fakePose('ST-03', 'ST', 1, ['站']),
    fakePose('ST-04', 'ST', 2, ['全身']),
    fakePose('ST-05', 'ST', 1, ['回眸']),
    fakePose('HOME-01', 'HOME', 2, ['窗'], ['自然光']),
    fakePose('CAFE-01', 'CAFE', 1, ['咖啡'], ['自然光']),
    fakePose('SCENE-01', 'SCENE', 3, ['夜'], ['夜景']),
  ]
  it('多样性约束：同分类最多 3 个，结果取满 limit', () => {
    const out = recommendPoses(target, pool, { limit: 6, maxPerCategory: 3 })
    expect(out).toHaveLength(6)
    const stCount = out.filter((p) => p.category === 'ST').length
    expect(stCount).toBeLessThanOrEqual(3)
  })
  it('平局按 id 稳定排序（可复现）', () => {
    const a = recommendPoses(target, pool)
    const b = recommendPoses(target, [...pool].reverse())
    expect(a.map((p) => p.id)).toEqual(b.map((p) => p.id))
  })
  it('不含自身，且同分类排最前', () => {
    const out = recommendPoses(target, pool, { limit: 3, maxPerCategory: 3 })
    expect(out.some((p) => p.id === 'ST-01')).toBe(false)
    expect(out[0].category).toBe('ST')
  })
})
