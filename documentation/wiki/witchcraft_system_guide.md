# WitchcraftFEX — Sistema, Arquitetura & Guia de Engenharia

> **Versão do Ecossistema**: `v1.0.0-devel`  
> **Classificação**: Offensive Security Toolkit & Cyberdeck Runtime  
> **Público-alvo**: Engenheiros de Segurança, Desenvolvedores de Ferramental, Operadores Ofensivos

---

## 1. Visão Geral do Projeto

O **WitchcraftFEX** (WFEX) é um toolkit ofensivo, cyberdeck runtime e motor de automação modular. Ele unifica centenas de utilitários de rede, análise forense, OSINT, varredura de vulnerabilidades, engenharia reversa, pós-exploração e inteligência artificial local em uma infraestrutura coesa, extensível e agnóstica a ambiente.

O repositório é organizado de forma modular em três camadas fundamentais:

```
witchcraft_fex/
├── witchcraft/
│   ├── main.py                     # Entry point único CLI
│   ├── witchcraft/
│   │   ├── metalcore/              # Motor central de execução e roteamento (core.py)
│   │   ├── interface/              # Camada de interfaces (AI/Harpia, MCP, CLI, Web)
│   │   ├── modules/                # Módulos operacionais (scanner, osint, server, calicrafy...)
│   │   └── settings.py             # Registro mestre de funções (FN_REGISTRY)
│   └── spellbook/                  # Grimório de dados, modelos, pacotes e binários
├── documentation/
│   ├── wiki/                       # Documentação técnica e operacional
│   └── manifest/                   # Manifestos de evolução e refatoração
└── snapcraft.yaml / Dockerfile     # Empacotamento para distribuição universal
```

---

## 2. Motor Metalcore (`metalcore/core.py`)

O **Metalcore** é a fundação do WitchcraftFEX. Ele não apenas fornece primitivas de runtime, mas atua como o mediador entre comandos CLI arbitrários, binds declarativos e execuções seguras em subprocessos.

### Componentes Principais

1. **Roteamento Shell e CLI (`net_shell_router`)**:
   - É chamado diretamente em `main.py` recebendo o `FN_REGISTRY`.
   - Lê os argumentos via `sys.argv`, aplica filtros globais (`--output_mode_html`, `--output_mode_none`) e despacha:
     - Comandos reservados: `version`, `help`, `manual`.
     - Funções nativas registradas em `FN_REGISTRY` (prefixadas ou não com `wfex.`).
     - Binds declarativos do catálogo (`rocketdb_v2.json`) executados via `net_parser`.
     - Execução shell arbitrária caso habilitado via `NT_ENABLE_ARBITRARY_SHELL`.

2. **Parser de Binds (`net_parser`)**:
   - Varre o banco de dados `rocketdb_v2.json`.
   - Identifica os argumentos marcados como `@@nome_parametro` no template do bind e os substitui pelos valores passados na CLI via `search_arg(args_v, "nome_parametro")`.
   - Dispara a execução via `net_exec` e trata `stdout`, `stderr` e status code.

3. **Executor e Logger (`net_exec` e `net_logger`)**:
   - `net_exec`: Invoca processos através de `subprocess.Popen(..., shell=True)` capturando streams de forma estruturada (`{"stdout": ..., "stderr": ..., "status": ...}`).
   - `net_logger`: Suporta modos de cor ANSI terminal e modo HTML (`<span>` com cores inline), permitindo que saídas de terminal sejam renderizadas nativamente na WebUI ou no MCP sem sequências quebradas.

4. **Sistema de Ajuda Dinâmica (`dynamic_manual`)**:
   - Fornece inspeção interativa de todos os binds e categorias com filtros:
     ```bash
     ./main.py help --option category     # Lista categorias disponíveis
     ./main.py help --option manual       # Exibe o manual completo do sistema
     ./main.py help --option network      # Filtra binds de rede
     ./main.py help --option all          # Dump completo de argumentos e binds
     ```

