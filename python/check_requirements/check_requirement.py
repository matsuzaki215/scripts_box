import click
import glob
import os
import re
from typing import Dict, List, Optional, TypeVar

REGEX_READ = '-r\s*([^#\s]+)'
REGEX_MODULE = '([\w-]+)\s*([=!<>~]+)([0-9.]+)'
T = TypeVar('T', str, List[str])


class CheckRequirement(object):
    def __init__(self, dir_path: str):
        self.requirements_dir: str = dir_path
        self.tree: Dict[str, Dict[str, Optional[T]]] = dict()

        self.patterns = {
            '-r': re.compile(REGEX_READ),
            'module': re.compile(REGEX_MODULE)
        }

        self.dependencies = {}

    def _get_requirements(self):
        requirements = glob.glob(os.path.join(self.requirements_dir, '*.txt'))
        return requirements

    def _parse_requirement(self, file):
        filename = os.path.basename(file)

        self.tree[filename] = {
            '-r': None,
            'modules': list()
        }
        with open(file, 'r') as fp:
            for line in fp.readlines():
                result = self.patterns['-r'].match(line)
                if result:
                    self.tree[filename]['-r'] = result.group(1)

                result = self.patterns['module'].match(line)
                if result:
                    self.tree[filename]['modules'].append(result.group(1))

                if self.tree[filename]['-r'] is not None:
                    if self.tree[filename]['-r'] not in self.dependencies:
                        self.dependencies[self.tree[filename]['-r']] = set()
                    self.dependencies[self.tree[filename]['-r']].add(filename)

    def parse(self, files):
        self.tree = dict()

        for f in files:
            self._parse_requirement(f)

        return self.tree

    def check(self):
        errors = dict()

        requirements = self._get_requirements()
        module_tree = self.parse(requirements)
        for filename, value in module_tree.items():
            errors[filename] = list()

            parent = value['-r']
            modules = value['modules']
            # check self-duplication
            self_duplicated = [x for x in set(modules) if modules.count(x) > 1]

            for dm in self_duplicated:
                errors[filename].append(f'{dm} is duplicated in same file.')

            reference = f'>> {parent}'
            while parent in module_tree:
                parent_value = module_tree[parent]
                parent_duplicated = set(modules) & set(parent_value['modules'])
                for dm in parent_duplicated:
                    errors[filename].append(f'{dm} is duplicated in ({reference})')
                parent = parent_value['-r']
                reference = f'{reference} >> {parent}'
        return errors

    def show(self):
        requirements = self._get_requirements()
        module_tree = self.parse(requirements)

        for filename, value in module_tree.items():
            print(filename, value)

    def show_error(self):
        error_list = self.check()

        values = []
        for v in self.dependencies.values():
            values.extend(v)

        root_file = ''
        for key in self.dependencies.keys():
            if key not in values:
                root_file = key
                break

        self._show_error_recursive(error_list, root_file)

        """
        for filename, errors in error_list.items():
            if len(errors) == 0:
                print(f'{filename} is OK')
                continue

            for err in errors:
                print(f'{filename}: {err}')
        """

    def _show_error_recursive(self, error_list, filename, depth=0):
        errors = error_list[filename]
        indent = '    '*(depth-1)
        prefix = '' if depth == 0 else f'  {indent}└ '

        if len(errors) == 0:
            print(f'{prefix}{filename}')

        for err in errors:
            print(f'{prefix}{filename} <-- {err}')

        if filename not in self.dependencies:
            return

        for fn in self.dependencies[filename]:
            self._show_error_recursive(error_list, filename=fn, depth=depth+1)


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument('dir_path', type=str)
def main(dir_path):
    rv = CheckRequirement(dir_path)
    rv.show_error()


if __name__ == '__main__':
    main()
