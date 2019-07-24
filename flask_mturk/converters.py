from werkzeug.routing import BaseConverter


class IDConverter(BaseConverter):
    regex = "[A-Z0-9]+"
