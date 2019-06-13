import inspect
import abc
from textwrap import dedent


class Source:

    def __init__(self):
        pass

    @abc.abstractmethod
    def source_code(self):
        pass

    def __eq__(self, other):
        if not isinstance(other, Source):
            return False
        return self.source_code() == other.source_code()

    def __hash__(self):
        return hash(self.source_code())

    def __str__(self):
        return self.source_code()


class JsFunction(Source):

    def __init__(self, func):
        super().__init__()
        self.func = func
        self.name = func.__name__
        self._source_code = None

    def source_code(self):
        if self._source_code is None:
            self._source_code = dedent(inspect.getsource(self.func))
        return self._source_code


class JsFlat(Source):

    def __init__(self, func):
        super().__init__()
        if len(inspect.signature(func).parameters) > 0:
            raise ValueError("Flat JS functions can't have arguments")
        self.func = func
        self._source_code = None

    def source_code(self):
        if self._source_code is None:
            func_source = inspect.getsource(self.func)
            func_source = dedent(func_source)
            source_lines = func_source.split("\n")
            source_lines = filter(lambda line: line.startswith(" ") or line.startswith("\t"), source_lines)
            func_source = "\n".join(source_lines)
            func_source = dedent(func_source)
            self._source_code = func_source

        return self._source_code


class JsRaw(Source):

    def __init__(self, js_source):
        super().__init__()
        self.js_source = js_source
        self._source_code = None

    def source_code(self):
        if self._source_code is None:
            escaped_js_source = self.js_source.translate(str.maketrans({
                "\\": "\\\\",
                "'": "\\'"
            }))
            self._source_code = "__pragma__('js', '{}', '" + escaped_js_source + "')"
        return self._source_code
