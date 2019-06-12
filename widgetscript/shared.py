def __unique_py_function_name__(name, context_id):
    return "__" + name + "_in_context_" + context_id


def __unique_context_variable_name__(context_id):
    return "__js_context_" + context_id


def __unique_handle_name__(context_id):
    return "__js_context_" + context_id + "_handle"
