import os
import shlex
import subprocess
import sys
import jsonpickle


class Bootstrap:
    name: str
    root_directory: str = '~/bs-project'
    modules: list = []
    default_env: str = 'dev'
    external_modules: list = []
    variables: dict = {}

    __modules_directory: str = os.path.abspath('modules')
    __src_dir: str = os.path.dirname(os.path.abspath(__file__))
    __external_modules_directory: str = __src_dir + '/modules'

    class Module:
        name: str
        root_directory_name: str | None = None
        docker_compose_file: str = 'dockercompose.yml'
        external: bool = False
        commands: list = []
        variables: dict = {}

        class Command:
            on: str = 'up'
            condition: str | list = []
            module: str | None = None
            container: str
            command: str | list

    def prepare(self):
        for external_module in self.external_modules:
            module_dir = self.get_module_dir(external_module, external=True)
            with open(module_dir + '/bs-module.json', 'r') as module_json_file:
                module_json = module_json_file.read()
            module = jsonpickle.decode(module_json)
            self.modules.insert(
                0,
                module
            )

    def add_module(self, module: Module):
        self.modules.append(module)
        module.bootstrap = self
        return self

    def get_module_root_dir(self, module: Module | str) -> str:
        module = self.get_module(module)
        return self.root_directory + '/' + self.default_env + '/' + (module.root_directory_name or module.name)

    def get_module_dir(self, module: Module | str, external: bool = False) -> str:
        module_name = module.name if isinstance(module, Bootstrap.Module) else module
        if external or isinstance(module, Bootstrap.Module) and module.external:
            return self.__external_modules_directory + '/' + module_name
        return self.__modules_directory + '/' + module_name

    def get_module_env_variables(self, module: Module | str, env: str) -> dict:
        module = self.get_module(module)

        variables = os.environ.copy()
        variables['BS_ROOT_DIR'] = self.get_module_root_dir(module)
        variables['BS_ENV'] = env
        for _module in self.modules:
            variables['BS_' + _module.name.upper().replace('-', '_') + "_SERVICE"] = self.get_service_name(_module, env)

        try:
            bootstrap_variables = self.variables[env]
        except KeyError:
            bootstrap_variables = {}

        try:
            module_variables = module.variables[env]
        except KeyError:
            module_variables = {}

        variables.update(bootstrap_variables)
        variables.update(module_variables)

        return variables

    def get_stack_name(self, module: Module, env: str) -> str:
        return '{0}-{1}-{2}'.format(self.name, env, module.name)

    def up_module(self, module: Module | str, rebuild: bool = False, remote: bool = False, env: str | None = None):
        module = self.get_module(module)
        env = env or self.default_env
        os.chdir(self.get_module_dir(module))
        command = [
            'docker-compose',
            '-p',
            self.get_stack_name(module, env),
            'up', '-d', '--force-recreate'
        ]

        if rebuild:
            command.append('--build')

        res = subprocess.run(command, env=self.get_module_env_variables(module, env))

        if res.returncode == 0:
            self.exec_module_commands(module, 'up', remote, env)

    def get_module(self, module: str | Module) -> Module:
        if isinstance(module, Bootstrap.Module):
            return module

        for _module in self.modules:
            if _module.name == module:
                return _module

        raise Exception('Module ' + module + ' not found.')

    def exec_module_commands(self, module: Module | str, on: str, remote: bool, env: str):
        module = self.get_module(module)

        for command in module.commands:
            if command.on == on:
                self.exec_module_command(module, command, remote, env)

    def exec_module_command(self, module: Module | str, command: Module.Command, remote: bool, env: str):

        module = self.get_module(module)

        command_list = [command.command] if isinstance(command.command, str) else command.command

        for single_command in command_list:
            must_exec = False
            condition = [command.condition] if isinstance(command.condition, str) else command.condition

            if not condition:
                must_exec = True
            else:
                if remote and "remote" in condition:
                    must_exec = True
                if not remote and "not:remote" in condition:
                    must_exec = True

            if must_exec:
                self.exec(command.module or module, command.container, single_command, env)

        self.exec_module_commands(module, 'after-command-exec', remote, env)

    def up(self, rebuild: bool | str = False, env: str | None = None, remote: bool | str = False):
        rebuild = True if rebuild == 'true' or rebuild else False
        remote = True if remote == 'true' or remote else False
        env = env or self.default_env
        for module in self.modules:
            self.up_module(module, rebuild, remote, env)

    def get_service_name(self, module: Module, env: str) -> str:
        return self.name + '-' + env + '-' + module.name

    def get_container_name(self, module: Module, container: str, env: str) -> str:
        return self.get_service_name(module, env) + '-' + container + '-1'

    def exec(self, module: Module | str, container: str, command: str, env: str | None = None):
        env = env or self.default_env
        module = self.get_module(module)
        os.chdir(self.get_module_dir(module))
        variables = self.get_module_env_variables(module, env)

        _command_str = ('docker compose -p' + self.get_stack_name(module, env) + ' exec ' + container + ' ' + command) \
            .format(**variables)
        _command = shlex.split(_command_str)

        return subprocess.run(_command, env=variables)

    @staticmethod
    def init_from_json(json_name: str = 'bs.json'):
        with open('./' + json_name, 'r') as json_file:
            data = json_file.read()
        _bs = jsonpickle.decode(data)
        if isinstance(_bs, Bootstrap):
            _bs.prepare()
            return _bs

        raise Exception('Invalid Bootstrap json file')

    @staticmethod
    def setup():
        if os.path.isfile('./bs.json'):
            raise Exception('Bootstrap already inited.')
        _bs = Bootstrap()
        _bs.name = input("Name of bootstrap: ")
        _bs.modules = []
        _bs.external_modules = []

        json_data = jsonpickle.encode(_bs, indent=4)

        f = open("./bs.json", "w")
        f.write(json_data)
        f.close()

try:
    bs = Bootstrap.init_from_json()
except Exception:
    bs = Bootstrap

method = sys.argv[1]
args_obj = {}

for arg in sys.argv[2:]:
    if '=' in arg:
        sep = arg.find('=')
        key, value = arg[:sep], arg[sep + 1:]
        args_obj[key] = value

getattr(bs, method)(**args_obj)
