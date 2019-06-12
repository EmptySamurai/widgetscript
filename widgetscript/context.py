import json
import base64
import json
import uuid
import inspect
from IPython.display import display, Javascript

from .injectors import AnonymousJsContextInjector, PrecompiledJsContextInjector
from .compiler import compile_context_generator
from .shared import __unique_py_function_name__, __unique_context_variable_name__, __unique_handle_name__


def _decode_param(param):
    return json.loads(base64.b64decode(param).decode())


def _encode_param(param):
    return base64.b64encode(json.dumps(param).encode()).decode()


def _encode_result(result):
    return json.dumps(result)


def random_id():
    return str(uuid.uuid4()).replace("-", "_")


class PrecompiledWidgetContext:

    def __init__(self, context_generator_script):
        self.context_generator_script = context_generator_script
        self.precompiled_context_id = random_id()
        self.context_generator_var_name = "__js_precompiled_context_generator_{}".format(self.precompiled_context_id)
        self.injected = False

    def save(self, path):
        with open(path, "w") as f:
            f.write(self.context_generator_script)

    def inject(self):
        if self.injected:
            raise ValueError("Precompiled context {} was already injected".format(self.precompiled_context_id))
        display(Javascript("window.{} = {};".format(self.context_generator_var_name, self.context_generator_script)))
        self.injected = True

    @classmethod
    def load(cls, path):
        with open(path, "r") as f:
            context_generator_script = f.read()

        return cls(context_generator_script)

    def __del__(self):
        if self.injected:
            display(Javascript("window.{} = undefined;".format(self.context_generator_var_name)))


class WidgetContext:

    def __init__(self, data=None, precompiled_context=None):
        self._js_functions = []
        self._py_functions = []
        self._js_inits = []
        self.context_id = random_id()
        self.data = data
        self.precompiled_context = precompiled_context

        self._executed_js_at_least_once = False
        self._js_display_id = self.context_id + "_js"

        self._main_frame = None
        for frame in inspect.stack():
            frame_globals = frame[0].f_globals
            if frame_globals.get("__name__") == "__main__":
                self._main_frame = frame[0]
                break

        if self._main_frame is None:
            raise ValueError("Can't find __main__ frame in stack")

    def py(self, f):
        def wrapper(*args, **kwargs):
            args = map(_decode_param, args)
            kwargs = {key: _decode_param(value) for key, value in kwargs.items()}
            return _encode_result(f(*args, **kwargs))

        unique_f_name = __unique_py_function_name__(f.__name__, self.context_id)
        self._main_frame.f_globals[unique_f_name] = wrapper
        self._py_functions.append(unique_f_name)

        return f

    def js_init(self, f):
        if len(inspect.signature(f).parameters) > 0:
            raise ValueError("js_init function shouldn't have arguments")
        self._js_inits.append(f)
        return self.js(f)

    def js(self, f):
        def wrapper(*args):
            args = list(map(_encode_param, args))
            if len(args) > 0:
                args = "'" + "' , '".join(args) + "'"
            else:
                args = ""

            script = __unique_context_variable_name__(self.context_id) + "." + f.__name__ + "({})".format(args) + ";"
            self._execute_js(script)

        self._js_functions.append(f)
        return wrapper

    def _get_context_generator_script(self, minify):
        return compile_context_generator(self._js_functions, self._js_inits, minify)

    def compile(self, minify=True):
        return PrecompiledWidgetContext(self._get_context_generator_script(minify=minify))

    def html(self):
        if self.precompiled_context is None:
            injector = AnonymousJsContextInjector(self._get_context_generator_script(minify=True))
        else:
            if not self.precompiled_context.injected:
                self.precompiled_context.inject()
            injector = PrecompiledJsContextInjector(self.precompiled_context)

        return "\n".join((
            '<div id="{}" style="display: none;"></div>'.format(__unique_handle_name__(self.context_id)),
            '<script>{}</script>'.format(injector.get_inject_script(self.context_id, self.data, self._py_functions)),
        ))

    def _repr_html_(self):
        return self.html()

    def _execute_js(self, code):
        display(Javascript(code), update=self._executed_js_at_least_once, display_id=self.context_id + "_js")
        self._executed_js_at_least_once = True