5. **Variáveis de Ambiente Críticas**:
   - `NT_DATAROOT`: Raiz do repositório de recursos (padrão: `spellbook/`).
   - `NT_SETUP_COLORS`: Formato de saída (`color`, `none`, `html`).
   - `NT_COSMIC_SIGKEY`: Chave HMAC mestra de autenticação do ecossistema.
   - `NT_DEBUG`: Ativa logging detalhado de cada comando executado.

---

## 3. Spellbook: O Grimório de Recursos (`spellbook/`)

O **Spellbook** funciona como o "disco rígido" de conhecimento e ferramentas do monorepo. Ele armazena tudo o que o motor e os operadores necessitam para execução:

| Diretório | Função e Conteúdo |
| :--- | :--- |
| `database/` | `rocketdb_v2.json`: Catálogo mestre com mais de 200 binds parametrizados, documentados com categoria e backend (`cmd_backend`). |
| `models/` | Modelos de IA locais GGUF (ex: Hermes-3-Llama-3.2-3B) com symlink `model.gguf` para carregamento imediato. |
| `pkg/` | Utilitários pré-compilados e interpretadores: `busybox`, `llama/` (llama-server compilado), `server/` (servidor HTTP assíncrono), `xcript/` (linguagem estática). |
| `misc/` | Arquivos e matrizes de fontes ASCII/Unicode (`calicrafy.json`, `calicrafy.ascii`) para renderização tipográfica no terminal. |
| `webui/` | Assets compilados para a interface gráfica web (`index.html`, `ui.css`, `ui.js`, imagens). |
| `bloodmoon-os/` | Configurações de kernel e buildroot para appliances embarcados. |
| `provider/` | Configurações de telemetria externa, Prometheus e dashboards Grafana. |
| `wordlists/` / `fuzzing/` | Dicionários de força bruta, payloads e patterns de ataque. |

---

## 4. Interfaces: AI/Harpia, MCP, CLI & Web

O diretório `witchcraft/witchcraft/interface/` provê as vias de controle humano e automatizado:

```
witchcraft/interface/
├── ai/                     # Agente Harpia autônomo (harpia_agent.py)
├── mcp/                    # Model Context Protocol Server (mcp_server.py)
├── cli/                    # REPL e sessões interativas de terminal (interactive.py)
└── web/                    # Backend gerador e extensões WebUI (generator.py, extensions/)
```

### 4.1. Harpia: Agente de IA Ofensiva em Loop ReAct (`interface/ai/harpia_agent.py`)
- Conecta-se diretamente à API local do `llama-server` (`http://localhost:5599/v1/chat/completions`).
- Executa um **loop ReAct multi-step** (`max_steps=8`) capaz de encadear múltiplas ferramentas MCP e injetar dinamicamente binds descobertas via `witchcraft_search_binds`.
- **Output Integral vs Sumário Truncado**: toda saída de comando é exibida integralmente (sem truncamento) na CLI e na WebUI; apenas a cópia enviada ao contexto do LLM para raciocínio/sumário é truncada (Head + Tail).
- **Modo Shell Puro (`shell_mode`)**: suporta `propose` (padrão, com aprovação humana via `[y/N/e]` na CLI ou `/api/harpia/approve` na WebUI), `auto` e `off`.
- Documentação completa em [Harpia AI: Loop Agentic, MCP & Shell Puro](harpia_agentic_loop.md).

### 4.2. Servidor MCP (`interface/mcp/mcp_server.py`)
- Implementa o padrão da especificação **Model Context Protocol (JSON-RPC 2.0)**.
- Expõe automaticamente:
  - Todas as ferramentas do `rocketdb_v2.json` como MCP Tools (`witchcraft_search_binds`, `scanner_dns`, `nmap`, etc.).
  - Telemetria de sistema ao vivo via `witchcraft_system_stats`.
  - Execução estática de automações na linguagem própria via `witchcraft_xcript_eval`.
  - Execução controlada de shell puro via `witchcraft_shell_exec` (respeitando `NT_ENABLE_ARBITRARY_SHELL`).
