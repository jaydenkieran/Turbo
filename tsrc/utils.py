import discord


def get_destination_string(msg):
    """Returns the destination string from a discord.Message object"""
    if not isinstance(msg, discord.Message):
        raise TypeError("This function only accepts discord.Message objects")
    d = None
    if msg.channel.is_private:
        d = 'Private Message'
    else:
        d = '#{0.channel.name} ({0.server.name})'.format(msg)
    return d


def format_bool(boolean):
    """Returns a string based on bool value"""
    return ['no', 'yes'][boolean]


def format_option(txt1, txt2):
    """Returns a formatted string with ANSI for printing configurated options"""
    txt1 = "\033[36m{}".format(txt1)  # cyan
    txt2 = "\033[39m{}".format(txt2)  # default
    r = "{}{}".format(txt1, txt2)
    return r
