"""
Harpia AI & MCP Chat Extension for WitchcraftFEX WebUI.
Provides a full chat interface connected to local LLM (llama-server) and Witchcraft MCP tools.
"""

harpia_section = """
<section class="content-sec" id="harpia_ai">
    <header class="sec-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 16px; font-weight: bold; color: var(--ancient);">🦅 Harpia AI — MCP Agent</span>
            <span id="harpia-status-badge" style="background: rgba(0, 200, 80, 0.2); border: 1px solid rgb(0, 200, 80); color: #5f5; font-size: 11px; padding: 2px 8px; border-radius: 12px;">● MCP READY</span>
        </div>
        <div style="display: flex; gap: 8px;">
            <button type="button" class="btn-downloader" onclick="switchHarpiaView('chat')" style="padding: 4px 10px; font-size: 12px; cursor: pointer;">💬 Agent Chat</button>
            <button type="button" class="btn-downloader" onclick="switchHarpiaView('llama')" style="padding: 4px 10px; font-size: 12px; cursor: pointer;">🦙 Raw Llama UI</button>
            <button type="button" class="btn-downloader" onclick="clearHarpiaChat()" style="padding: 4px 10px; font-size: 12px; cursor: pointer;">🗑️ Clear</button>
        </div>
    </header>

    <!-- Harpia Native MCP Chat View -->
    <div id="harpia-chat-view" style="display: flex; flex-direction: column; height: 72vh; background: #000000a8; border: 1px solid var(--ancient); border-radius: 8px; overflow: hidden;">
        <div id="harpia-messages" style="flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; font-family: monospace; font-size: 13px;">
            <div style="background: #111111cc; border-left: 3px solid var(--ancient); padding: 10px 12px; border-radius: 4px;">
                <strong style="color: var(--ancient);">🦅 Harpia:</strong>
                <div style="margin-top: 4px; line-height: 1.5;">
                    Harpia MCP Agent online. Ask me to run scans, inspect system stats, or execute Xcript automation.<br>
                    <span style="opacity: 0.75; font-size: 11px;">Shortcuts: <code>/mcp witchcraft_search_binds {"cmd_backend":"nmap"}</code> | <code>/xcript declare x = "hello"; echo x</code></span>
                </div>
            </div>
        </div>

        <form id="harpia-chat-form" onsubmit="sendHarpiaMessage(event)" style="display: flex; gap: 8px; padding: 12px; background: #0a0a0ae0; border-top: 1px solid var(--ancient);">
            <input
                type="text"
                id="harpia-input"
                placeholder="Ask Harpia AI or run /mcp <tool> <json> or /xcript <code>..."
                autocomplete="off"
                style="flex: 1; background: #141414; color: var(--text-color, #fff); border: 1px solid var(--ancient); border-radius: 6px; padding: 10px 12px; font-family: monospace; font-size: 13px;"
            />
            <button
                type="submit"
                id="harpia-send-btn"
                class="form-text-submit"
                style="width: auto; padding: 0 20px; margin: 0; cursor: pointer;"
            >
                Send 🦅
            </button>
        </form>
    </div>

    <!-- Raw Llama-Server Iframe View (Toggleable) -->
    <div id="harpia-llama-view" style="display: none;">
        <iframe src="http://localhost:5599" class="outputer outputer-xl" frameborder="0"></iframe>
    </div>

    <script>
        let harpiaHistory = [];

        function switchHarpiaView(mode) {
            const chatView = document.getElementById('harpia-chat-view');
            const llamaView = document.getElementById('harpia-llama-view');
            if (mode === 'llama') {
                chatView.style.display = 'none';
                llamaView.style.display = 'block';
            } else {
                chatView.style.display = 'flex';
                llamaView.style.display = 'none';
            }
        }

        function escapeHarpiaHtml(str) {
            return String(str || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        }

        function appendHarpiaBubble(role, text, toolCalls) {
            const container = document.getElementById('harpia-messages');
            if (!container) return;

            const isUser = role === 'user';
            const wrapper = document.createElement('div');
            wrapper.style.background = isUser ? '#1b1b2fcc' : '#111111cc';
            wrapper.style.borderLeft = isUser ? '3px solid cyan' : '3px solid var(--ancient)';
            wrapper.style.padding = '10px 12px';
            wrapper.style.borderRadius = '4px';

            let toolsHtml = '';
            if (Array.isArray(toolCalls) && toolCalls.length > 0) {
                toolsHtml = toolCalls.map(tc => `
                    <div style="margin: 6px 0; padding: 8px; background: #050505; border: 1px solid #333; border-radius: 4px; font-size: 12px;">
                        <div style="color: cyan; font-weight: bold; margin-bottom: 4px;">
                            ⚙️ MCP Tool: ${escapeHarpiaHtml(tc.name)} <span style="opacity:0.7;">${escapeHarpiaHtml(JSON.stringify(tc.arguments || {}))}</span>
                        </div>
                        <pre style="margin: 0; white-space: pre-wrap; word-break: break-word; color: #ddd; max-height: 220px; overflow-y: auto;">${escapeHarpiaHtml(tc.output)}</pre>
                    </div>
                `).join('');
            }

            const title = isUser
                ? '<strong style="color: cyan;">👤 Operator:</strong>'
                : '<strong style="color: var(--ancient);">🦅 Harpia:</strong>';

            wrapper.innerHTML = `
                ${title}
                ${toolsHtml}
                <div style="margin-top: 4px; white-space: pre-wrap; line-height: 1.5;">${escapeHarpiaHtml(text)}</div>
            `;
            container.appendChild(wrapper);
            container.scrollTop = container.scrollHeight;
        }

        function clearHarpiaChat() {
            harpiaHistory = [];
            const container = document.getElementById('harpia-messages');
            if (container) container.innerHTML = '';
            appendHarpiaBubble('assistant', 'Chat history cleared. Ready for next operation.', []);
        }

        function sendHarpiaMessage(e) {
            e.preventDefault();
            const input = document.getElementById('harpia-input');
            const btn = document.getElementById('harpia-send-btn');
            const badge = document.getElementById('harpia-status-badge');
            if (!input || !input.value.trim()) return;

            const prompt = input.value.trim();
            input.value = '';
            appendHarpiaBubble('user', prompt, []);

            if (btn) btn.disabled = true;
            if (badge) {
                badge.textContent = '● THINKING...';
                badge.style.color = 'yellow';
            }

            const ztoken = (document.getElementById('ztoken') || {}).value || '';

            fetch('/api/harpia/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Auth-Token': ztoken
                },
                body: JSON.stringify({
                    prompt: prompt,
                    history: harpiaHistory,
                    ztoken: ztoken
                })
            })
            .then(r => r.json())
            .then(data => {
                const reply = data.reply || data.error || 'No response';
                const calls = data.tool_calls || [];
                appendHarpiaBubble('assistant', reply, calls);
                harpiaHistory.push({ role: 'user', content: prompt });
                harpiaHistory.push({ role: 'assistant', content: reply });
                if (badge) {
                    badge.textContent = data.status === 'offline' ? '● LLM OFFLINE (MCP DIRECT)' : '● MCP READY';
                    badge.style.color = data.status === 'offline' ? 'orange' : '#5f5';
                }
            })
            .catch(err => {
                appendHarpiaBubble('assistant', '[Connection Error] ' + err.message, []);
            })
            .finally(() => {
                if (btn) btn.disabled = false;
            });
        }
    </script>
</section>
"""

harpia = {
    "section": harpia_section,
    "button": '<button type="submit" class="sidebar-submit" onclick="toggleSection(\'harpia_ai\')">㊊ Harpia</button>',
}

