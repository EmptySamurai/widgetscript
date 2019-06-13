from .shared import __unique_py_function_name__, __unique_context_variable_name__, __unique_handle_name__
from .source import JsFunction, JsFlat


def __callback_adapter__(callback, error_callback):
    def wrapper(result):
        if "ename" in result.content:
            if error_callback:
                error_callback(result.content)
            else:
                console.error(result.content)
            return

        result = result.content.data['text/plain']
        # trim quotes
        result = result.substring(1, result.length - 1)
        return callback(JSON.parse(result))

    return wrapper


def __convert_py_argument__(arg):
    return "'" + btoa(JSON.stringify(arg, lambda k, v: None if v == None else v)) + "'"


def __convert_py_starred_argument__(args):
    converted_args = []
    for arg in args:
        converted_args.push(__convert_py_argument__(arg))

    return converted_args.join(",")


def __convert_py_keyword_argument__(name, arg):
    return name + "=" + __convert_py_argument__(arg)


def __convert_py_starred_keyword_argument__(args):
    __pragma__('jsiter')

    converted_args = []
    for arg_name in args:
        converted_args.push(__convert_py_keyword_argument__(arg_name, args[arg_name]))

    __pragma__('nojsiter')
    return converted_args.join(",")


def __cleanup__():
    for py_func in __py_functions_names:
        IPython.notebook.kernel.execute("del {}".format(py_func))

    window[__unique_context_variable_name__(__context_id)] = js_undefined
    console.log("Cleaned")


def __common_init__():
    handle = document.getElementById(__unique_handle_name__(__context_id))
    cell = handle.closest(".cell")

    def callback(record, observer):
        for mutation in record:
            for node in mutation.removedNodes:
                if node.contains(handle) or node == handle:
                    __cleanup__()
                    observer.disconnect()
                    return

    observer = __new__(MutationObserver(callback))
    observer.observe(cell.parentElement, {"childList": True, "subtree": True})


JS_BUILTINS = tuple(
    [
        JsFunction(f) for f in
        [
            __callback_adapter__,
            __convert_py_argument__,
            __convert_py_starred_argument__,
            __convert_py_keyword_argument__,
            __convert_py_starred_keyword_argument__,
            __unique_py_function_name__,
            __unique_context_variable_name__,
            __cleanup__,
            __unique_handle_name__
        ]
    ] + [
        JsFlat(f) for f in
        [
            __common_init__
        ]
    ]
)