- **Modos de operação**:
  - `stdio`: Para integração com ferramentas como Claude Desktop, IDEs ou scripts CLI (`./main.py server.mcp`).
  - `HTTP JSON-RPC 2.0`: Exposto no endpoint `/api/mcp` pelo servidor web na porta `5500`.

### 4.3. Interface CLI Interativa (`interface/cli/interactive.py`)
- REPL dedicado acionado via `./main.py harpia.cli`.
- Suporta troca de modos (`/mode agent|auto|off|shell`), ajuste de passos (`/steps <N>`), aprovação interativa de shell proposto (`[y/N/e]`) e atalhos diretos sem depender de IA: `/shell <cmd>`, `!<cmd>`, `/mcp <tool> {"arg": "val"}` ou `/xcript <code>`.

### 4.4. WebUI & Gerador Estático (`interface/web/`)
- `generator.py`: Motor em Python que compila o arquivo estático `spellbook/webui/index.html` gerando formulários HTML para todos os binds do `rocketdb_v2.json`, registrando as extensões ativas (`Haki`, `Handbook`, `Harpia AI`).
- O frontend consome os endpoints HTTP do servidor Python:
  - `/api/exec`: Executa comandos autenticados via token HMAC ou cookie de sessão.
  - `/api/harpia/chat`: Interface de chat conversacional com Harpia e MCP.
  - `/api/mcp`: Endpoint HTTP MCP JSON-RPC.

---

## 5. Deploy & Execução com Docker

O WitchcraftFEX pode ser orquestrado inteiramente via containers para isolamento total da pilha:

### 5.1. Construção da Imagem
A partir da raiz do monorepo ou de `witchcraft/`:

```bash
docker build -t witchcraftfex:latest -f witchcraft/dockerfile witchcraft/
```

### 5.2. Orquestração com Docker Compose
O arquivo `witchcraft/docker-compose.yml` provê o ecossistema completo:
- Servidor Witchcraft principal (portas `5500` e `5599`)
- Portainer (porta `9443`) para monitoramento de containers
- Prometheus (porta `9000`) coletando métricas do toolkit
- Grafana (porta `3000`) com dashboards pré-carregados

```bash
cd witchcraft/
docker compose up -d
```

---

## 6. Distribuição com Snapcraft & Setup de Build

O WitchcraftFEX é empacotado como Snap (`witchcraftfex`) sob confinamento estrito (`confinement: strict`) na base Ubuntu Core (`core26`).

### 6.1. Requisitos e Setup Inicial do Ambiente de Build
Para compilar o snap na máquina local:

```bash
# 1. Instalar o utilitário oficial Snapcraft e o multipass/LXD
sudo apt update
sudo apt install snapd -y
sudo snap install snapcraft --classic

# 2. Inicializar o backend de build (LXD ou Multipass)
sudo snap install lxd
sudo lxd init --auto
sudo usermod -aG lxd $USER
newgrp lxd
```

### 6.2. Compilando o Pacote Snap
Na raiz do monorepo onde reside `snapcraft.yaml`:

```bash
# Build em ambiente limpo e isolado
snapcraft --use-lxd

# Para build destrutivo direto no host (ex: containers ou CI)
snapcraft --destructive-mode
```

### 6.3. Instalação e Permissões
Após a geração do pacote `.snap`:

```bash
sudo snap install witchcraftfex_1.0.0_amd64.snap --dangerous

# Conectar os plugs necessários para rede, montagem e home
sudo snap connect witchcraftfex:network
sudo snap connect witchcraftfex:network-bind
sudo snap connect witchcraftfex:home
sudo snap connect witchcraftfex:removable-media
```

---

## 7. Manifesto de Refatoração do Frontend

> [!IMPORTANT]
> A camada de interface WebUI (`spellbook/webui/`) passará por uma refatoração arquitetural completa para migrar de templates monolíticos em strings para uma arquitetura moderna orientada a componentes.  
> Toda a especificação técnica e plano de migração do frontend está documentado em:  
> 🔗 [Manifesto de Refatoração do Frontend](../manifest/manifest_frontend_refactor.md)
