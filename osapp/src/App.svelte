<script>
  import { onMount } from 'svelte';

  let page = 'chat';
  let health = { ok: false, text: '检查中…' };
  let messages = [
    { role: 'bot', text: '你好，我是 llama-mem。本地记忆、离线运行。', meta: 'system' }
  ];
  let input = '';
  let busy = false;
  let memories = [];
  let memQuery = '';
  let memError = '';
  let config = { api: 'http://127.0.0.1:8765', model: 'Qwen2.5-14B-Instruct-Q4_K_M' };
  let autostart = false;
  let autoService = false;
  let statusNote = '';
  let composerEl;

  const api = window.os || null;

  async function refreshHealth() {
    if (!api) { health = { ok: false, text: '需要在桌面壳中运行' }; return; }
    const h = await api.health();
    health = h.ok ? { ok: true, text: '服务在线' } : { ok: false, text: '服务未启动' };
  }

  async function startService() {
    if (!api) return;
    statusNote = '启动中…';
    const r = await api.start();
    statusNote = r.ok ? ('已启动 pid=' + r.pid) : (r.error || '启动失败');
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 1000));
      const h = await api.health();
      if (h.ok) { health = { ok: true, text: '服务在线' }; statusNote = '服务在线'; return; }
    }
    health = { ok: false, text: '启动超时' };
  }

  async function stopService() {
    if (!api) return;
    const r = await api.stop();
    statusNote = r.ok ? '已停止' : (r.error || '停止失败');
    await refreshHealth();
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    input = '';
    messages = [...messages, { role: 'user', text, meta: 'you' }];
    busy = true;
    try {
      if (!api) throw new Error('桌面 API 不可用');
      const r = await api.ask(text);
      const a = r.data || {};
      const ans = a.answer || a.error || JSON.stringify(a);
      messages = [...messages, {
        role: 'bot', text: ans,
        meta: [a.state, a.latency_s ? (a.latency_s + 's') : '', a.block_ids ? ('blocks ' + a.block_ids.join(',')) : ''].filter(Boolean).join(' · ')
      }];
    } catch (e) {
      messages = [...messages, { role: 'bot', text: '请求失败：' + e.message, meta: 'error' }];
    } finally { busy = false; }
  }

  async function loadMemories() {
    if (!api) return;
    memError = '';
    try {
      const r = await api.memories();
      const d = r.data;
      memories = Array.isArray(d) ? d : (d.memories || []);
    } catch (e) { memError = e.message; }
  }

  async function forget(id) {
    if (!api) return;
    await api.forget(id);
    await loadMemories();
  }

  async function toggleAutostart() {
    if (!api) return;
    autostart = !autostart;
    await api.autostartSet(autostart);
  }

  async function toggleAutoService() {
    if (!api) return;
    autoService = !autoService;
    config = { ...config, autoService };
    await api.configSet(config);
  }

  let filtered = [];
  $: filtered = memories.filter(m =>
    !memQuery || JSON.stringify(m).toLowerCase().includes(memQuery.toLowerCase()));

  onMount(async () => {
    if (api) {
      try { config = { ...config, ...(await api.configGet() || {}) }; } catch {}
      autoService = !!config.autoService;
      try { autostart = await api.autostartGet(); } catch {}
    }
    refreshHealth();
    loadMemories();
    const offHotkey = api && api.onHotkey
      ? api.onHotkey(() => {
          page = 'chat';
          setTimeout(() => composerEl && composerEl.focus(), 60);
        })
      : null;
    const t = setInterval(refreshHealth, 5000);
    return () => { clearInterval(t); if (offHotkey) offHotkey(); };
  });
</script>

