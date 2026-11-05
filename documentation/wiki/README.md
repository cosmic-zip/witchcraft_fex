# ⛩️ WitchcraftFEX — Wiki & Documentação Oficial
> *Unified Purple Team Framework & Autonomous Security Engine*  
> **Autor & Engenharia:** COSMIC ZIP  
> **Filosofia:** Cypherpunk / Netrunner Culture / Zero External Dependencies

---

## ⚡ Visão Geral do Framework

O **WitchcraftFEX** é uma plataforma modular de operações cibernéticas, automação de testes de intrusão e resposta a incidentes. Construído sob a ótica dos princípios **Cypherpunk** e na cultura **Netrunner**, o projeto consolida mais de 200 ferramentas de segurança em um catálogo declarativo único (`rocketdb_v2.json`), acionável via CLI de alta performance e interface Web SPA reativa em HTMX.

---

## 📚 Seções da Wiki

- **[Arquitetura Técnica de Código & Guia de Operações Diárias](witchcraft_architecture_and_operations.md)**: Documentação avançada da arquitetura interna (`metalcore`, `rocketdb_v2.json`, subsistema Harpia `ai`/`cli`/`mcp`/`web`, interpretador estático Rust `xcript`) e playbooks práticos de uso no dia a dia.
- **[Apresentação & Grimório Cypherpunk](cypherpunk_presentation.md)**: Apresentação completa com os 8 módulos temáticos, arquitetura, Purple Team loop, modelo de autodefesa em 5 camadas e cheat-sheets operacionais.
- **[Engenharia de Linux Embarcado com Buildroot](embedded_linux_buildroot_mastery.md)**: Guia completo de arquitetura, compilação eficiente, ccache, dissecação de menus, runtimes (Python/Rust), linkers, inclusão de binários externos e todos os filesystems.
- **[Repositório & Código Fonte](https://cosmic-zip.github.io/)**: Wiki externa e guia canônico do Netrunner.

---

## 🚀 Arquitetura & Componentes

```
+-------------------------------------------------------------------------+
|                            WITCHCRAFTFEX                                |
+-------------------------------------------------------------------------+
|  [CLI Router]     Padronização SCLF (--target, --port, --interface)     |
|  [Single SSoT]    rocketdb_v2.json com 208+ rotinas e cmd_backend       |
|  [Web Engine]     SPA Reativa gerada proceduralmente com HTMX           |
|  [Spellbook]      Grimório de binários nativos, wordlists e modelos     |
|  [Harpia Engine]  Agente IA + MCP Server + CLI + Web Chat (llama.cpp)   |
|  [Xcript Engine]  Linguagem de script flat em Rust (binário estático)   |
|  [Wiki Engine]    Servidor Nginx Alpine ultraleve com Docsify           |
+-------------------------------------------------------------------------+
```
