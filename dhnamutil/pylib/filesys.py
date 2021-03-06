
import sys
import os
import io
import json
import pickle
import logging
import pprint


def get_os_independent_path(path):
    return os.path.join(*path.split('/'))


def get_relative_path_wrt_this(path):
    return os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        get_os_independent_path(path))


def get_line_gen(path, remove_newline=False):
    if isinstance(path, io.IOBase):
        f = path
    else:
        f = open(path)

    with f:
        for line in f:
            if remove_newline and line[-1] == '\n':
                line = line[:-1]
            yield line


def get_base_without_extension(path):
    file_name_only, file_extension = os.path.splitext(os.path.basename(path))
    assert file_extension[0] == '.'
    return file_name_only


def get_extension(path):
    _, file_extension = os.path.splitext(path)
    assert file_extension[0] == '.'
    return file_extension[1:]


def change_extension(path, new_ext):
    pre, ext = os.path.splitext(path)
    return '{}.{}'.format(pre, new_ext)


def open_with_mkdirs(path, *args):
    mkdirs_unless_exist(path)
    return open(path, *args)


def mkdirs_unless_exist(path):
    dir_path = os.path.dirname(path)
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)


class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return {'__py__set': list(obj)}
        else:
            return super().default(obj)


def as_python_object(dic):
    if '__py__set' in dic and len(dic) == 1:
        return set(dic['__py__set'])
    else:
        return dic


def example_extended_json_encoder():
    data = [1, 2, 3, set(['an', 'set', 'example']), {'some_key': 'some_value'}]
    j = json.dumps(data, cls=ExtendedJSONEncoder)
    print(json.loads(j, object_hook=as_python_object))


def json_save(obj, path, **kargs):
    with open(path, 'w') as f:
        json.dump(obj, f, **kargs)


def json_save_pretty(obj, path, **kargs):
    new_kargs = dict(ensure_ascii=False, indent=4, sort_keys=False)
    new_kargs.update(kargs)
    json_save(obj, path, **new_kargs)


def json_dump_pretty(obj, fp, **kargs):
    new_kargs = dict(ensure_ascii=False, indent=4, sort_keys=False)
    new_kargs.update(kargs)
    json.dump(obj, fp, **kargs)


def json_load(path, **kargs):
    with open(path) as f:
        return json.load(f, **kargs)


def pickle_save(obj, path, **kargs):
    with open(path, 'wb') as f:
        pickle.dump(obj, f, **kargs)


def pickle_save_highest(obj, path, **kargs):
    new_kargs = dict(protocol=pickle.HIGHEST_PROTOCOL)
    new_kargs.update(kargs)
    pickle_save(obj, path, **new_kargs)


def pickle_load(path, **kargs):
    with open(path, 'rb') as f:
        return pickle.load(f, **kargs)


def read_file(path):
    with open(path) as f:
        return f.read()


def write_file(path, text):
    with open(path, 'w') as f:
        return f.write(text)


def python_save(obj, path, repr=repr):
    return write_file(path, repr(obj))


def python_save_pretty(obj, path, **kargs):
    with open(path, 'w') as f:
        python_dump_pretty(obj, f, **kargs)


def python_dump_pretty(obj, fp, **kargs):
    pprint_kwargs = dict(indent=4)
    pprint_kwargs.update(kargs)
    assert 'stream' not in pprint_kwargs

    pprint.pprint(obj, stream=fp, **pprint_kwargs)


def python_load(path, *args):
    assert len(args) <= 2  # for globals and locals
    return eval(read_file(path), *args)


def make_logger(name, log_file_path, to_stdout=True, overwriting=False, format_str=None):
    if format_str is None:
        log_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    else:
        log_formatter = logging.Formatter(format_str)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    mode = 'w' if overwriting else 'a'
    file_handler = logging.FileHandler("{0}".format(log_file_path), mode=mode)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    if to_stdout:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)

    return logger
