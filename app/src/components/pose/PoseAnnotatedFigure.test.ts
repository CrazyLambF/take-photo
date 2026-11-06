// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PoseAnnotatedFigure from './PoseAnnotatedFigure.vue'
import type { PoseAnnotation } from '@/types/pose'

const annotation: PoseAnnotation = {
  canvas: { w: 1728, h: 2304 },
  caption: '全身直立：重心与手臂先调',
  guides: { axisX: 0.4, horizonY: 0.5 },
  marks: [
    { id: 'a', type: 'rect', x: 0.2, y: 0.1, w: 0.1, h: 0.2, rx: 0.02, label: '下巴微收', tone: 'danger' },
    { id: 'b', type: 'arrow', from: [0.8, 0.3], to: [0.6, 0.4], label: '手臂离身一拳', tone: 'guide' },
    { id: 'c', type: 'hline', y: 0.5, x1: 0.1, x2: 0.9, label: '双肩等高', labelAt: [0.5, 0.45] },
    { id: 'd', type: 'ruler', axis: 'y', from: 0.1, to: 0.9, divisions: 8, label: '八头身', tone: 'measure' },
  ],
}

describe('PoseAnnotatedFigure', () => {
  it('有 marks 时渲染图元层与 HTML 标签层', () => {
    const w = mount(PoseAnnotatedFigure, { props: { src: '/poses/ST-01/cover.jpg', alt: '自然直立', annotation } })
    const svg = w.find('svg')
    expect(svg.exists()).toBe(true)

    expect(svg.findAll('rect').length).toBeGreaterThanOrEqual(1)
    expect(svg.findAll('polygon').length).toBe(1) // 箭头尖
    expect(svg.findAll('line').length).toBeGreaterThanOrEqual(3) // hline + 量尺主线/刻度

    // 文字必须在 HTML 层，不能进 SVG
    const labels = w.findAll('.paf-label')
    expect(labels).toHaveLength(4)
    expect(labels[0].text()).toContain('下巴微收')
    expect(labels[0].find('.idx').text()).toBe('1')
    expect(svg.text()).toBe('')
    expect(w.findAll('.paf-list li')).toHaveLength(4)
    expect(w.find('.paf-caption').text()).toContain('全身直立')
  })

  it('没有 annotation 时只渲染图片，不渲染任何标注层', () => {
    const w = mount(PoseAnnotatedFigure, { props: { src: '/poses/ST-02/cover.jpg', alt: '回眸' } })
    expect(w.find('img').exists()).toBe(true)
    expect(w.find('svg').exists()).toBe(false)
    expect(w.findAll('.paf-label')).toHaveLength(0)
    expect(w.find('.paf-list').exists()).toBe(false)
  })

  it('归一化坐标按 75×100 viewBox 与百分比正确映射', () => {
    const w = mount(PoseAnnotatedFigure, { props: { src: '/poses/ST-01/cover.jpg', alt: '自然直立', annotation } })
    const rect = w.find('svg rect')

    // x/w 走 75 单位宽，y/h 走 100 单位高
    expect(rect.attributes('x')).toBe('15')
    expect(rect.attributes('width')).toBe('7.5')
    expect(rect.attributes('y')).toBe('10')
    expect(rect.attributes('height')).toBe('20')

    // 标签锚点 = 归一化坐标 × 100%；无 labelAt 时 rect 取自身左上角
    expect(w.findAll('.paf-label')[0].attributes('style')).toContain('left: 20%')
    expect(w.findAll('.paf-label')[0].attributes('style')).toContain('top: 10%')
    expect(w.findAll('.paf-label')[2].attributes('style')).toContain('left: 50%')

    // 徽标与标签同锚点，移动端只露序号
    expect(w.findAll('.paf-badge')[1].text()).toBe('②')
    expect(w.findAll('.paf-badge')[1].attributes('style')).toContain('left: 60%')
  })
})
