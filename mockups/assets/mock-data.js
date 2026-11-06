/* ============================================================
   摆拍手册 PoseGuide · 原型示例数据 mock-data.js
   · 分类与姿势条目取自《拍照姿势App项目计划.md》§2.2（24 条子集 / 全量 100 条）
   · 图片全部为运行时生成的内联 SVG 渐变占位（无外部资源），
     覆盖 cover（示例）/ line（线稿标注）/ wrong（错误示范）三层素材（§4.2）
   ============================================================ */
(function () {
  'use strict';

  /* ---------- 十类分类（§2.1）＋ 柔和点缀色（占位图调色板） ---------- */
  const CATS = [
    { id: 'ST',     name: '站姿 · 日常',   short: '站姿',   tint: ['#EAD9C3', '#C9976F'] },
    { id: 'SIT',    name: '坐姿',          short: '坐姿',   tint: ['#DEE5D0', '#93A37E'] },
    { id: 'STREET', name: '街拍 · 行走互动', short: '街拍',  tint: ['#D8DDE4', '#8494AA'] },
    { id: 'TRAVEL', name: '旅行 · 地标打卡', short: '旅行',  tint: ['#CBE2DE', '#6FA098'] },
    { id: 'HOME',   name: '室内 · 居家',   short: '居家',   tint: ['#F2E6D0', '#C7A475'] },
    { id: 'CAFE',   name: '咖啡店 · 餐桌', short: '咖啡店', tint: ['#E9D8C9', '#A57C63'] },
    { id: 'BACK',   name: '背影 · 剪影',   short: '背影',   tint: ['#EACDB2', '#8A5A41'] },
    { id: 'CLOSE',  name: '特写 · 局部',   short: '特写',   tint: ['#F4DED6', '#C68B7B'] },
    { id: 'PROP',   name: '道具 · 互动',   short: '道具',   tint: ['#F4E8CB', '#C0A95F'] },
    { id: 'DUO',    name: '多人 · 合影',   short: '多人',   tint: ['#F4DCE0', '#C08792'] },
  ];
  const CAT_MAP = Object.fromEntries(CATS.map(c => [c.id, c]));
  // 每类 10 条（全量口径，§2.1）
  CATS.forEach(c => { c.total = 10; });

  /* ---------- 姿势条目（§2.2 子集，steps/mistakes 按条目要点整理） ---------- */
  const P = (o) => Object.assign({ people: 1, gear: ['phone', 'camera'], props: [], ai: true }, o);
  const POSES = [
    P({ id: 'ST-01', name: '自然直立', cat: 'ST', diff: 1, light: ['自然光'], tags: ['站姿', '全身'],
        focal: '等效 24–35mm（手机 1x）', cam: '竖构图全身，镜头与腰同高', set: '人像模式 f/2.8–4',
        steps: ['双脚前后错开，摆出丁字步', '重心放到后腿，收腹开肩', '双手自然下垂并微微离开身体'],
        mistakes: ['双臂贴死身体，显壮显僵', '重心居中，双腿线条显短'] }),
    P({ id: 'ST-02', name: '45°侧身回眸', cat: 'ST', diff: 1, light: ['自然光', '黄金时刻'], tags: ['站姿', '回眸', '半身'],
        focal: '等效 24–35mm（手机 1x）', cam: '竖构图半身，人物居右三分线', set: '人像模式 f/2.8–4',
        steps: ['背对镜头站定，双脚前后错开', '身体侧转 45°，重心移到后腿', '听口令转头看镜头，连拍 3–5 张'],
        mistakes: ['只转头不转身，面部僵硬', '下巴上扬显鼻孔', '双臂贴死身体显壮'] }),
    P({ id: 'ST-03', name: '靠墙站', cat: 'ST', diff: 1, light: ['自然光'], tags: ['站姿', '街头'], ai: false,
        focal: '等效 35–50mm（手机 1–2x）', cam: '侧面平视中景，选干净墙面', set: '普通模式即可',
        steps: ['肩或背轻靠墙，找到支撑点', '一腿屈膝，脚掌轻点墙面', '手插袋或自然下垂，肩膀放松'],
        mistakes: ['整片背部贴墙，姿态僵硬', '屈膝腿膝盖内扣，线条变形'] }),
    P({ id: 'ST-06', name: '拨发动态', cat: 'ST', diff: 1, light: ['自然光', '逆光'], tags: ['站姿', '动态'],
        focal: '等效 50mm（手机 2x）', cam: '平视半身，连拍快门 ≥ 1/250s', set: '连拍模式',
        steps: ['单手撩起一侧头发', '借风或甩动制造发丝弧线', '连拍抓拨发的瞬间帧'],
        mistakes: ['手挡住脸，五官被遮', '快门过慢，发丝糊成一团'] }),

    P({ id: 'SIT-02', name: '侧坐叠腿', cat: 'SIT', diff: 1, light: ['自然光'], tags: ['坐姿', '曲线'],
        focal: '等效 35mm（手机 1x）', cam: '侧面全景，表现腿部曲线', set: '人像模式',
        steps: ['双腿并拢向一侧侧放', '小腿向后叠，脚尖绷直', '腰背挺直，一手撑椅面'],
        mistakes: ['脚尖松弛下垂，线条松散', '膝盖正对镜头，显腿短'] }),
    P({ id: 'SIT-05', name: '屈膝抱腿', cat: 'SIT', diff: 1, light: ['自然光'], tags: ['坐姿', '居家'],
        focal: '等效 24–35mm（手机 1x）', cam: '平视全身，膝盖朝向镜头', set: '人像模式',
        steps: ['坐高处台阶或床沿', '双膝屈起并拢', '手臂环抱小腿，下巴微收'],
        mistakes: ['弯腰驼背，气质全无', '双膝打开，显松垮'] }),

    P({ id: 'STREET-01', name: '行走抓拍', cat: 'STREET', diff: 2, light: ['自然光'], tags: ['街拍', '动态'],
        focal: '等效 24–35mm（手机 1x）', cam: '后退跟拍或原地连拍，脚下留白要少', set: '连拍 1/500s',
        steps: ['正常步速向前走，不看镜头', '手拿咖啡或手机，给手找事做', '摄影师后退跟拍，连拍 5–8 张'],
        mistakes: ['刻意迈大步，姿态失真', '画面下方留白过多，人显矮'] }),
    P({ id: 'STREET-02', name: '回眸瞬间', cat: 'STREET', diff: 2, light: ['自然光'], tags: ['街拍', '回眸'],
        focal: '等效 50mm（手机 2x）', cam: '低机位竖构图，连拍抓甩发帧', set: '连拍模式',
        steps: ['行走中听口令突然回头', '头发自然甩动，眼神接触镜头', '连拍抓发丝扬起的那一帧'],
        mistakes: ['回头过猛，表情失控', '只转头，肩颈线条僵硬'] }),
    P({ id: 'STREET-08', name: '雨天打伞', cat: 'STREET', diff: 2, light: ['自然光'], props: ['伞'], tags: ['街拍', '雨天'], ai: false,
        focal: '等效 24mm（手机 1x）', cam: '低机位把地面倒影拍进画面', set: '夜景/雨天模式',
        steps: ['伞略向后倾，露出脸部', '踩水花制造动感', '低机位收入人＋倒影同框'],
        mistakes: ['伞压太低，脸全被遮', '忽略地面倒影，雨天氛围减半'] }),

    P({ id: 'TRAVEL-02', name: '人在景中', cat: 'TRAVEL', diff: 1, light: ['自然光'], tags: ['旅行', '风景'],
        focal: '等效 16–24mm（手机 0.5–1x）', cam: '竖构图三分线，前景花草做层次', set: '广角小光圈',
        steps: ['人物占比 < 1/10，面向地标', '站在三分线上，目视远方', '前景借花草做虚化层次'],
        mistakes: ['人物过大，地标被挡', '海平线切头，构图压迫'] }),
    P({ id: 'TRAVEL-04', name: '海边跳跃', cat: 'TRAVEL', diff: 2, light: ['黄金时刻'], tags: ['旅行', '动态'],
        focal: '等效 16–24mm（手机 0.5x）', cam: '超低机位仰拍＋连拍', set: '连拍 1/1000s',
        steps: ['喊口令「1-2-3 跳」齐跳', '双臂上扬，双腿后踢', '连拍取腾空最高帧'],
        mistakes: ['机位太高，跳跃感全无', '只拍单张，错过最高点'] }),
    P({ id: 'TRAVEL-08', name: '阳台清晨', cat: 'TRAVEL', diff: 1, light: ['黄金时刻'], tags: ['旅行', '氛围'],
        focal: '等效 50mm（手机 2x）', cam: '侧逆光，纱帘做柔光前景', set: '人像模式',
        steps: ['靠栏杆伸懒腰或端咖啡', '侧身面向晨光方向', '纱帘入镜做柔光前景'],
        mistakes: ['正对强光，面部死黑', '纱帘过厚，画面灰蒙'] }),

    P({ id: 'HOME-01', name: '窗边侧脸', cat: 'HOME', diff: 1, light: ['自然光'], tags: ['居家', '侧脸'],
        focal: '等效 50–85mm（手机 2–3x）', cam: '侧面 45°，窗光主光', set: '人像模式 f/2.8',
        steps: ['站/坐窗前，脸转向光', '眼看窗外，不看镜头', '暗部借白墙反光补光'],
        mistakes: ['背对窗户，面部欠曝', '顶灯与环境光混杂，脸脏'] }),
    P({ id: 'HOME-08', name: '沙发阅读', cat: 'HOME', diff: 1, light: ['自然光', '人造光'], props: ['书'], tags: ['居家', '氛围'], ai: false,
        focal: '等效 35mm（手机 1x）', cam: '侧光中景，落地灯做画面点缀', set: '夜模式防抖',
        steps: ['盘坐沙发捧书', '举书挡脸或侧头阅读', '落地灯入镜做暖光点缀'],
        mistakes: ['书的封面反光抢戏', '背景杂物太多，画面杂乱'] }),

    P({ id: 'CAFE-01', name: '捧杯看镜头', cat: 'CAFE', diff: 1, light: ['自然光'], props: ['咖啡'], tags: ['咖啡店', '道具'],
        focal: '等效 35mm（手机 1x）', cam: '平视半身，背景人流虚化', set: '人像模式 f/2.8',
        steps: ['双手捧杯凑近下巴', '浅笑看向镜头', '选靠窗位借自然光'],
        mistakes: ['杯子挡嘴，笑容被吃掉', '背景人流杂乱，主体不突出'] }),
    P({ id: 'CAFE-04', name: '桌面 POV', cat: 'CAFE', diff: 1, light: ['自然光'], props: ['咖啡'], tags: ['咖啡店', '俯拍'],
        focal: '等效 24mm（手机 1x）', cam: '垂直俯拍桌面，餐布/木纹做底色', set: '俯拍保持水平',
        steps: ['双手入镜捧杯或比心', '食物摆在画面对面', '桌面物品成组摆放（3 件以内）'],
        mistakes: ['俯拍不正，画面歪斜', '桌面物品超过 3 件，杂乱'] }),

    P({ id: 'BACK-01', name: '张开双臂', cat: 'BACK', diff: 1, light: ['黄金时刻'], tags: ['背影', '旅行'],
        focal: '等效 24mm（手机 1x）', cam: '竖构图，人物占下 1/3，天空留白', set: '普通模式',
        steps: ['面朝大海/山野站定', '双臂向两侧完全张开', '人物置于画面下 1/3'],
        mistakes: ['人物居中，天空留白不足', '手臂弯曲，线条不舒展'] }),
    P({ id: 'BACK-08', name: '落日剪影', cat: 'BACK', diff: 2, light: ['逆光', '黄金时刻'], tags: ['背影', '剪影'], ai: false,
        focal: '等效 24–35mm（手机 1x）', cam: '逆光对天空点测光，人物收成纯黑剪影', set: '点测光 -1EV',
        steps: ['面朝落日站立', '肢体夸张舒展（叉腰/伸手）', '对天空点测光并 -1EV'],
        mistakes: ['对人物测光，剪影变灰', '肢体拘谨，剪影轮廓不清'] }),

    P({ id: 'CLOSE-01', name: '侧脸特写', cat: 'CLOSE', diff: 1, light: ['自然光'], tags: ['特写', '侧脸'],
        focal: '等效 85mm（手机 2–3x）', cam: '平视，对焦眼睛', set: '人像模式 f/2.8',
        steps: ['面向光源摆出 2/3 侧脸', '眼看斜上方', '对焦眼睛，光比要小'],
        mistakes: ['对焦到鼻尖，眼睛虚', '光比过大，暗部死黑'] }),
    P({ id: 'CLOSE-06', name: '手部特写', cat: 'CLOSE', diff: 1, light: ['自然光'], props: ['花'], tags: ['特写', '手部'],
        focal: '等效 50mm（手机 2x）', cam: '俯拍或侧拍，背景纯净', set: '近景对焦',
        steps: ['手拿花/戴戒指摆好手型', '背景选纯净色块', '注意手部状态，指尖放松'],
        mistakes: ['手部僵硬，指节泛白', '背景杂乱，主体不突出'] }),

    P({ id: 'PROP-02', name: '牵引气球', cat: 'PROP', diff: 1, light: ['自然光'], props: ['气球'], tags: ['道具', '户外'],
        focal: '等效 24mm（手机 1x）', cam: '低机位，气球飘向画面留白处', set: '普通模式',
        steps: ['手牵气球束举过头顶', '微仰头看气球', '气球朝画面留白一侧'],
        mistakes: ['气球挡脸，人物失焦', '气球出画，道具失效'] }),
    P({ id: 'PROP-06', name: '宠物互动', cat: 'PROP', diff: 2, light: ['自然光'], props: ['宠物'], tags: ['道具', '动态'], ai: false,
        focal: '等效 35mm（手机 1x）', cam: '蹲下与宠物平视', set: '连拍 1/500s',
        steps: ['蹲下与宠物视线齐平', '用零食逗引宠物视线', '连拍抓互动瞬间'],
        mistakes: ['俯拍宠物，视线错位', '快门过慢，动物糊掉'] }),

    P({ id: 'DUO-04', name: '额头相抵', cat: 'DUO', diff: 1, people: 2, light: ['逆光'], tags: ['双人', '氛围'],
        focal: '等效 50mm（手机 2x）', cam: '平视近景，逆光轮廓光更有氛围', set: '人像模式',
        steps: ['闭眼额头轻贴', '手互搭手臂', '逆光位拍轮廓光'],
        mistakes: ['额头用力顶，表情紧张', '顺光平拍，氛围全无'] }),
    P({ id: 'DUO-09', name: '拉手奔跑', cat: 'DUO', diff: 2, people: 2, light: ['黄金时刻'], tags: ['双人', '动态'],
        focal: '等效 16–24mm（手机 0.5x）', cam: '广角低机位连拍', set: '连拍 1/500s',
        steps: ['牵手朝镜头方向跑', '或互相追逐制造互动', '低机位连拍取腾空帧'],
        mistakes: ['速度太慢，画面平淡', '快门不够，两人都糊'] }),
  ];

  /* ---------- 构图/光线小贴士（§5.2 / 决策 §9-8，按类别键控，改写自 §2.1–2.2 通用要点） ---------- */
  const TIPS = {
    ST:     ['头顶留白约 1/10，裁切脚部会显局促', '逆光时对焦亮部并 -1EV，保留高光层次'],
    SIT:    ['坐椅面前 1/3，腰背挺直更显精神', '低机位仰拍可拉长腿部线条'],
    STREET: ['低机位＋竖构图是街拍万能公式', '连拍抓「不看镜头」的自然帧'],
    TRAVEL: ['人小景大：人物占比 < 1/10 更显景致', '海平线避开头顶，避免切割感'],
    HOME:   ['窗光是主角：侧光/逆光优于顶灯', '画面做减法，收拾背景杂物'],
    CAFE:   ['靠窗位光线最佳，桌面物品成组摆放（3 件以内）', '垂直俯拍时双手入镜更有 POV 感'],
    BACK:   ['背影要「有戏」：手、脚、头必须有内容', '服装与背景的颜色对比是成败关键'],
    CLOSE:  ['对焦眼睛，光比要小', '手型放松如「半握蛋」更显自然'],
    PROP:   ['道具是视觉锚点：一图一件主道具', '道具颜色与服装呼应'],
    DUO:    ['站位高低错落，避免一排呆立', '喊口令引导互动，抓真实笑容'],
  };

  /* ============================================================
     占位图生成：poseSVG(pose, kind)
     kind: 'cover'（示例图，AI 角标对应） | 'line'（线稿标注） | 'wrong'（错误示范）
     说明：几何人形剪影 ＋ 类别色调渐变，模拟「杂志感大图」的版面观感
     ============================================================ */
  const hash = (s) => { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; };

  const ARMS = [
    'M-3,-58 C-16,-46 -21,-26 -20,-8 M3,-58 C16,-46 21,-26 20,-8',
    'M-3,-58 C-20,-64 -28,-80 -26,-94 M3,-58 C14,-48 18,-30 18,-12',
    'M-3,-56 C-18,-50 -14,-34 -6,-30 M3,-56 C18,-50 22,-36 16,-28',
    'M-2,-56 C-20,-52 -24,-34 -14,-24 M4,-58 C22,-64 26,-82 22,-94',
  ];
  const LEGS = [
    'M0,-8 C-2,24 -10,48 -13,72 M2,-8 C4,24 8,48 10,72',
    'M0,-8 C-4,26 -14,50 -20,70 M2,-8 C6,22 14,44 16,70',
    'M0,-8 C-2,20 -8,44 -10,70 M2,-8 C10,10 24,20 34,12',
  ];

  function figure(x, y, s, ink, seed, thick) {
    const a = ARMS[seed % ARMS.length], l = LEGS[(seed >>> 2) % LEGS.length];
    const w1 = thick ? 30 : 3, w2 = thick ? 13 : 2.4, w3 = thick ? 15 : 2.6;
    return `<g transform="translate(${x} ${y}) scale(${s})" stroke="${ink}" stroke-linecap="round" fill="none">
      <circle cx="0" cy="-88" r="${thick ? 19 : 18}" ${thick ? `fill="${ink}" stroke="none"` : ''}/>
      <path d="M0,-64 L0,-6" stroke-width="${w1}"/>
      <path d="${a}" stroke-width="${w2}"/>
      <path d="${l}" stroke-width="${w3}"/>
    </g>`;
  }

  function accessory(p, ink, x, y) {
    const out = [];
    if (p.props.includes('气球')) out.push(`<g stroke="${ink}" fill="none" stroke-width="2"><circle cx="${x + 34}" cy="${y - 148}" r="24" fill="${ink}" opacity=".85"/><path d="M${x + 30},${y - 126} C${x + 18},${y - 92} ${x + 30},${y - 56} ${x + 16},${y - 34}"/></g>`);
    if (p.props.includes('咖啡')) out.push(`<g fill="${ink}"><rect x="${x - 44}" y="${y - 44}" width="20" height="26" rx="4"/><rect x="${x - 47}" y="${y - 48}" width="26" height="6" rx="3"/></g>`);
    if (p.props.includes('伞')) out.push(`<g stroke="${ink}" stroke-width="4" fill="${ink}"><path d="M${x - 54},${y - 112} A54,54 0 0 1 ${x + 54},${y - 112} Z"/><path d="M${x},${y - 112} L${x},${y - 98}" fill="none" stroke-linecap="round"/></g>`);
    if (p.props.includes('花')) out.push(`<g fill="${ink}"><circle cx="${x - 26}" cy="${y - 38}" r="7"/><circle cx="${x - 15}" cy="${y - 45}" r="7"/><circle cx="${x - 18}" cy="${y - 31}" r="7"/></g>`);
    if (p.props.includes('宠物')) out.push(`<g fill="${ink}"><ellipse cx="${x + 34}" cy="${y + 62}" rx="15" ry="10"/><circle cx="${x + 47}" cy="${y + 55}" r="7"/><path d="M${x + 43},${y + 49} l-2,-6 l5,3 Z"/></g>`);
    if (p.props.includes('书')) out.push(`<g fill="${ink}"><path d="M${x - 34},${y - 30} q14,-8 26,0 l0,18 q-12,-7 -26,0 Z"/><path d="M${x - 8},${y - 30} q12,-8 26,0 l0,18 q-14,-7 -26,0 Z"/></g>`);
    return out.join('');
  }

  function poseSVG(p, kind) {
    const cat = CAT_MAP[p.cat];
    const seed = hash(p.id);
    const uid = `${p.id}-${kind}`;
    const W = 480, H = 640;
    const [t1, t2] = cat.tint;

    /* ---- 线稿标注图 ---- */
    if (kind === 'line') {
      const ann1 = (p.steps[0] || '').slice(0, 10);
      const ann2 = (p.steps[1] || '').slice(0, 10);
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="${p.name} 线稿标注示意">
        <rect width="${W}" height="${H}" fill="#FCF8F0"/>
        <g stroke="#D8CBB6" stroke-width="1.5" stroke-dasharray="6 7"><path d="M160,0 V640"/><path d="M320,0 V640"/><path d="M0,213 H480"/><path d="M0,427 H480"/></g>
        <path d="M0,540 H480" stroke="#C9B896" stroke-width="2"/>
        <g fill="none" stroke="#43382B" stroke-width="2.6" stroke-linecap="round">
          <circle cx="240" cy="292" r="34"/><path d="M240,326 L240,470" stroke-width="5"/>
          <path d="M235,346 C205,368 198,404 202,438 M245,346 C275,368 282,404 278,438" stroke-width="4"/>
          <path d="M238,472 C233,520 216,556 208,588 M242,472 C248,520 258,556 264,588" stroke-width="4.4"/>
        </g>
        <g fill="#43382B"><circle cx="240" cy="292" r="4"/><circle cx="240" cy="470" r="4"/><circle cx="208" cy="588" r="4"/><circle cx="264" cy="588" r="4"/></g>
        <g font-family="inherit" font-size="15" fill="#8B7D6E">
          <path d="M276,270 C330,240 360,150 392,120" stroke="#B9A98F" fill="none" stroke-width="1.6"/>
          <text x="316" y="102">${ann1}</text>
          <path d="M212,420 C160,440 140,500 128,540" stroke="#B9A98F" fill="none" stroke-width="1.6"/>
          <text x="46" y="576">${ann2}</text>
        </g>
        <text x="24" y="${H - 22}" font-size="14" fill="#B9A98F">线稿示意 · ${p.id}</text>
      </svg>`;
    }

    /* ---- 错误示范 ---- */
    if (kind === 'wrong') {
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="${p.name} 错误示范示意">
        <defs><linearGradient id="wg-${uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#D9D3CA"/><stop offset="1" stop-color="#9E968B"/></linearGradient></defs>
        <rect width="${W}" height="${H}" fill="url(#wg-${uid})"/>
        <ellipse cx="240" cy="590" rx="190" ry="34" fill="rgba(40,32,24,.18)"/>
        <g transform="rotate(7 240 400)">${figure(240, 400, 1.35, 'rgba(48,40,32,.75)', seed, true)}</g>
        <g stroke="#C03B23" stroke-width="7" stroke-linecap="round"><path d="M198,300 L282,384"/><path d="M282,300 L198,384"/></g>
        <g><rect x="18" y="18" width="128" height="38" rx="19" fill="#C03B23"/><path d="M40,30 l14,14 M54,30 l-14,14" stroke="#fff" stroke-width="3" stroke-linecap="round"/><text x="66" y="44" font-size="17" fill="#fff" font-weight="600">常见错误</text></g>
        <text x="18" y="${H - 20}" font-size="15" fill="rgba(255,255,255,.75)">${p.mistakes[0]}</text>
      </svg>`;
    }

    /* ---- 示例图（cover）---- */
    const uid2 = uid;
    const closeUp = p.cat === 'CLOSE';
    const duo = p.cat === 'DUO';
    const top = p.id === 'CAFE-04';
    const sunX = 90 + (seed % 280), sunY = 110 + (seed % 90), sunR = 44 + (seed % 34);
    const fig = top
      ? `<g fill="rgba(43,32,22,.72)">
           <ellipse cx="150" cy="330" rx="88" ry="88" fill="none" stroke="rgba(43,32,22,.72)" stroke-width="10"/>
           <rect x="288" y="252" width="86" height="118" rx="16"/>
           <ellipse cx="331" cy="410" rx="60" ry="14"/>
           <path d="M96,508 q26,-34 62,-6 q30,24 -6,44 q-46,20 -56,-38Z"/>
           <circle cx="120" cy="516" r="26"/><circle cx="352" cy="520" r="26"/>
         </g>`
      : duo
        ? figure(196, 402, 1.18, 'rgba(43,32,22,.72)', seed, true) + figure(296, 396, 1.12, 'rgba(43,32,22,.6)', seed + 7, true)
        : figure(240 + (seed % 60) - 30, 402, closeUp ? 2.05 : 1.35, 'rgba(43,32,22,.74)', seed, true);

    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="${p.name} 示例占位图">
      <defs>
        <linearGradient id="cg-${uid2}" x1="0" y1="0" x2="0.25" y2="1"><stop offset="0" stop-color="${t1}"/><stop offset="1" stop-color="${t2}"/></linearGradient>
        <radialGradient id="vg-${uid2}" cx="0.5" cy="0.42" r="0.85"><stop offset="0.55" stop-color="rgba(30,20,12,0)"/><stop offset="1" stop-color="rgba(30,20,12,.26)"/></radialGradient>
      </defs>
      <rect width="${W}" height="${H}" fill="url(#cg-${uid2})"/>
      <circle cx="${sunX}" cy="${sunY}" r="${sunR}" fill="rgba(255,252,244,.5)"/>
      <path d="M0,508 Q120,452 250,500 T480,486 V640 H0 Z" fill="rgba(38,28,18,.22)"/>
      <path d="M0,560 Q160,514 320,552 T480,542 V640 H0 Z" fill="rgba(38,28,18,.32)"/>
      ${accessory(p, 'rgba(43,32,22,.6)', 240, 380)}
      ${fig}
      <ellipse cx="${240 + (seed % 60) - 30}" cy="594" rx="96" ry="16" fill="rgba(30,22,14,.25)"/>
      <rect width="${W}" height="${H}" fill="url(#vg-${uid2})"/>
    </svg>`;
  }

  /* ---------- 小尺寸构图示意（机位卡：三分线 + 人物位置） ---------- */
  function framingSVG(p) {
    const right = /右|侧/.test(p.cam);
    const low = /低机位|仰拍/.test(p.cam) || /仰/.test(p.cam);
    const x = right ? 320 : 240, y = low ? 430 : 350;
    return `<svg viewBox="0 0 200 150" role="img" aria-label="构图示意">
      <rect x="8" y="8" width="184" height="134" rx="8" fill="#FDF9F1" stroke="#D8CBB6"/>
      <g stroke="#C9B896" stroke-dasharray="4 5" stroke-width="1.2"><path d="M69,8 V142"/><path d="M131,8 V142"/><path d="M8,53 H192"/><path d="M8,98 H192"/></g>
      <circle cx="${x / 2.4}" cy="${y / 4.4}" r="7" fill="rgba(43,32,22,.7)"/>
      <path d="M${x / 2.4},${y / 4.4 + 8} L${x / 2.4},${y / 4.4 + 30}" stroke="rgba(43,32,22,.7)" stroke-width="6" stroke-linecap="round"/>
      <text x="16" y="26" font-size="11" fill="#8B7D6E">${p.focal.split('（')[0]}</text>
    </svg>`;
  }

  window.PG_DATA = { CATS, CAT_MAP, POSES, TIPS, poseSVG, framingSVG };
})();
