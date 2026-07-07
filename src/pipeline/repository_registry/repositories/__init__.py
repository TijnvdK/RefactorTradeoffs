from importlib import import_module
from pkgutil import iter_modules

for _, module_name, _ in iter_modules(__path__):
    import_module(f'{__name__}.{module_name}')
