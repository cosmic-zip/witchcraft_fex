#!/usr/bin/python3
#░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░#
#                                                                                                                              #
#       Welcome to the WitchcraftFEX project! Originally written in Lua, the main parts of the codebase have been              #
#       rewritten in Python to make it easier to find new contributors and employees for the Cosmic Sec&Dev company.           #
#                                                                                                                              #
#░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░#

from witchcraft.metalcore.core import net_shell_router
from witchcraft.settings import *
# net_shell_router(FN_REGISTRY, "spellbook/pkg/common/hello.sh")
net_shell_router(FN_REGISTRY)