<div class="shell">
  <aside class="sidebar">
    <div class="brand">
      <div class="logo"></div>
      <div><b>llama-mem</b><span>local memory · offline</span></div>
    </div>
    <nav class="nav">
      <button class:active={page === 'chat'} on:click={() => page = 'chat'}>💬 对话</button>
      <button class:active={page === 'memory'} on:click={() => { page = 'memory'; loadMemories(); }}>🧠 记忆库</button>
      <button class:active={page === 'status'} on:click={() => { page = 'status'; refreshHealth(); }}>📊 状态</button>
      <button class:active={page === 'settings'} on:click={() => page = 'settings'}>⚙️ 设置</button>
    </nav>
    <div class="foot">
      <div class="pill"><span class="dot" class:ok={health.ok}></span>{health.text}</div>
      <div style="margin-top:8px">v0.1 · tray shell</div>
    </div>
  </aside>

  <main class="main">
    <header class="topbar">
      <h1>{page === 'chat' ? '对话' : page === 'memory' ? '记忆库' : page === 'status' ? '运行状态' : '设置'}</h1>
      <div class="row">
        <span class="pill"><span class="dot" class:ok={health.ok}></span>{health.text}</span>
        <button class="ghost" on:click={refreshHealth}>刷新</button>
      </div>
    </header>

    <section class="content">
      {#if page === 'chat'}
        <div class="chat" style="height:100%">
          <div class="messages">
            {#if messages.length === 0}<div class="empty">开始对话</div>{/if}
            {#each messages as m}
              <div class="msg {m.role}">
                {m.text}
                {#if m.meta}<div class="meta">{m.meta}</div>{/if}
              </div>
            {/each}
            {#if busy}<div class="msg bot"><span class="muted">思考中…</span></div>{/if}
          </div>
          <div class="composer">
            <textarea bind:this={composerEl} bind:value={input} placeholder="问点什么，或说“记住：…”" on:keydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}></textarea>
            <button class="primary" on:click={send} disabled={busy}>发送</button>
          </div>
        </div>

      {:else if page === 'memory'}
        <div class="row" style="margin-bottom:14px">
          <input style="flex:1" bind:value={memQuery} placeholder="搜索记忆…" />
          <button on:click={loadMemories}>刷新</button>
        </div>
        {#if memError}<div class="error">{memError}</div>{/if}
        <div class="memlist">
          {#each filtered as m}
            <div class="mem">
              <div class="id">#{m.id}</div>
              <div class="text">{m.first_line || m.text || ''}<div class="muted small">{m.len || m.n_tokens || ''} {m.n_tokens ? 'tokens' : ''}</div></div>
              <div class="date">{m.created_at || ''}</div>
              <button class="danger ghost" on:click={() => forget(m.id)}>删除</button>
            </div>
          {:else}
            <div class="empty">没有记忆，或服务未启动</div>
          {/each}
        </div>

      {:else if page === 'status'}
        <div class="kv">
          <div class="card"><div class="muted small">服务</div><div class="n">{health.ok ? '在线' : '离线'}</div></div>
          <div class="card"><div class="muted small">记忆</div><div class="n">{memories.length}</div></div>
          <div class="card"><div class="muted small">桌面壳</div><div class="n">v0.1</div></div>
        </div>
        <div class="card" style="margin-top:16px">
          <div class="spread">
            <div><b>本地服务</b><div class="muted small">127.0.0.1:8765 · 仅本机</div></div>
            <div class="row">
              <button on:click={startService}>启动</button>
              <button on:click={stopService}>停止</button>
            </div>
          </div>
          <div class="muted small" style="margin-top:12px">{statusNote || '启动后托盘常驻；关闭窗口不会退出。'}</div>
        </div>

      {:else if page === 'settings'}
        <div class="card">
          <div class="setting">
            <div><b>开机自启</b><div class="muted small">登录 Windows 后自动启动托盘</div></div>
            <button class="toggle" class:on={autostart} on:click={toggleAutostart} aria-label="开机自启"></button>
          </div>
          <div class="setting">
            <div><b>启动时启动本地服务</b><div class="muted small">托盘启动后自动拉起 8765（14B 加载较慢）</div></div>
            <button class="toggle" class:on={autoService} on:click={toggleAutoService} aria-label="启动时启动服务"></button>
          </div>
          <div class="setting">
            <div><b>本地 API</b><div class="muted small">{config.api}</div></div>
            <span class="muted small">只监听 127.0.0.1</span>
          </div>
          <div class="setting">
            <div><b>模型</b><div class="muted small">{config.model}</div></div>
            <span class="muted small">14B Q4_K_M</span>
          </div>
          <div class="setting">
            <div><b>数据目录</b><div class="muted small">D:\llama-mem\kvmem\daily</div></div>
            <button class="ghost" on:click={() => api && api.openPath('D:\\llama-mem\\kvmem\\daily')}>打开</button>
          </div>
        </div>
      {/if}
    </section>
  </main>
</div>