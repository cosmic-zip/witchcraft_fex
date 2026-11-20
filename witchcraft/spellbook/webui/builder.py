"""
WitchcraftFEX WebUI Static Component & Index Generator.
Builds pure static HTML component files and index.html inside spellbook/webui/.
"""
import os
import json
import re

WEBUI_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENTS_DIR = os.path.join(WEBUI_DIR, "components", "tools")


def get_rocketdb_path():
    candidates = [
        os.path.join(WEBUI_DIR, "..", "database", "rocketdb_v2.json"),
        os.path.join(os.environ.get("NT_DATAROOT", ""), "database", "rocketdb_v2.json"),
        "witchcraft/spellbook/database/rocketdb_v2.json",
        "spellbook/database/rocketdb_v2.json",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.abspath(c)
    return None


def generate_tool_component(bind: dict) -> str:
    name = bind.get("name", "")
    desc = bind.get("description", "")
    args = bind.get("arguments") or {}

    args_inputs = []
    for arg_name, arg_info in args.items():
        input_id = f"arg_{arg_name}"
        arg_desc = arg_info.get("description", arg_name)
        options = arg_info.get("options")

        if options:
            opts_html = "\n".join(f'            <option value="{opt}">{opt}</option>' for opt in options)
            args_inputs.append(f"""        <div class="form-group">
            <label for="{input_id}" class="form-label">{arg_name.upper()}</label>
            <select name="{arg_name}" id="{input_id}" class="form-control">
{opts_html}
            </select>
            <small class="form-hint">{arg_desc}</small>
        </div>""")
        else:
            args_inputs.append(f"""        <div class="form-group">
            <label for="{input_id}" class="form-label">{arg_name.upper()}</label>
            <input type="text" class="form-control" name="{arg_name}" id="{input_id}" placeholder="{arg_desc}">
            <small class="form-hint">{arg_desc}</small>
        </div>""")

    fields_html = "\n".join(args_inputs) if args_inputs else '        <div class="form-info-note">Nenhum parâmetro adicional obrigatório.</div>'

    return f"""<section class="content-sec content-sec-visible">
    <header class="sec-header">
        <div>
            <span class="tool-title-name"><em>{name}</em></span>
            <span class="tool-title-desc">{desc}</span>
        </div>
    </header>

    <div class="tool-workspace-split">
        <div class="tool-terminal-pane">
            <div class="terminal-toolbar">
                <span class="term-title">💻 Terminal / Output</span>
                <div class="term-actions">
                    <button type="button" onclick="downloadDivAsTxt('tool_output_box', 'output_{name}.txt')" class="btn btn-secondary btn-sm">Salvar Log</button>
                    <button type="button" onclick="document.getElementById('tool_output_box').textContent = ''" class="btn btn-secondary btn-sm">Limpar Tela</button>
                </div>
            </div>
            <div class="outputer">
                <pre id="tool_output_box"></pre>
            </div>
        </div>

        <div class="tool-form-pane">
            <form class="tool-form" method="post"
                hx-post="/api/exec"
                hx-include="#ztoken"
                hx-target="#tool_output_box"
                hx-indicator="#exec-spinner">
                <input type="hidden" name="EZEC_{name}" value="{name}">
                
                <div class="form-fields">
{fields_html}
                </div>

                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">
                        ▶ Executar
                    </button>
                    <button type="reset" class="btn btn-secondary">
                        Limpar
                    </button>
                    <span id="exec-spinner" class="htmx-indicator tool-exec-spinner">⚡ Executando...</span>
                </div>
            </form>
        </div>
    </div>
</section>
"""


def build_all_components():
    db_path = get_rocketdb_path()
    if not db_path:
        raise FileNotFoundError("rocketdb_v2.json not found")

    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tools = data.get("index", [])
    os.makedirs(COMPONENTS_DIR, exist_ok=True)

    for bind in tools:
        name = bind.get("name")
        if not name:
            continue
        html = generate_tool_component(bind)
        file_path = os.path.join(COMPONENTS_DIR, f"{name}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)

    return len(tools)


def gen_wrapper(args_v=None):
    count = build_all_components()
    print(f"Generated {count} tool components in {COMPONENTS_DIR}")
    return 0


if __name__ == "__main__":
    gen_wrapper()
