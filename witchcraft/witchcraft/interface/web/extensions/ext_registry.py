from witchcraft.interface.web.extensions.home import home
from witchcraft.interface.web.extensions.handbook import handbook
from witchcraft.interface.web.extensions.haki import haki
from witchcraft.interface.web.extensions.llama_ui import llama_ui
from witchcraft.interface.web.extensions.settings import settings


mods_reg = [
    home,
    handbook,
    haki,
    llama_ui,
    settings,
]

def mods():
    buttons = []
    sections = []
    for mod in mods_reg:
        buttons.append(mod.get("button"))
        sections.append(mod.get("section"))
    
    return {
        "buttons": buttons,
        "sections": sections
    }