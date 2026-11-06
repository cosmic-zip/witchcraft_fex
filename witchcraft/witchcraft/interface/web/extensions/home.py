"""
Home Dashboard Extension for WitchcraftFEX WebUI.
Encapsulates real-time system monitoring dashboard (CPU, RAM, GPU, Containers, VMs,
Processes, Network Interfaces, and Uptime) with configurable auto-refresh polling.
"""

home_sec = """
<section class="content-sec" id="default" style="display: block;">
    <div class="home-dashboard">
        <!-- Dashboard Top Control Bar -->
        <header class="sec-header" style="display: flex; justify-content: space-between; align-items: center; width: 100%; box-sizing: border-box; margin-bottom: 15px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 16px; font-weight: bold; color: var(--ancient);">⛩️ System Monitor Dashboard</span>
                <span id="home-live-badge" style="background: rgba(0, 200, 80, 0.2); border: 1px solid rgb(0, 200, 80); color: #5f5; font-size: 11px; padding: 2px 8px; border-radius: 12px;">● LIVE</span>
            </div>
            <div class="home-refresh-bar" style="display: flex; align-items: center; gap: 8px; font-size: 12px;">
                <label for="home-interval-select" style="color: var(--text-color); opacity: 0.8;">Auto-Refresh:</label>
                <select id="home-interval-select" class="home-select" onchange="setHomeRefreshInterval(this.value)" style="background: #000000a0; color: var(--ancient); border: 1px solid var(--ancient); border-radius: 4px; padding: 2px 6px; font-family: monospace;">
                    <option value="0">⏸️ Pause</option>
                    <option value="2">⚡ 2s</option>
                    <option value="5" selected>⏱️ 5s</option>
                    <option value="10">🕰️ 10s</option>
                    <option value="30">⏳ 30s</option>
                </select>
                <button type="button" class="btn-downloader" onclick="fetchHomeStats()" style="padding: 2px 10px; font-size: 12px; cursor: pointer;">🔄 Refresh</button>
                <span id="home-countdown" style="opacity: 0.6; font-size: 11px; min-width: 45px;">(5s)</span>
            </div>
        </header>

        <!-- Dashboard Grid Layout -->
        <div class="dashboard-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 15px; margin-bottom: 20px;">
            
            <!-- Widget 1: System Info & Host -->
            <div class="dash-card" style="background: #00000099; border: 1px solid var(--ancient); border-radius: 8px; padding: 12px;">
                <h4 style="margin: 0 0 10px 0; color: var(--ancient); display: flex; justify-content: space-between;">
                    <span>🖥️ Host Overview</span>
                    <span id="dash-os-arch" style="font-size: 11px; color: var(--text-color); opacity: 0.7;">Linux</span>
                </h4>
                <div style="font-size: 12px; line-height: 1.6;">
                    <div><strong>Hostname:</strong> <span id="dash-hostname" style="color: cyan;">--</span></div>
                    <div><strong>Kernel:</strong> <span id="dash-kernel">--</span></div>
                    <div><strong>Uptime:</strong> <span id="dash-uptime" style="color: #5f5;">--</span></div>
                    <div><strong>Load Average:</strong> <span id="dash-loadavg">1m: -- | 5m: -- | 15m: --</span></div>
                </div>
            </div>

            <!-- Widget 2: CPU Usage -->
            <div class="dash-card" style="background: #00000099; border: 1px solid var(--ancient); border-radius: 8px; padding: 12px;">
                <h4 style="margin: 0 0 10px 0; color: var(--ancient); display: flex; justify-content: space-between;">
                    <span>⚡ CPU Utilization</span>
                    <span id="dash-cpu-percent" style="color: #5f5; font-size: 13px;">0%</span>
                </h4>
                <div style="font-size: 12px; margin-bottom: 8px;">
                    <span id="dash-cpu-model" style="display: block; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">Loading...</span>
                    <span id="dash-cpu-cores" style="opacity: 0.7;">-- Cores</span>
                </div>
                <div class="dash-progress-track" style="background: #222; border-radius: 4px; height: 12px; overflow: hidden; border: 1px solid #444;">
                    <div id="dash-cpu-bar" style="background: linear-gradient(90deg, #00c850, var(--ancient)); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
                </div>
            </div>

            <!-- Widget 3: Memory (RAM & Swap) -->
            <div class="dash-card" style="background: #00000099; border: 1px solid var(--ancient); border-radius: 8px; padding: 12px;">
                <h4 style="margin: 0 0 10px 0; color: var(--ancient); display: flex; justify-content: space-between;">
                    <span>🧠 Memory & Swap</span>
                    <span id="dash-mem-percent" style="color: cyan; font-size: 13px;">0%</span>
                </h4>
                <div style="font-size: 12px; margin-bottom: 6px; display: flex; justify-content: space-between;">
                    <span>RAM: <span id="dash-mem-used">0 GB</span> / <span id="dash-mem-total">0 GB</span></span>
                    <span style="opacity: 0.7;">Avail: <span id="dash-mem-avail">0 GB</span></span>
                </div>
                <div class="dash-progress-track" style="background: #222; border-radius: 4px; height: 10px; overflow: hidden; margin-bottom: 8px; border: 1px solid #444;">
                    <div id="dash-mem-bar" style="background: cyan; height: 100%; width: 0%; transition: width 0.3s ease;"></div>
                </div>
                <div style="font-size: 11px; opacity: 0.8; display: flex; justify-content: space-between;">
                    <span>Swap: <span id="dash-swap-used">0 GB</span> / <span id="dash-swap-total">0 GB</span></span>
                    <span id="dash-swap-percent">0%</span>
                </div>
            </div>

            <!-- Widget 4: GPU Hardware -->
            <div class="dash-card" style="background: #00000099; border: 1px solid var(--ancient); border-radius: 8px; padding: 12px;">
                <h4 style="margin: 0 0 10px 0; color: var(--ancient);">🎮 GPU Hardware</h4>
                <div id="dash-gpu-content" style="font-size: 12px; line-height: 1.5;">
                    <span style="opacity: 0.7;">Scanning graphics controllers...</span>
                </div>
            </div>

        </div>

        <!-- Second Row: Virtualization & Network Grid -->
        <div class="dashboard-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 15px; margin-bottom: 20px;">
            
            <!-- Virtual Machines (libvirt) -->
            <div class="dash-card" style="background: #00000099; border: 1px solid var(--ancient); border-radius: 8px; padding: 12px;">
                <h4 style="margin: 0 0 10px 0; color: var(--ancient); display: flex; justify-content: space-between;">
                    <span>🖥️ Libvirt VMs</span>
                    <span id="dash-vms-count" style="font-size: 11px; opacity: 0.8;">0 running</span>
                </h4>
                <div id="dash-vms-list" style="font-size: 12px; max-height: 140px; overflow-y: auto;">
                    <span style="opacity: 0.7;">No virtual machines found</span>
                </div>
            </div>

            <!-- Containers (Docker) -->
            <div class="dash-card" style="background: #00000099; border: 1px solid var(--ancient); border-radius: 8px; padding: 12px;">
                <h4 style="margin: 0 0 10px 0; color: var(--ancient); display: flex; justify-content: space-between;">
                    <span>🐳 Docker Containers</span>
                    <span id="dash-containers-count" style="font-size: 11px; opacity: 0.8;">0 running</span>
                </h4>
                <div id="dash-containers-list" style="font-size: 12px; max-height: 140px; overflow-y: auto;">
                    <span style="opacity: 0.7;">No active containers</span>
                </div>
            </div>

            <!-- Network Interfaces -->
            <div class="dash-card" style="background: #00000099; border: 1px solid var(--ancient); border-radius: 8px; padding: 12px;">
                <h4 style="margin: 0 0 10px 0; color: var(--ancient);">📡 Network Interfaces</h4>
                <div id="dash-network-list" style="font-size: 12px; max-height: 140px; overflow-y: auto;">
                    <span style="opacity: 0.7;">Loading network traffic...</span>
                </div>
            </div>

        </div>

        <!-- Third Row: Active Processes (Htop view) -->
        <div class="dash-card" style="background: #00000099; border: 1px solid var(--ancient); border-radius: 8px; padding: 12px; margin-bottom: 20px;">
            <h4 style="margin: 0 0 10px 0; color: var(--ancient); display: flex; justify-content: space-between; align-items: center;">
                <span>🔥 Active Processes (HTOP)</span>
                <span style="font-size: 11px; opacity: 0.7;">Top CPU & Memory Consumers</span>
            </h4>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
                    <thead>
                        <tr style="border-bottom: 1px solid var(--ancient); color: cyan;">
                            <th style="padding: 6px 8px;">PID</th>
                            <th style="padding: 6px 8px;">USER</th>
                            <th style="padding: 6px 8px;">CPU%</th>
                            <th style="padding: 6px 8px;">MEM%</th>
                            <th style="padding: 6px 8px;">COMMAND</th>
                        </tr>
                    </thead>
                    <tbody id="dash-process-tbody">
                        <tr>
                            <td colspan="5" style="padding: 10px; text-align: center; opacity: 0.6;">Loading processes...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- Dashboard Auto-Refresh & Fetch Logic -->
    <script>
        let homeRefreshIntervalSeconds = 5;
        let homeTimerRemaining = 5;
        let homeIntervalHandle = null;
        let homeCountdownHandle = null;

        function fetchHomeStats() {
            const liveBadge = document.getElementById('home-live-badge');
            if (liveBadge) liveBadge.style.opacity = '0.5';

            fetch('/api/system/stats')
                .then(res => {
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    return res.json();
                })
                .then(data => {
                    renderDashboard(data);
                    if (liveBadge) liveBadge.style.opacity = '1';
                })
                .catch(err => {
                    console.warn('[Home Dashboard] Direct /api/system/stats failed, fallback to /api/exec:', err);
                    // Fallback to /api/exec
                    const ztoken = (document.getElementById('ztoken') || {}).value || '';
                    const formData = new URLSearchParams();
                    formData.append('EZECsystem_stats', 'system.stats');
                    formData.append('json', 'true');
                    formData.append('ztoken', ztoken);

                    fetch('/api/exec', {
                        method: 'POST',
                        body: formData
                    })
                    .then(r => r.json())
                    .then(data => {
                        renderDashboard(data);
                        if (liveBadge) liveBadge.style.opacity = '1';
                    })
                    .catch(e => console.error('[Home Dashboard] Failed to load stats:', e));
                });
        }

        function renderDashboard(data) {
            if (!data) return;

            // 1. Host Overview
            if (data.os) {
                document.getElementById('dash-hostname').textContent = data.os.hostname || '--';
                document.getElementById('dash-kernel').textContent = `${data.os.system} ${data.os.kernel}`;
                document.getElementById('dash-os-arch').textContent = data.os.arch || '';
            }
            if (data.uptime) {
                document.getElementById('dash-uptime').textContent = data.uptime.formatted || '--';
            }
            if (data.cpu && data.cpu.loadavg) {
                const l = data.cpu.loadavg;
                document.getElementById('dash-loadavg').textContent = `1m: ${l['1m']} | 5m: ${l['5m']} | 15m: ${l['15m']}`;
            }

            // 2. CPU
            if (data.cpu) {
                document.getElementById('dash-cpu-model').textContent = data.cpu.model || 'Generic CPU';
                document.getElementById('dash-cpu-cores').textContent = `${data.cpu.cores} Physical/Logical Cores`;
                const cpuUsage = data.cpu.usage_percent || 0;
                document.getElementById('dash-cpu-percent').textContent = `${cpuUsage}%`;
                const cpuBar = document.getElementById('dash-cpu-bar');
                if (cpuBar) {
                    cpuBar.style.width = `${Math.min(100, cpuUsage)}%`;
                    cpuBar.style.background = cpuUsage > 80 ? 'red' : (cpuUsage > 50 ? 'yellow' : 'linear-gradient(90deg, #00c850, var(--ancient))');
                }
            }

            // 3. Memory
            if (data.memory) {
                const mem = data.memory;
                document.getElementById('dash-mem-percent').textContent = `${mem.percent_used || 0}%`;
                document.getElementById('dash-mem-used').textContent = `${mem.used_gb || 0} GB`;
                document.getElementById('dash-mem-total').textContent = `${mem.total_gb || 0} GB`;
                document.getElementById('dash-mem-avail').textContent = `${mem.available_gb || 0} GB`;
                const memBar = document.getElementById('dash-mem-bar');
                if (memBar) {
                    memBar.style.width = `${Math.min(100, mem.percent_used || 0)}%`;
                }
                document.getElementById('dash-swap-used').textContent = `${mem.swap_used_gb || 0} GB`;
                document.getElementById('dash-swap-total').textContent = `${mem.swap_total_gb || 0} GB`;
                document.getElementById('dash-swap-percent').textContent = `${mem.swap_percent_used || 0}%`;
            }

            // 4. GPU
            const gpuContainer = document.getElementById('dash-gpu-content');
            if (gpuContainer && data.gpu) {
                if (data.gpu.length === 0) {
                    gpuContainer.innerHTML = '<span style="opacity: 0.6;">No dedicated GPU detected.</span>';
                } else {
                    gpuContainer.innerHTML = data.gpu.map(g => `
                        <div style="margin-bottom: 6px; padding: 4px 6px; background: #111; border-radius: 4px;">
                            <strong>🎮 ${g.name}</strong>
                            ${g.vram_total_mb ? `<div style="font-size: 11px; opacity: 0.8;">VRAM: ${g.vram_used_mb}MB / ${g.vram_total_mb}MB (${g.utilization_percent || 0}%) | Temp: ${g.temp_c}°C</div>` : ''}
                        </div>
                    `).join('');
                }
            }

            // 5. VMs
            const vmContainer = document.getElementById('dash-vms-list');
            if (vmContainer && data.vms) {
                document.getElementById('dash-vms-count').textContent = `${data.vms.running || 0} running / ${data.vms.total || 0} total`;
                if (!data.vms.items || data.vms.items.length === 0) {
                    vmContainer.innerHTML = '<span style="opacity: 0.6;">No libvirt virtual machines.</span>';
                } else {
                    vmContainer.innerHTML = data.vms.items.map(v => `
                        <div style="display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #222;">
                            <span>${v.name}</span>
                            <span style="color: ${v.running ? '#5f5' : '#888'}; font-size: 11px;">[${v.state}]</span>
                        </div>
                    `).join('');
                }
            }

            // 6. Containers
            const ctContainer = document.getElementById('dash-containers-list');
            if (ctContainer && data.containers) {
                document.getElementById('dash-containers-count').textContent = `${data.containers.running || 0} running / ${data.containers.total || 0} total`;
                if (!data.containers.items || data.containers.items.length === 0) {
                    ctContainer.innerHTML = '<span style="opacity: 0.6;">No Docker containers found.</span>';
                } else {
                    ctContainer.innerHTML = data.containers.items.map(c => `
                        <div style="display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #222;">
                            <span title="${c.image}">${c.name || c.id}</span>
                            <span style="color: ${c.running ? '#5f5' : '#888'}; font-size: 11px;">[${c.status}]</span>
                        </div>
                    `).join('');
                }
            }

            // 7. Network
            const netContainer = document.getElementById('dash-network-list');
            if (netContainer && data.network) {
                netContainer.innerHTML = data.network.map(n => `
                    <div style="display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #222;">
                        <strong>📡 ${n.interface}</strong>
                        <span style="font-size: 11px; opacity: 0.8;">RX: ${n.rx_mb} MB | TX: ${n.tx_mb} MB</span>
                    </div>
                `).join('');
            }

            // 8. Processes (Htop table)
            const procTbody = document.getElementById('dash-process-tbody');
            if (procTbody && data.processes) {
                if (data.processes.length === 0) {
                    procTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; opacity: 0.6;">No active processes reported</td></tr>';
                } else {
                    procTbody.innerHTML = data.processes.map(p => `
                        <tr style="border-bottom: 1px solid #1a1a1a;">
                            <td style="padding: 4px 8px; font-family: monospace; color: #888;">${p.pid}</td>
                            <td style="padding: 4px 8px; color: cyan;">${p.user}</td>
                            <td style="padding: 4px 8px; font-weight: bold; color: ${parseFloat(p.cpu) > 20 ? 'red' : '#5f5'};">${p.cpu}%</td>
                            <td style="padding: 4px 8px; color: var(--ancient);">${p.mem}%</td>
                            <td style="padding: 4px 8px; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${p.command}">${p.command}</td>
                        </tr>
                    `).join('');
                }
            }
        }

        function setHomeRefreshInterval(seconds) {
            homeRefreshIntervalSeconds = parseInt(seconds, 10);
            homeTimerRemaining = homeRefreshIntervalSeconds;
            
            if (homeIntervalHandle) clearInterval(homeIntervalHandle);
            if (homeCountdownHandle) clearInterval(homeCountdownHandle);

            const countdownEl = document.getElementById('home-countdown');
            if (homeRefreshIntervalSeconds <= 0) {
                if (countdownEl) countdownEl.textContent = '(Paused)';
                return;
            }

            // Countdown ticker
            homeCountdownHandle = setInterval(() => {
                homeTimerRemaining--;
                if (homeTimerRemaining <= 0) {
                    homeTimerRemaining = homeRefreshIntervalSeconds;
                }
                if (countdownEl) countdownEl.textContent = `(${homeTimerRemaining}s)`;
            }, 1000);

            // Fetcher interval
            homeIntervalHandle = setInterval(() => {
                fetchHomeStats();
            }, homeRefreshIntervalSeconds * 1000);
        }

        // Initialize dashboard when document loads or section is displayed
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                fetchHomeStats();
                setHomeRefreshInterval(5);
            });
        } else {
            fetchHomeStats();
            setHomeRefreshInterval(5);
        }
    </script>
</section>
"""

home = {
    "section": home_sec,
    "button": '<button type="submit" class="sidebar-submit" onclick="toggleSection(\'default\')">㊊ Home</button>'
}
