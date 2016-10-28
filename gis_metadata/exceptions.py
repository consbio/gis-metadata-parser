""" A module to define metadata parsing exceptions """


class ParserError(Exception):
    """ A class to represent all parsing exceptions """

    def __init__(self, msg_format, **kwargs):
        """
        Call Exception with a message formatted with named arguments from
        a Dictionary with values by key, or a list of named parameters.
        """

        super(ParserError, self).__init__(msg_format.format(**kwargs))


class ConfigurationError(ParserError):
    """
    A class to represent problems with a parser's configuration
    :raised: during parsing operation when a parser is misconfigured
    """


class InvalidContent(ParserError):
    """
    A class to represent problems with XML parsing of metadata content
    :raised: while reading raw data into the XML tree before parsing
    """


class NoContent(ParserError):
    """
    A class to represent issues with empty metadata content
    :raised: while reading raw data into the XML tree before parsing
    """


class ValidationError(ParserError):
    """
    A class to represent validation exceptions:
    :raised: after updates when validating, updating the tree, or serializing
    """

    def __init__(self, msg_format, invalid=None, missing=None, **kwargs):
        """ Capture missing or invalid fields and values """

        # Track details about the error for handling downstream
        self.invalid = {} if invalid is None else invalid
        self.missing = [] if missing is None else missing

        super(ValidationError, self).__init__(msg_format, **kwargs)
