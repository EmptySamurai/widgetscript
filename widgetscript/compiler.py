import subprocess
import ast
import astor
import tempfile
import shutil
import os
from functools import lru_cache

from .js_builtins import JS_BUILTINS, \
    __callback_adapter__, __convert_py_argument__, \
    __convert_py_starred_argument__, \
    __convert_py_keyword_argument__, __convert_py_starred_keyword_argument__
from .shared import __unique_py_function_name__


def pycall(f, callback=None, error_callback=None):
    """
    Function that should be called inside js function to call python function
    Example: pycall(foo(x, y, z=5), js_callback, js_error_callback)
    Supports all types of arguments (positional, keywords, starred positional, starred keywords)
    :param f: function to call with its arguments. Write f as if you were calling it
    :param callback: js callback, that would be invoked with py function call results
    :param error_callback: js callback, that would be invoked if py function fails
    """
    if callback is not None:
        callback(f)


def _relative_path(path):
    return os.path.join(os.path.dirname(__file__), path)


def _node_source(node):
    return astor.to_source(node).strip()


class _PycallToIPythonKernelTransformer(ast.NodeTransformer):

    def __init__(self):
        super().__init__()

    def _pycall_arg_to_str(self, call_node):

        def convert_arg_value(arg):
            return __convert_py_argument__.__name__ + "({})".format(_node_source(arg))

        def convert_starred_arg_value(arg):
            return __convert_py_starred_argument__.__name__ + "({})".format(_node_source(arg.value))

        def convert_keyword_value(keyword):
            return __convert_py_keyword_argument__.__name__ + "({}, {})".format(keyword.arg,
                                                                                _node_source(keyword.value))

        def convert_starred_keyword_value(keyword):
            return __convert_py_starred_keyword_argument__.__name__ + "({})".format(_node_source(keyword.value))

        orig_func_name = _node_source(call_node.func)
        unique_func_name = __unique_py_function_name__.__name__ + "('{}', __context_id)".format(orig_func_name)

        args = []
        for arg in call_node.args:
            if isinstance(arg, ast.Starred):
                converted_arg = convert_starred_arg_value(arg)
            else:
                converted_arg = convert_arg_value(arg)

            args.append(converted_arg)

        kwargs = []
        for keyword in call_node.keywords:
            if keyword.arg is not None:
                kwarg = convert_keyword_value(keyword)
            else:
                kwarg = convert_starred_keyword_value(keyword)
            kwargs.append(kwarg)

        all_args = args + kwargs
        if len(all_args) == 0:
            all_args_sum = "+"
        else:
            all_args_sum = "+" + "+ ',' +".join(all_args) + "+"

        return "{}+'('{}')'".format(unique_func_name, all_args_sum)

    def visit_Call(self, node):
        if hasattr(node.func, "id") and node.func.id == pycall.__name__:
            if not (1 <= len(node.args) <= 3):
                raise ValueError("{} should have 1, 2 or 3 arguments".format(pycall.__name__))

            if not isinstance(node.args[0], ast.Call):
                raise ValueError("First argument to {} should be function call".format(pycall.__name__))

            args = []
            args.append(self._pycall_arg_to_str(node.args[0]))
            if len(node.args) > 1:
                callbacks = [_node_source(node.args[1])]
                if len(node.args) > 2:
                    callbacks.append(_node_source(node.args[2]))
                args.append(
                    "{'iopub':{'output': " + __callback_adapter__.__name__ + "(" + ",".join(callbacks) + ")}}"
                )

                args.append("{'silent': False}")

            return ast.parse("IPython.notebook.kernel.execute({})".format(",".join(args)))
        else:
            return node


def _transform_py_code(source_code):
    tree = ast.parse(source_code)
    tree.body[0].decorator_list = []
    tree = _PycallToIPythonKernelTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    return _node_source(tree)


@lru_cache(25)
def compile_context_generator(sources, minify):
    tempdir = tempfile.mkdtemp()

    try:
        sources = JS_BUILTINS + sources

        py_file = os.path.join(tempdir, "source.py")
        js_file = os.path.join(tempdir, "__target__", "source.js")
        js_merged_file = os.path.join(tempdir, "source_merged.js")
        js_minified_file = os.path.join(tempdir, "source_merged.min.js")
        if minify:
            js_out_file = js_minified_file
        else:
            js_out_file = js_merged_file

        with open(py_file, 'w') as f:
            for source in sources:
                f.write(_transform_py_code(source.source_code()))
                f.write("\n\n")

        subprocess.check_call(["transcrypt", "--nomin", py_file])
        subprocess.check_call(
            [_relative_path("./node_modules/rollup/bin/rollup"), js_file, "--format", "cjs", "--file", js_merged_file]
        )
        if minify:
            subprocess.check_call(
                [_relative_path("./node_modules/uglify-es/bin/uglifyjs"), js_merged_file, "-o", js_minified_file]
            )

        with open(js_out_file, 'r') as f:
            script = f.read()

        script = "\n".join(["function(__context_id, __data, __py_functions_names){"
                            "let exports = {};",
                            script,
                            "return exports;",
                            "}"])

        return script
    finally:
        shutil.rmtree(tempdir)
