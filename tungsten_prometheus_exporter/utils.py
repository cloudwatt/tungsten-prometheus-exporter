import collections


def my_import(name):
    components = name.split(".")
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def dict_merge(dct, dct_merge):
    for k, v in dct_merge.items():
        if (
            k in dct and
            isinstance(dct[k], dict) and
            isinstance(dct_merge[k], collections.Mapping)
        ):
            dict_merge(dct[k], dct_merge[k])
        else:
            dct[k] = dct_merge[k]
