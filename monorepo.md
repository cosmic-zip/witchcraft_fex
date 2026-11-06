# Witchcraft Monorepo

Este repositório unifica os projetos do ecossistema **Witchcraft**, reunindo ferramentas de segurança ofensiva/defensiva (OPSEC), linguagem de script, sistema operacional customizado (baseado em Buildroot), manifestos conceituais e documentação técnica.

Abaixo está a descrição e a responsabilidade de cada diretório presente na raiz do monorepo:

---

## Estrutura de Diretórios

### 📁 `.github/`
Configurações de CI/CD e automação do GitHub:
- Contém os fluxos de trabalho (workflows) do GitHub Actions (como [`witchcraft.yml`](file:///home/cosmic/workspace/witchcraft-mono/.github/workflows/witchcraft.yml)), responsáveis pela instalação de dependências, compilação de binários e execução automática de testes.

---

### 📁 `docs/`
Central de documentação geral e visualização do projeto:
- **`wiki/`**: Wiki navegável (construída com Docsify) com artigos técnicos, guias operacionais e apresentações conceituais.
- **`index.html`**: Página web de apresentação e documentação estática do framework.
- **`changelog.md`**: Histórico detalhado de versões, correções e novos recursos adicionados.
- **`graph.mmd`**: Diagramas arquiteturais em Mermaid ilustrando o fluxo dos módulos, componentes e engine.
- **`images/`**: Banners, capturas de tela e assets visuais utilizados nas páginas e documentações.

---

### 📁 `manifest/`
Documentos conceituais e filosóficos:
- Espaço dedicado a reflexões, manifestos e referências não técnicas relacionadas à cultura e filosofia **cypherpunk**, privacidade, soberania digital e ética operacional.

---

### 📁 `witchcraft/` (WitchcraftFEX)
O núcleo da suite de ferramentas de segurança cibernética ofensiva e defensiva:
- **`main.py`**: Ponto de entrada (CLI) para execução de subcomandos, módulos e inicialização de rotinas.
- **`witchcraft/`**: Pacote principal em Python contendo:
  - `metalcore/`: Mecanismos de roteamento de comandos (`core.py`), carregamento dinâmico e execução de binds.
  - `modules/`: Módulos operacionais (scanners DNS/Nmap/IP, OSINT, gerador de relatórios, monitor de hardware, servidores web/AI).
  - `interface/`: Gerador e templates da interface web (WebUI) e extensões.
  - `tests/`: Bateria de testes unitários da ferramenta.
- **`spellbook/`**: Grimório de utilitários, bibliotecas auxiliares, bancos de dados de assinaturas/comandos (`rocketdb_v2.json`), páginas de manual e recursos de suporte.
- **Arquivos de deploy/empacotamento**: Configurações para Docker (`dockerfile`, `docker-compose.yml`) e Snapcraft (`snapcraft.yaml`).

---

### 📁 `xcript/` (Witchcraft-Xcript)
Linguagem de script independente desenvolvida em Rust:
- Projetada originalmente para automação de configurações e rotinas do framework, evoluiu para uma linguagem autônoma com tipagem e suporte à estrutura de dados `omega type` (equivalente flexível a `any`/`hashmap`), além de variáveis e blocos condicionais.

---

### 📁 `bloodmoon-os/`
Sistema operacional customizado minimalista voltado para operações e segurança:
- **`configs/`**: Arquivos de configuração de compilação do kernel e do sistema (ex.: `nt_defconfig` para Buildroot).
- **`desktop/`**: Configurações de ambiente gráfico, scripts de inicialização de interface e perfil de usuário.
- **`setup.sh`**: Script para clonar e preparar o ambiente de compilação utilizando Buildroot.
