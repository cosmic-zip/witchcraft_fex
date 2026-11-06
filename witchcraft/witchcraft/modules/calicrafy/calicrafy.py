from witchcraft.metalcore.core import *
import re

def load_font():
    font_file = f"{NT_DATAROOT}misc/calicrafy.json"
    with open(font_file, "r") as file:
        font = json.load(file)
        file.close()
        return font.get("index")

def to_ascii_font(string, font="crafy_lower", max_width=210):
    if not string:
        return ""

    fonts = load_font()
    if not fonts:
        return ""
    fonts = fonts.get(font, {})
    if not fonts:
        return ""

    rendered = ""
    parts = re.split(r"(@@.*?@@)", string)

    blocks = []
    for p in parts:
        if not p:
            continue
        if p.startswith("@@") and p.endswith("@@") and len(p) >= 4:
            content = p[2:-2].strip()
            if content:
                blocks.append((content, True))
        else:
            content = p.strip()
            if content:
                blocks.append((content, False))

    for text_part, is_bullet in blocks:
        clean = re.sub(r"[^a-zA-Z0-9 •]+", "", text_part).strip()
        if not clean:
            continue

        if is_bullet:
            clean = "• " + clean

        interactions = []
        current_line = ""
        current_px = 0

        for char in clean:
            glyph = fonts.get(char)
            char_w = (len(glyph[0]) + 1) if glyph else 1

            if current_px + char_w > max_width and current_line:
                interactions.append(current_line)
                current_line = char
                current_px = char_w
            else:
                current_line += char
                current_px += char_w

        if current_line:
            interactions.append(current_line)

        for nw in interactions:
            output = []
            for lt in nw: 
                fl = fonts.get(lt)
                if fl:
                    output.append(fl)

            if not output:
                continue

            height = len(output[0])
            for step in range(height):
                for lts in output:
                    rendered = rendered + lts[step] + " "
                rendered = rendered + "\n"
            rendered = rendered + "\n"

    return rendered.rstrip("\n")


def presentation(title, subtitle, body, footer, theme="default"):

    theme_list = {
        "default": {
            "w": "white",
            "t": "white",
            "s": "white",
            "b": "white",
            "f": "white",
        },
        "punk": {
            "w": "bright_green",
            "t": "bright_green",
            "s": "yellow",
            "b": "magenta",
            "f": "red",
        },
        "cyber": {
            "w": "bright_cyan",
            "t": "cyan",
            "s": "bright_magenta",
            "b": "bright_blue",
            "f": "magenta",
        },
        "matrix": {
            "w": "bright_green",
            "t": "green",
            "s": "bright_green",
            "b": "green",
            "f": "bright_black",
        },
        "bloodmoon": {
            "w": "bright_red",
            "t": "red",
            "s": "bright_yellow",
            "b": "bright_red",
            "f": "red",
        },
        "gold": {
            "w": "bright_yellow",
            "t": "yellow",
            "s": "bright_white",
            "b": "bright_yellow",
            "f": "yellow",
        },
        "cosmic": {
            "w": "bright_magenta",
            "t": "magenta",
            "s": "bright_cyan",
            "b": "bright_white",
            "f": "cyan",
        },
        "stealth": {
            "w": "bright_black",
            "t": "white",
            "s": "bright_black",
            "b": "white",
            "f": "bright_black",
        },
    }


    if isinstance(theme, str):
        theme = theme_list.get(theme) or theme_list.get("default")
    elif not theme:
        theme = theme_list.get("default")


    title = to_ascii_font(title, font="crafy_upper", max_width=210)
    body = to_ascii_font(body, font="crafy_lower", max_width=210)

    eyeliner("WITCHCRAFT PRESENTATION", theme.get("w"), length=210)
    net_logger(title, theme.get("t") , "bold", True)
    net_logger(subtitle, theme.get("s") , "bold", True)
    net_logger(body, theme.get("b") , "normal", True)
    net_logger(footer, theme.get("f") , "italic", True)

def presentation_wrapper(args_v):
    title = search_arg(args_v, "title", False)
    subtitle = search_arg(args_v, "subtitle", False)
    body = search_arg(args_v, "body", False)
    footer = search_arg(args_v, "footer", False)
    theme = search_arg(args_v, "theme", False) or "default"
    presentation(title, subtitle, body, footer, theme=theme)
    return 0

def press_creator(args_v):
    file_name = search_arg(args_v, "file_name", False) or "presentation.txt"
    theme_name = search_arg(args_v, "theme", False) or "default"
    save = False

    eyeliner("WITCHCRAFT PRESENTATION CREATOR", "cyan", length=210)

    while not save:
        title = input("title: ")
        subtitle = input("subtitle: ")
        body = input("body: ")
        footer = input("footer: ")

        presentation(title, subtitle, body, footer, theme=theme_name)

        ans = input("save [y/n]? ").strip().lower()
        if ans == "y":
            save = True
            with open(file_name, "a") as file:
                s = f'./main.py presentation --title "{title}" --subtitle "{subtitle}" --body "{body}" --footer "{footer}" --theme {theme_name}\n'
                file.write(s)
            net_logger(f"Saved slide to {file_name}", "green", "bold", True)

def press_reader(args_v):
    file_name = search_arg(args_v, "file_name", False) or "presentation.txt"
    if not os.path.isfile(file_name):
        net_logger(f"File '{file_name}' not found.", "red", "bold", True)
        return 1

    with open(file_name, "r") as file:
        slides = [line.strip() for line in file if line.strip()]

    for i, slide_cmd in enumerate(slides):
        print("\033c", end="")
        output = net_exec(slide_cmd)
        if output.get("stdout"):
            print(output["stdout"])
        if i < len(slides) - 1:
            input("\n[Press Enter for next slide...]")

    return 0