import json
from urllib.parse import unquote
import uuid
import inspect
from IPython.display import display, Javascript

from .injectors import AnonymousJsContextInjector, PrecompiledJsContextInjector
from .compiler import compile_context_generator
from .shared import __unique_py_function_name__, __unique_context_variable_name__, __unique_handle_name__
from .source import JsFunction, JsFlat, JsRaw


def _decode_param(param):
    return json.loads(unquote(param))


def _random_id():
    return str(uuid.uuid4()).replace("-", "_")


class PrecompiledJsContext:
    """
    Contains compiled code of some `JsContext`.
    Using precompiled context is more efficient, than compiling it every time.
    Not only because it eliminates compilation stage, but shares same JavaScript code between contexts.
    """

    def __init__(self, context_generator_script):
        self.context_generator_script = context_generator_script
        self.id = _random_id()
        self.context_generator_var_name = "__js_precompiled_context_generator_{}".format(self.id)
        self.injected = False

    def save(self, path):
        """
        Saves precompiled context to file
        :param path: path to file
        """
        with open(path, "w") as f:
            f.write(self.context_generator_script)

    def inject(self):
        if self.injected:
            raise ValueError("Precompiled context {} was already injected".format(self.id))
        display(Javascript("window.{} = {};".format(self.context_generator_var_name, self.context_generator_script)))
        self.injected = True

    @classmethod
    def load(cls, path):
        """
        Loads precompiled context from file
        :param path: path to saved context
        """
        with open(path, "r") as f:
            context_generator_script = f.read()

        return cls(context_generator_script)

    def __del__(self):
        if self.injected:
            display(Javascript("window.{} = undefined;".format(self.context_generator_var_name)))


class JsContext:
    """
    `JsContext` creates JavaScript context and provides Python <-> JavaScript interaction
    """

    def __init__(self, data=None, precompiled_context=None):
        """
        Creates `JsContext`
        :param data: data to pass to context in JavaScript. Would be available as __data variable.
         By default it would be null
        :param precompiled_context: precompiled context obtained from same `JsContext`
        """
        self._sources = []
        self._py_functions = []
        self.id = _random_id()
        self.data = data
        self.precompiled_context = precompiled_context

        self._executed_js_at_least_once = False
        self._js_display_id = self.id + "_js"

        self._main_frame = None
        for frame in inspect.stack():
            frame_globals = frame[0].f_globals
            if frame_globals.get("__name__") == "__main__":
                self._main_frame = frame[0]
                break

        if self._main_frame is None:
            raise ValueError("Can't find __main__ frame in stack")

    def py(self, f):
        """
        Decorator for python functions invokable from js functions
        Returns its argument without modifications
        """

        def wrapper(*args, **kwargs):
            args = map(_decode_param, args)
            kwargs = {key: _decode_param(value) for key, value in kwargs.items()}
            return json.dumps(f(*args, **kwargs))

        unique_f_name = __unique_py_function_name__(f.__name__, self.id)
        self._main_frame.f_globals[unique_f_name] = wrapper
        self._py_functions.append(unique_f_name)

        return f

    def js_by_name(self, name):
        """
        Creates wrapper for JavaScript function by its name inside `exports` variable
        Usually used together with `js_raw` function
        :param name: name of the function
        :return: function that calls JavaScript function with name equals to `name`
        """

        def func(*args):
            args = map(json.dumps, args)
            args = ",".join(args)

            script = __unique_context_variable_name__(self.id) + "." + name + "({})".format(args) + ";"
            self._execute_js(script)

        return func

    def js(self, f):
        """
        Decorator for JavaScript functions.
        All js functions will be translated to JavaScript, and are accessible for each other inside one context
        Calling resulting function in python will execute correspondent function in JavaScript
        Doesn't return JavaScript function result back to Python (you can implement it yourself using `pycall`)
        """
        self._sources.append(JsFunction(f))
        return self.js_by_name(f.__name__)

    def js_flat(self, f):
        """
        Decorator for JavaScript code
        Body of target which bodies will be injected into context
        """
        self._sources.append(JsFlat(f))

        def wrapper():
            raise RuntimeError("Flat JS functions can't be called")

        return wrapper

    def js_raw(self, code):
        """
        Inserts raw JavaScript code into context
        Note that `pycall` is not available in raw code
        :param code: code to insert into context
        """
        self._sources.append(JsRaw(code))

    def _get_context_generator_script(self, minify):
        return compile_context_generator(tuple(self._sources), minify)

    def compile(self, minify=True):
        """
        Creates precompiled context from current one
        :param minify: if to minify code (for debug purposes)
        :return: precompiled context
        """
        return PrecompiledJsContext(self._get_context_generator_script(minify=minify))

    def html(self):
        """
        Returns HTML code that should be inserted in order to activate context
        No guarantees are given about case when same HTML code executed twice or more times
        :return: HTML code
        """
        if self.precompiled_context is None:
            injector = AnonymousJsContextInjector(self._get_context_generator_script(minify=True))
        else:
            if not self.precompiled_context.injected:
                self.precompiled_context.inject()
            injector = PrecompiledJsContextInjector(self.precompiled_context)

        context_param = {"id": self.id, "data": self.data}
        return "\n".join((
            '<div id="{}" style="display: none;"></div>'.format(__unique_handle_name__(self.id)),
            '<script>{}</script>'.format(injector.get_inject_script(context_param, self._py_functions)),
        ))

    def _repr_html_(self):
        return self.html()

    def _execute_js(self, code):
        display(Javascript(code), update=self._executed_js_at_least_once, display_id=self.id + "_js")
        self._executed_js_at_least_once = True
