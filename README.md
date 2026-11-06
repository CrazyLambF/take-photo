# 拍照姿势指南（PoseGuide）

100 条手机 / 相机拍照摆姿教程的 Vue 3 移动优先应用。每条姿势提供四帧式图集：**示例图 / 线稿示意 / 取景示意 / 易错标注**，配合分步口诀与易错点讲解。

- 内容：10 类 × 10 条 = 100 条（ST 站姿 / SIT 坐姿 / STREET 街拍 / TRAVEL 旅行 / HOME 居家 / CAFE 咖啡 / BACK 背影 / CLOSE 特写 / PROP 道具 / SCENE 场景）
- 技术：Vue 3.5 + TypeScript + Vite 8 + Vue Router 4 + Pinia + Vant 4（按需）+ Vitest
- 产品与数据设计见 **[拍照姿势App项目计划.md](拍照姿势App项目计划.md)**（含 33 条决策记录与依据）

## 目录结构

```
app/                     应用主体
├─ src/
│  ├─ components/pose/   PoseAnnotatedFigure.vue（四帧标注渲染）
│  ├─ data/              poses.json（100 条内容）、pose-annotations.json（78 条标注）
│  ├─ views/             PoseDetailView.vue 等
│  └─ types/             pose.ts（含标注判别联合类型）
├─ public/poses/{ID}/    cover.jpg 封面、lineart.png 线稿
└─ scripts/build_data.py 数据管线：登记封面与线稿到 poses.json
images/
├─ manifest.json         图像生成台账（模型、seed、花费）
├─ lineart/*.png         86 张线稿成品（源）
└─ lineart/skeleton/     90 套矢量骨架（SVG）
tools/
├─ extract_joints.py     MediaPipe 姿态估计 → joints-real.json
└─ build_annotations.py  由关节坐标派生标注 → pose-annotations.json
docs/                    方案评估与设计文档
mockups/                 原型图
```

## 本地运行

```bash
cd app
pnpm install
pnpm dev          # 开发
pnpm test         # 单元测试（14 例）
pnpm build        # 类型检查 + 构建
pnpm preview      # 预览构建产物
```

## 数据管线（改动内容后重跑）

```bash
# 1. 扫描 images/ 与 app/public/，把封面、线稿登记进 poses.json
python3 app/scripts/build_data.py

# 2. 从封面提取真实关节坐标（需要 mediapipe，见下）
PYTHONPATH=tools/pydeps python3 tools/extract_joints.py

# 3. 由关节坐标派生易错标注（ST-01..ST-10 为人工校准版，不会被覆盖）
python3 tools/build_annotations.py
```

### 姿态估计依赖

`joints-real.json` 由 MediaPipe PoseLandmarker 对封面做真实检测生成。若需重跑：

```bash
python3 -m pip install --target tools/pydeps \
  --trusted-host pypi.org --trusted-host files.pythonhosted.org mediapipe
mkdir -p tools/models
curl -o tools/models/pose_landmarker_full.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
```

## 已知边界

- **线稿 86/100**：CLOSE 特写类 10 条按设计改「取景示意」（画面里只有脸，人体线稿语义不成立）；4 条（SIT-07 / BACK-06 / STREET-09 / SCENE-08）被内容审核拒绝，显示诚实空态而非占位图。
- **标注 78/100**：22 条无标注（CLOSE 10 条 + 12 条姿态检测置信度不足），详情页退化为两帧，不显示假标注。
- **头身比只在 6.5–9.0 可信区间报数字**，其余仅给刻度不给数——实测检出分布 −1.8~12.7，跳出区间说明头高估算失真。
- 标注坐标绑定当前封面，**更换封面后必须重跑 `extract_joints.py` + `build_annotations.py`**。
- `steps` / `mistakes` 文案仍由类级模板派生，同类别内文案重复（决策 #15 待人工打磨）。
- 图像生成累计花费 11.40 元（详情见 `images/manifest.json` 与计划文档决策 #26–#33）。

## 部署

应用是纯静态站点，`pnpm build` 产物在 `app/dist/`，已配置 GitHub Pages 自动部署。

- **线上地址**：https://crazylambf.github.io/take-photo/
- **触发方式**：推送到 `main` 分支自动构建部署（也可在 Actions 页手动 `workflow_dispatch`）
- **工作流**：`.github/workflows/deploy.yml`（install → test → build → 传产物 → 发布）

### 为什么需要 base

仓库是 GitHub Pages **项目站点**，跑在 `https://crazylambf.github.io/take-photo/` 子路径下，不是域名根路径。因此：

1. CI 构建时注入 `VITE_BASE_PATH=/take-photo/`，`vite.config.ts` 读取后传给 `base`；
2. 所有静态资源必须经 `src/utils/asset.ts` 的 `asset()` 拼接 `import.meta.env.BASE_URL`。**不要写成 `/${path}` 的根路径**——本地根路径部署下看不出问题，一上线就全部 404。
3. 构建后把 `index.html` 复制成 `404.html`。路由用 `createWebHistory`，直接刷新 `/poses/ST-01` 这类深层链接时 Pages 找不到实体文件，靠 404.html 兜底让前端路由接管。

本地预览线上行为：

```bash
cd app
VITE_BASE_PATH=/take-photo/ pnpm build
pnpm preview      # 预览地址是 http://localhost:4173/take-photo/
```

部署到域名根路径（如自有域名）时，去掉 env 变量直接 `pnpm build` 即可。

### 首次启用 Pages

仓库 Settings → Pages → **Source 选 “GitHub Actions”**（只需设置一次）。此后推 `main` 即自动发布。

## 素材说明

封面与线稿为 AI 生成（豆包 seedream），仅用于演示。上线前请确认肖像与合规要求，相关记录见 [images/合规与AI标识.md](images/合规与AI标识.md)。
