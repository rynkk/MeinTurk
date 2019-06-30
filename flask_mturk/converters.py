from werkzeug.routing import BaseConverter, ValidationError


class IDConverter(BaseConverter):
    regex = "[A-Z0-9]+"
