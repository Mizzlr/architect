import colorama


def stringify(obj):
    if not isinstance(obj, str):
        obj = str(obj)
    return obj


def red(obj):
    return colorama.Fore.RED + stringify(obj) + "\033[39m"


def cyan(obj):
    return colorama.Fore.CYAN + stringify(obj) + "\033[39m"


def green(obj):
    return colorama.Fore.GREEN + stringify(obj) + "\033[39m"


def yellow(obj):
    return colorama.Fore.YELLOW + stringify(obj) + "\033[39m"


def magenta(obj):
    return colorama.Fore.MAGENTA + stringify(obj) + "\033[39m"


def white(obj):
    return colorama.Fore.WHITE + stringify(obj) + "\033[39m"


def pink(obj):
    return magenta(obj)
