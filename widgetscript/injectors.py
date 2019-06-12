import json

from .shared import __unique_context_variable_name__


class AnonymousJsContextInjector:
    def __init__(self, context_generator_script):
        self.context_generator_script = context_generator_script

    def get_inject_script(self, context_id, data, py_functions_names):
        return "window.{} = ({})({});".format(
            __unique_context_variable_name__(context_id),
            self.context_generator_script,
            ",".join(("'" + context_id + "'", json.dumps(data), json.dumps(py_functions_names)))
        )


class PrecompiledJsContextInjector:
    def __init__(self, precompiled_context):
        self.precompiled_context = precompiled_context

    def get_inject_script(self, context_id, data, py_functions_names):
        return "window.{} = {}({});".format(
            __unique_context_variable_name__(context_id),
            self.precompiled_context.context_generator_var_name,
            ",".join(("'" + context_id + "'", json.dumps(data), json.dumps(py_functions_names)))
        )
