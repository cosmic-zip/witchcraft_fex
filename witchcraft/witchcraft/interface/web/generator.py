from witchcraft.interface.web.templates.base import *
from witchcraft.metalcore.core import *
from witchcraft.interface.web.extensions.ext_registry import mods
import random


def gen_base(args_v=None):
    base = base_html
    base = base.replace("@@PAGETITLE", NT_GEN_TITLE)
    database = read_db()

    overall_sections = []
    category_map = {}
    for item in database:
        category = item.get("category") or "system"
        tool_name = item.get("name")

        button = sidebar_button.replace("@@BTNAME", tool_name)
        
        if category not in category_map:
            category_map[category] = []
        category_map[category].append(button)

    category_blocks = []
    ordered_cats = [
        "network", "web", "security", "forensics", "system",
        "core", "containers", "firewall", "database", "antivirus", "cleanup"
    ]
    all_cats = list(category_map.keys())
    sorted_cats = sorted(all_cats, key=lambda c: (ordered_cats.index(c) if c in ordered_cats else 999, c))

    for cat_name in sorted_cats:
        cat_buttons = "\n".join(category_map[cat_name])
        cat_id = cat_name.replace(".", "_").replace("-", "_")
        block = sidebar_category_group.replace("@@CATID", cat_id)
        block = block.replace("@@CATNAME", cat_name.upper())
        block = block.replace("@@CATBUTTONS", cat_buttons)
        category_blocks.append(block)

    categories_html = "\n".join(category_blocks)
    sbar = sidebar_groups.replace("@@SYSTEM", categories_html)
    sbar = sbar.replace("@@CATEGORIES", categories_html)
    base = base.replace("@@ZTOKEN", NT_COSMIC_SIGKEY)
    base = base.replace("@@NT_GEN_HOST", NT_GEN_HOST)
    base = base.replace("@@SIDEBAR", sbar)
    base = base.replace("@@CONTAINER", "")
    return base


def gen_extends():
    base = gen_base()
    # ADD extensions
    ext = mods()

    buttons = "\n".join(ext.get("buttons"))
    sections = "\n".join(ext.get("sections"))

    base = base.replace("@@EXTENSIONS", buttons)
    base = base.replace("@@EXTENDS", sections)
    base = base.replace("@@NT_GEN_HOST", NT_GEN_HOST)
    base = base.replace("@@ERROR", "neko hackers inside >_<")
    return base


def gen_wrapper(args_v=None):
    print(gen_extends())
    return 0
