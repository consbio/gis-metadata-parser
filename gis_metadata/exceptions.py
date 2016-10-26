""" A module to define metadata parsing exceptions """


class ParserError(Exception):
    """ A class to encapsulate all parsing exceptions """

    def __init__(self, msg_format, invalid=None, missing=None, **kwargs):
        """
        Call Exception with a message formatted with named arguments from
        a Dictionary with values by key, or a list of named parameters.
        """

        super(ParserError, self).__init__(msg_format.format(**kwargs))

        # Track details about the error for handling downstream
        self.invalid = {} if invalid is None else invalid
        self.missing = [] if missing is None else missing
