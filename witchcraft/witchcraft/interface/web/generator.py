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
        seed = str(random.randint(101010, 991199))

        bottom = sidebar_button.replace("@@IDSECTION", seed)
        bottom = bottom.replace("@@BTNAME", item.get("name"))
        
        if category not in category_map:
            category_map[category] = []
        category_map[category].append(bottom)

        new_sec = section.replace("@@IDSECTION", seed)
        new_sec = new_sec.replace("@@IDOUTPUTHTX", "#ID" + seed)
        new_sec = new_sec.replace("@@IDOUTPUT", "ID" + seed)
        new_sec = new_sec.replace("@@REQUESTID", seed)
        new_sec = new_sec.replace("@@TITLE", item.get("name"))
        new_sec = new_sec.replace("@@HINT", item.get("description", ""))
        new_sec = new_sec.replace("@@MNAMEZ", item.get("name"))
        new_sec = new_sec.replace("@@MNAME", item.get("name"))

        # idk
        type = item.get("type")
        extends = item.get("extends")

        arguments = item.get("arguments")
        args_buffer = []
        id_list = []
        if arguments:
            args = item["arguments"]
            for arg in args:

                arg_obj = args.get(arg)
                if arg_obj and arg_obj.get("options"):
                    arg_options = arg_obj.get("options")

                    buffer = []
                    for opt in arg_options:
                        buffer.append(
                            section_form_select_options.replace("@@FOPTION_NAME", opt)
                        )

                    new_select = section_form_select.replace("@@IDFNAME", arg)
                    id_list.append(arg)
                    new_select = section_form_select.replace(
                        "@@FOPTIONS", "\n".join(buffer)
                    )
                    args_buffer.append(new_select)

                else:
                    new_text = section_form_text.replace("@@FTITLE", arg)
                    id_list.append(arg)
                    new_text = new_text.replace("@@IDFTITLE", arg)
                    args_buffer.append(new_text)

        ids = ""
        for x in id_list:
            ids = ids + "#" + x + ", "
        new_sec = new_sec.replace("@@IDFNAME_LIST", ids)
        new_sec = new_sec.replace("@@FORM_CONTENT", "\n".join(args_buffer))
        new_sec = new_sec.replace("@@NT_GEN_HOST", NT_GEN_HOST)
        overall_sections.append(new_sec)

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
    base = base.replace("@@SIDEBAR", sbar)
    base = base.replace("@@CONTAINER", "\n".join(overall_sections))
    return base


def gen_extends():
    base = gen_base()
    # ADD extensions
    ext = mods()

    buttons = "\n".join(ext.get("buttons"))
    sections = "\n".join(ext.get("sections"))

    base = base.replace("@@EXTENSIONS", buttons)
    base = base.replace("@@EXTENDS", sections)
    base = base.replace("@@ERROR", "neko hackers inside >_<")
    return base


def gen_wrapper(args_v=None):
    print(gen_extends())
    return 0
