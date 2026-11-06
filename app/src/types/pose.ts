/** 内容数据类型 —— 对应《拍照姿势App项目计划.md》§2.3 数据模型 */

export type CategoryId =
  | 'ST' | 'SIT' | 'STREET' | 'TRAVEL' | 'HOME'
  | 'CAFE' | 'BACK' | 'CLOSE' | 'PROP' | 'SCENE'

export type Difficulty = 1 | 2 | 3

export interface PoseCamera {
  /** 焦段（手机给出等效变焦倍数），构建期从计划文本提取，可能为空待打磨 */
  focal: string
  /** 机位高度与角度 */
  angle: string
  /** 构图与画幅 */
  framing: string
  /** 参数建议（可读化） */
  settings?: string
}

export interface PoseBody {
  body: string
  hands?: string
  head?: string
  expression?: string
}

export interface PoseImages {
  cover?: string
  lineArt?: string
  wrong?: string
}

export interface Pose {
  id: string
  name: string
  category: CategoryId
  difficulty: Difficulty
  people: number
  gear: ('phone' | 'camera')[]
  /** 光线条件：自然光/黄金时刻/逆光/夜景/人造光 */
  light: string[]
  camera: PoseCamera
  pose: PoseBody
  steps: string[]
  mistakes: string[]
  props?: string[]
  images: PoseImages
  tags: string[]
}

export interface PosesData {
  meta: { generated: string; copyStatus: string; source: string }
  poses: Pose[]
}

export interface CategoryTip {
  type: 'composition' | 'light'
  text: string
}

export interface CategoryTips {
  category: CategoryId
  name: string
  tips: CategoryTip[]
}

export interface TipsData {
  meta: { generated: string }
  categories: CategoryTips[]
}

/* ------------------------------------------------------------------ *
 * 姿势封面标注（图元 + 文案），见 data/pose-annotations.json
 * 坐标一律归一化到封面画幅 0–1，封面固定 1728×2304（3:4）
 * ------------------------------------------------------------------ */

/** 归一化坐标：0 = 左/上边缘，1 = 右/下边缘 */
export type Norm = number

/** 图元语气：danger=易错点 / guide=修正指引 / measure=比例量尺 */
export type MarkTone = 'danger' | 'guide' | 'measure'

export interface MarkBase {
  id: string
  /** 标签全文；<768px 时只在图下列表出现，图上仅显示序号徽标 */
  label: string
  tone?: MarkTone
  /** 标签锚点（归一化）。缺省时按图元类型取默认锚点 */
  labelAt?: [Norm, Norm]
}

export interface RectMark extends MarkBase {
  type: 'rect'
  x: Norm
  y: Norm
  w: Norm
  h: Norm
  /** 圆角，单位与 w/h 相同的归一化值 */
  rx?: Norm
}

export interface ArrowMark extends MarkBase {
  type: 'arrow'
  from: [Norm, Norm]
  to: [Norm, Norm]
}

export interface HLineMark extends MarkBase {
  type: 'hline'
  y: Norm
  x1?: Norm
  x2?: Norm
}

export interface VLineMark extends MarkBase {
  type: 'vline'
  x: Norm
  y1?: Norm
  y2?: Norm
}

export interface CircleMark extends MarkBase {
  type: 'circle'
  cx: Norm
  cy: Norm
  r: Norm
}

export interface RulerMark extends MarkBase {
  type: 'ruler'
  axis: 'y'
  from: Norm
  to: Norm
  /** 刻度段数（人体比例用 7–8 段） */
  divisions: number
}

export type PoseMark =
  | RectMark
  | ArrowMark
  | HLineMark
  | VLineMark
  | CircleMark
  | RulerMark

/** 构图参考线（可选）：头身比、身体中轴、地平线 */
export interface PoseGuides {
  headRatio?: number
  axisX?: Norm
  horizonY?: Norm
}

export interface PoseAnnotation {
  canvas?: { w: number; h: number }
  caption?: string
  guides?: PoseGuides
  marks: PoseMark[]
}

export interface PoseAnnotationsData {
  meta: { version: number; generated: string }
  poses: Record<string, PoseAnnotation>
}
