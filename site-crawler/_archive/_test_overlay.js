
(() => {
  // 如果已经注入过，跳过
  if (window.__crawler_wizard) return;
  window.__crawler_wizard = true;

  // ── 样式 ──
  const style = document.createElement('style');
  style.textContent = `
    #cw-overlay {
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      z-index: 2147483647; pointer-events: none; font-family: system-ui, sans-serif;
    }
    #cw-panel {
      pointer-events: auto; position: fixed; top: 12px; left: 12px;
      background: #1a1d27; border: 1px solid #6366f1; border-radius: 10px;
      padding: 14px 18px; min-width: 280px; color: #e5e7eb; font-size: 13px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.5); user-select: none;
    }
    #cw-panel h3 { margin: 0 0 8px 0; font-size: 14px; color: #a5b4fc; }
    #cw-panel .step { color: #9ca3af; margin-bottom: 10px; }
    #cw-panel .btn {
      display: inline-block; padding: 6px 14px; border-radius: 5px;
      border: none; cursor: pointer; font-size: 12px; margin-right: 6px;
    }
    #cw-panel .btn-primary { background: #6366f1; color: #fff; }
    #cw-panel .btn-primary:hover { background: #818cf8; }
    #cw-panel .btn-ghost { background: transparent; border: 1px solid #374151; color: #d1d5db; }
    #cw-panel .btn-ghost:hover { background: #1f2937; }
    #cw-panel .btn-danger { background: #dc2626; color: #fff; }
    #cw-panel .log { background: #0f1117; border: 1px solid #1f2937; border-radius: 4px; padding: 6px 8px; max-height: 120px; overflow-y: auto; font-size: 11px; color: #6b7280; margin-top: 8px; }
    #cw-panel .log .ok { color: #4ade80; }
    #cw-panel .log .err { color: #f87171; }
    .cw-highlight {
      outline: 3px solid #6366f1 !important; outline-offset: 2px !important;
      cursor: pointer !important; transition: outline 0.2s;
    }
    .cw-highlight:hover { outline-color: #a5b4fc !important; }
  `;
  document.head.appendChild(style);

  // ── 面板 ──
  const overlay = document.createElement('div');
  overlay.id = 'cw-overlay';
  overlay.innerHTML = `
    <div id="cw-panel">
      <h3>🔧 配置向导</h3>
      <div class="step" id="cw-step">正在初始化...</div>
      <div id="cw-actions"></div>
      <div class="log" id="cw-log"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  const stepEl = document.getElementById('cw-step');
  const actionsEl = document.getElementById('cw-actions');
  const logEl = document.getElementById('cw-log');

  function log(msg, cls='') {
    const d = document.createElement('div');
    d.className = cls;
    d.textContent = msg;
    logEl.appendChild(d);
    logEl.scrollTop = logEl.scrollHeight;
    console.log('[wizard]', msg);
  }

  function setStep(text) { stepEl.textContent = text; }
  function setActions(buttons) {
    actionsEl.innerHTML = '';
    buttons.forEach(b => {
      const btn = document.createElement('button');
      btn.className = 'btn ' + (b.cls || 'btn-primary');
      btn.textContent = b.label;
      btn.onclick = b.fn;
      actionsEl.appendChild(btn);
    });
  }

  // ── 状态 ──
  let state = {
    stage: 'init',        // init | select_link | choose_type | detail | select_play | stream_found | done
    link_type: null,       // 'video' or 'image'
    selected_link: null,     // {href, text, selector}
    detail_url: null,
    play_link: null,
    stream_url: null,
    link_selector: null,    // 同类链接的 CSS 选择器
    config: { link_patterns: {video_detail:[], art_detail:[], exclude:[]}, extract_chains: {} }
  };
  window.__cw_state = state;

  // ── 工具：生成 CSS 选择器 ──
  function getSelector(el) {
    if (el.id) return '#' + el.id;
    let path = [];
    let cur = el;
    while (cur && cur !== document.body) {
      let sel = cur.tagName.toLowerCase();
      if (cur.className && typeof cur.className === 'string') {
        const cls = cur.className.trim().split(/\s+/)[0];
        if (cls) sel += '.' + cls;
      }
      const parent = cur.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter(c => c.tagName === cur.tagName);
        if (siblings.length > 1) sel += `:nth-child(${[...parent.children].indexOf(cur)+1})`;
      }
      path.unshift(sel);
      cur = cur.parentElement;
      if (path.length > 4) break;
    }
    return path.join(' > ');
  }

  // ── 工具：从 URL 生成正则 ──
  function urlToPattern(url) {
    const u = new URL(url);
    let path = u.pathname;
    // 把数字部分替换为正则
    path = path.replace(/\/\d+(?=\/|\.|$)/g, '/\\d+');
    path = path.replace(/\d+(?=\.html?)/, '\\d+');
    // escape
    path = path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return path;
  }

  // ── Stage: init → 等待用户选择链接 ──
  function startSelectLink() {
    state.stage = 'select_link';
    setStep('请点击页面上的一个内容链接（视频或图片）');
    setActions([
      { label: '取消', cls: 'btn-ghost', fn: () => { log('已取消'); startSelectLink(); } }
    ]);
    log('选择模式已激活，请点击页面链接...');

    // 高亮所有链接
    document.querySelectorAll('a[href]').forEach(a => {
      a.classList.add('cw-highlight');
      a.addEventListener('click', onLinkClick, true);
    });
  }

  function onLinkClick(e) {
    if (state.stage !== 'select_link') return;
    e.preventDefault();
    e.stopPropagation();

    const a = e.currentTarget;
    state.selected_link = { href: a.href, text: a.textContent.trim().substring(0,80), selector: getSelector(a) };
    log(`已选择: ${a.textContent.trim().substring(0,40)}`);
    log(`URL: ${a.href}`);
    // 清除高亮
    document.querySelectorAll('.cw-highlight').forEach(el => {
      el.classList.remove('cw-highlight');
      el.removeEventListener('click', onLinkClick, true);
    });
    // 询问类型
    state.stage = 'choose_type';
    setStep('这个链接指向什么内容？');
    setActions([
      { label: '视频内容', cls: 'btn-primary', fn: () => chooseType('video') },
      { label: '图片内容', cls: 'btn-primary', fn: () => chooseType('image') },
      { label: '重新选择', cls: 'btn-ghost', fn: startSelectLink },
    ]);
  }

  function chooseType(type) {
    state.link_type = type;
    log(`类型: ${type}`);
    // 生成 link_pattern
    const pattern = urlToPattern(state.selected_link.href);
    if (type === 'video') {
      state.config.link_patterns.video_detail.push(pattern);
    } else {
      state.config.link_patterns.art_detail.push(pattern);
    }
    // 生成同类链接的 CSS 选择器
    state.link_selector = state.selected_link.selector;
    log(`CSS 选择器: ${state.link_selector}`);
    log(`URL 正则: ${pattern}`);

    // 导航到详情页
    state.stage = 'navigating';
    setStep(`正在进入详情页...`);
    setActions([]);
    log(`导航到: ${state.selected_link.href}`);
    window.location.href = state.selected_link.href;
  }

  // ── 监听页面加载完成（详情页）──
  let pageReady = false;
  function onPageLoad() {
    if (pageReady) return;
    pageReady = true;
    if (state.stage === 'navigating') {
      // 到达详情页
      state.detail_url = window.location.href;
      if (state.link_type === 'video') {
        setStep('在详情页中，请点击「播放」或「立即播放」按钮/链接');
        setActions([
          { label: '已点击播放', cls: 'btn-primary', fn: onPlaySelected },
          { label: '跳过此步', cls: 'btn-ghost', fn: skipPlayStep },
        ]);
        // 高亮所有带播放文字的链接
        document.querySelectorAll('a').forEach(a => {
          const t = a.textContent.trim();
          if (t.includes('播放') || t.includes('Play') || t.includes('HD') || t.includes('播放')) {
            a.classList.add('cw-highlight');
          }
        });
        state.stage = 'select_play';
        log('详情页已加载，请点击播放链接');
      } else {
        // 图片类型：提取图片
        setStep('正在提取图片链接...');
        setActions([]);
        extractImageLinks();
      }
    }
  }
  window.addEventListener('load', () => setTimeout(onPageLoad, 500));

  // ── 播放链接选择 ──
  function onPlaySelected() {
    // 用户声称已点击，我们需要找到播放页的 URL
    // 实际是导航到了播放页，监听下一次 load
    state.stage = 'play_navigating';
    setStep('正在进入播放页...');
    log('如果已跳转，请等待播放页加载...');
    // 监听是否跳转
    let checkCount = 0;
    const checkNav = setInterval(() => {
      checkCount++;
      if (window.location.href !== state.detail_url) {
        clearInterval(checkNav);
        log(`已进入播放页: ${window.location.href}`);
        extractStreamUrl();
      }
      if (checkCount > 60) clearInterval(checkNav);
    }, 500);
  }

  function skipPlayStep() {
    log('跳过播放链接选择');
    extractStreamUrl();
  }

  // ── 提取流地址 ──
  function extractStreamUrl() {
    setStep('正在自动检测视频流地址...');
    setActions([]);
    // 扫描 iframe
    const iframes = [...document.querySelectorAll('iframe')];
    log(`发现 ${iframes.length} 个 iframe`);
    for (const f of iframes) {
      const src = f.src || '';
      log(`iframe src: ${src.substring(0,80)}`);
      try {
        const u = new URL(src);
        const videoUrl = u.searchParams.get('url');
        if (videoUrl && (videoUrl.includes('.m3u8') || videoUrl.includes('.mp4'))) {
          state.stream_url = videoUrl;
          state.config.extract_chains.video = {
            steps: [
              { name: 'detail', extract_js: '...' },  // 占位，后面替换
              { name: 'play', extract_js: '...' },
            ]
          };
          log(`✅ 找到流地址: ${videoUrl}`, 'ok');
          setStep('✅ 已找到视频流地址！');
          setActions([
            { label: '确认并生成配置', cls: 'btn-primary', fn: finishWizard },
            { label: '重新选择', cls: 'btn-ghost', fn: startSelectLink },
          ]);
          return;
        }
      } catch(e) {}
      if (src.includes('.m3u8') || src.includes('.mp4')) {
        state.stream_url = src;
        log(`✅ 找到流地址: ${src}`, 'ok');
        setStep('✅ 已找到视频流地址！');
        setActions([
          { label: '确认并生成配置', cls: 'btn-primary', fn: finishWizard },
          { label: '重新选择', cls: 'btn-ghost', fn: startSelectLink },
        ]);
        return;
      }
    }
    log('未自动找到流地址，请手动确认播放页已加载', 'err');
    setActions([
      { label: '刷新重试', cls: 'btn-primary', fn: () => location.reload() },
      { label: '跳过', cls: 'btn-ghost', fn: finishWizard },
    ]);
  }

  // ── 提取图片链接 ──
  function extractImageLinks() {
    const container = document.querySelector('#read_tpc') || document.body;
    const imgs = [...container.querySelectorAll('img')].map(img =>
      img.src || img.dataset.src || img.dataset.original || ''
    ).filter(Boolean);
    log(`✅ 找到 ${imgs.length} 张图片`);
    state.config.extract_chains.art = { steps: [{ name: 'detail', extract_js: '...' }] };
    setStep(`✅ 找到 ${imgs.length} 张图片`);
    setActions([
      { label: '确认并生成配置', cls: 'btn-primary', fn: finishWizard },
      { label: '重新选择', cls: 'btn-ghost', fn: startSelectLink },
    ]);
  }

  // ── 完成 ──
  function finishWizard() {
    setStep('配置已生成，正在保存...');
    setActions([]);
    // 把状态存到 window，让 Python 后端读取
    window.__cw_result = {
      link_type: state.link_type,
      link_selector: state.link_selector,
      selected_url: state.selected_link?.href,
      stream_url: state.stream_url,
      config: state.config,
    };
    log('✅ 配置已保存到 window.__cw_result', 'ok');
    log('可以关闭此窗口，返回管理界面查看结果。', 'ok');
    setStep('✅ 配置生成完成！可以关闭此窗口。');
    setActions([
      { label: '关闭窗口', cls: 'btn-primary', fn: () => window.close() },
    ]);
  }

  // ── 启动 ──
  setStep('就绪，请点击「开始选择」');
  setActions([
    { label: '开始选择', cls: 'btn-primary', fn: startSelectLink },
    { label: '取消', cls: 'btn-ghost', fn: () => log('已取消') },
  ]);
  log('配置向导已就绪');
})();
