# Manifesto de Refatoração da Interface Web (WebUI) — WitchcraftFEX

> **Identificador**: `MANIFEST-FE-2026-REF`  
> **Estado**: Planejado / Em Transição  
> **Componente Alvo**: `witchcraft/spellbook/webui/` & `witchcraft/interface/web/`

---

## 1. Motivação e Diagnóstico da Arquitetura Atual

Atualmente, o frontend do WitchcraftFEX é gerado a partir de um compilador em Python (`interface/web/generator.py`) que interpola strings e gera um arquivo estático monolítico `index.html` com cerca de 10.000 linhas de HTML/CSS/JS acoplados.

### Problemas Identificados
1. **Monolito de Strings**: Cada bind do `rocketdb_v2.json` gera uma tag `<section>` estática individual no HTML final, gerando um payload desnecessariamente pesado (~10 MB).
2. **Duplicação de Código**: Fragmentos de interface para execuções HTMX e iframes do `llama-server` replicados em múltiplos templates.
3. **Acoplamento Severo**: Alterações no layout ou em temas exigem reconstrução manual do arquivo via comando de build (`./main.py build.web`).
4. **Gerenciamento de Estado**: O chat da Harpia mantém histórico apenas em memória no navegador; faltam componentes reativos e persistência de sessões de operação.

---

## 2. Objetivos da Refatoração

1. **Separação Completa entre Backend e Frontend**: O backend Python (`pkg/server/server.py`) servirá estritamente uma API RESTful + MCP JSON-RPC, eliminando a injeção dinâmica de templates via concatenação de strings.
2. **Carregamento Dinâmico de Ferramentas (Lazy Catalog)**: O catálogo de binds (`rocketdb_v2.json`) será consumido via requisições `/api/tools` em JSON, gerando as interfaces de comando no DOM sob demanda.
3. **Arquitetura SPA / Componentizada**: Migração para componentes modulares limpos (HTML5 nativo, web components ou framework leve sem build step pesado).
4. **Terminal & Saída Reativa**: Renderização contínua de streams e logs de execução com terminal virtual (xterm.js ou renderizador ANSI/HTML leve).
5. **Cyberdeck Theme Engine**: Sistema de temas nativo em CSS custom properties (Cyber, Punk, Bloodmoon, Matrix, Stealth, Cosmic).

---

## 3. Especificação da Nova Arquitetura de Diretórios

O novo layout do frontend substituirá a estrutura de arquivos monolítica por uma árvore modular:

```
spellbook/webui/
├── index.html                   # Shell mínimo de montagem SPA
├── assets/
│   ├── css/
│   │   ├── core.css             # Grid do cyberdeck, reset e tipografia
│   │   ├── themes.css           # Paletas de cores (custom properties)
│   │   └── components.css       # Estilização de botões, modais e outputs
│   ├── js/
│   │   ├── app.js               # Ponto de entrada, roteador e auth
│   │   ├── catalog.js           # Gerenciador do catálogo de binds dinâmicos
│   │   ├── terminal.js          # Renderizador de saída e streaming
│   │   ├── harpia_chat.js       # Cliente WebSocket/SSE do agente de IA
│   │   └── mcp_bridge.js        # Cliente HTTP JSON-RPC 2.0 do MCP
│   └── media/                   # Banners, logos e wallpapers
└── components/
    ├── sidebar.html             # Categorias e menu de navegação
    ├── tool_view.html           # Template dinâmico de execução de bind
    └── harpia_panel.html        # Painel do agente de IA e ferramentas
```

---

## 4. Contratos de API da Nova Interface

O novo frontend consumirá exclusivamente estes endpoints padronizados:

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/login` | Autenticação com sessão HMAC e cookie `nt_session`. |
| `GET` | `/api/tools` | Retorna o índice completo de binds e argumentos de `rocketdb_v2.json`. |
| `POST` | `/api/exec` | Executa um bind e retorna status code, stdout (HTML ou texto) e stderr. |
| `POST` | `/api/mcp` | Comunicação direta JSON-RPC 2.0 com o servidor MCP. |
| `POST` | `/api/harpia/chat` | Envio de mensagens para o agente Harpia com histórico e execução de tools. |
| `GET` | `/api/system/stats` | Telemetria do host (CPU, memória, rede, discos). |

---

## 5. Fases de Execução da Refatoração

### Fase 1: Desacoplamento da API (Concluída)
- [x] Endpoints `/api/mcp`, `/api/harpia/chat`, `/api/exec` e `/api/system/stats` estabilizados em `pkg/server/server.py`.
- [x] Remoção de emojis e sequências quebradas no transporte de tools.
- [x] Suporte nativo a `--output_mode_html` no motor.

### Fase 2: Construção da SPA Dinâmica (Próximo Passo)
- [ ] Implementar carregamento dinâmico dos formulários de comando a partir de `/api/tools`.
- [ ] Eliminar as mais de 2.000 tags de seções repetidas de `spellbook/webui/index.html`.
- [ ] Integrar terminal interativo com suporte a rolagem contínua e exportação de logs.

### Fase 3: Persistência & Extensibilidade
- [ ] Adicionar persistência de histórico de chat e sessões no `localStorage` do navegador.
- [ ] Suporte a abas de ferramentas simultâneas no estilo split-view para operações de cyberdeck.
