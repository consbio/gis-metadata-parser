""" A module to define custom exceptions """


class ParserError(Exception):
    """ A class to encapsulate all parsing exceptions """

    def __init__(self, msg_format, *args, **kwargs):
        """
        Call Exception with a message formatted with named arguments from
        a Dictionary with values by key, or a list of named parameters.
        """
        Exception.__init__(self, msg_format.format(*args, **kwargs))


