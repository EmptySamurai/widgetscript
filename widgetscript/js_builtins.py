from .shared import __unique_py_function_name__, __unique_context_variable_name__, __unique_handle_name__


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


def __export_wrapper__(func):
    def wrapper(*args):
        decoded_args = []
        for arg in args:
            decoded_args.push(JSON.parse(atob(arg)))
        func(*decoded_args)

    return wrapper


def __convert_exports__(exports):
    __pragma__('jsiter')

    for func_name in exports:
        exports[func_name] = __export_wrapper__(exports[func_name])

    __pragma__('nojsiter')
    return exports


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


JS_BUILTINS = [__callback_adapter__,
               __convert_py_argument__,
               __convert_py_starred_argument__,
               __convert_py_keyword_argument__,
               __convert_py_starred_keyword_argument__,
               __export_wrapper__,
               __convert_exports__,
               __unique_py_function_name__,
               __unique_context_variable_name__,
               __cleanup__,
               __common_init__,
               __unique_handle_name__
               ]
