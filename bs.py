from __future__ import annotations

import inspect
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
    __src_dir: str = os.path.dirname(os.path.realpath(__file__))
    __external_modules_directory: str = __src_dir + '/modules'
    __bootstrap_project_dir: str = os.getcwd()

    class Console:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

        @staticmethod
        def t(log, decoration: str):
            return decoration + log + Bootstrap.Console.ENDC

        @staticmethod
        def log(log, decoration: str | None = None):
            print(Bootstrap.Console.t(log, decoration or Bootstrap.Console.HEADER))

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
            service: str
            command: str | list

    def prepare(self):
        for external_module in self.external_modules:
            module_dir = self.__get_module_dir(external_module, external=True)
            with open(module_dir + '/bs-module.json', 'r') as module_json_file:
                module_json = module_json_file.read()
            module = jsonpickle.decode(module_json)
            self.modules.insert(
                0,
                module
            )

    def __get_module_root_dir(self, module: Module | str) -> str:
        module = self.__get_module(module)
        return self.root_directory + '/' + self.default_env + '/' + (module.root_directory_name or module.name)

    def __get_module_dir(self, module: Module | str, external: bool = False) -> str:
        module_name = module.name if isinstance(module, Bootstrap.Module) else module
        if external or isinstance(module, Bootstrap.Module) and module.external:
            return self.__external_modules_directory + '/' + module_name
        return self.__modules_directory + '/' + module_name

    def __get_module_env_variables(self, module: Module | str, env: str) -> dict:
        module = self.__get_module(module)

        variables = os.environ.copy()
        variables['BS_ROOT_DIR'] = self.__get_module_root_dir(module)
        variables['BS_ENV'] = env
        for _module in self.modules:
            variables['BS_' + _module.name.upper().replace('-', '_') + "_SERVICE"] = self.__get_service_name(_module,
                                                                                                             env)

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

    def __get_stack_name(self, module: Module, env: str) -> str:
        return '{0}-{1}-{2}'.format(self.name, env, module.name)

    def down_module(self, module: Module | str, env: str | None = None):
        module = self.__get_module(module)
        env = env or self.default_env
        os.chdir(self.__get_module_dir(module))
        command = [
            'docker-compose',
            '-p',
            self.__get_stack_name(module, env),
            'down'
        ]
        subprocess.run(command, env=self.__get_module_env_variables(module, env))

    def up_module(self, module: Module | str, env: str | None = None, rebuild: bool = False, remote: bool = False):
        module = self.__get_module(module)
        env = env or self.default_env
        os.chdir(self.__get_module_dir(module))
        command = [
            'docker-compose',
            '-p',
            self.__get_stack_name(module, env),
            'up', '-d', '--force-recreate'
        ]

        if rebuild:
            command.append('--build')

        res = subprocess.run(command, env=self.__get_module_env_variables(module, env))

        if res.returncode == 0:
            Bootstrap.Console.log(module.name.upper() + ': Running up scripts...', Bootstrap.Console.UNDERLINE)
            self.exec_module_commands(
                module,
                on='up',
                remote=remote,
                env=env,
                auto_scripts=True
            )

    def __get_module(self, module: str | Module) -> Module:
        if isinstance(module, Bootstrap.Module):
            return module

        for _module in self.modules:
            if _module.name == module:
                return _module

        raise Exception('Module ' + module + ' not found.')

    def exec_module_commands(self, module: Module | str, on: str, remote: bool, env: str, auto_scripts: bool):
        module = self.__get_module(module)
        for command in module.commands:
            if command.on == on:
                self.exec_module_command(module, command, remote, env, auto_scripts)

    def exec_module_command(
            self,
            module: Module | str,
            command: Module.Command,
            remote: bool = False,
            env: str | None = None,
            auto_scripts: bool = True
    ):
        module = self.__get_module(module)
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
                self.assert_service_running(
                    module=command.module or module,
                    env=env,
                    service=command.service,
                    remote=True
                )
                self.exec(
                    module=command.module or module,
                    service=command.service,
                    command=single_command,
                    env=env,
                    remote=remote
                )
                if auto_scripts:
                    self.exec_module_commands(command.module or module, 'after-command-exec', remote, env, False)

    def up(self, env: str | None = None, rebuild: bool | str = False, remote: bool | str = False):
        rebuild = True if rebuild == 'true' or rebuild else False
        remote = True if remote == 'true' or remote else False
        env = env or self.default_env
        for module in self.modules:
            self.up_module(module, rebuild=rebuild, remote=remote, env=env)

    def down(self, env: str | None = None):
        for module in self.modules:
            self.down_module(module, env)

    def __get_service_name(self, module: Module, env: str) -> str:
        return self.name + '-' + env + '-' + module.name

    def assert_service_running(self, module: Module | str, env: str | None = None, service: str | None = None, remote: bool = False):
        module = self.__get_module(module)
        env = env or self.default_env

        res = self.exec(module=module, service=service, env=env, command="/bin/sh -c 'echo OK'", remote=remote)
        if res.returncode != 0:
            Bootstrap.Console.log(service.upper()+' is not running.', Bootstrap.Console.WARNING)
            answer = input('Run '+module.name.upper()+' to continue? (y|yes)').lower()
            if answer == 'yes' or answer == 'y':
                self.up_module(module=module, env=env, remote=remote)

    def exec(self, module: Module | str, service: str, command: str, env: str | None = None, remote: bool = False):
        env = env or self.default_env
        module = self.__get_module(module)
        os.chdir(self.__get_module_dir(module))
        variables = self.__get_module_env_variables(module, env)

        _command_str = (
            'docker compose -p{0} exec {1} {2}'.format(
                self.__get_stack_name(module, env),
                service,
                command
            )
        ).format(**variables)
        _command = shlex.split(_command_str)

        return subprocess.run(_command, env=variables)

    @staticmethod
    def init_from_json(json_name: str = 'bs.json'):
        with open(Bootstrap.__bootstrap_project_dir + '/' + json_name, 'r') as json_file:
            data = json_file.read()
        _bs = jsonpickle.decode(data)
        if isinstance(_bs, Bootstrap):
            _bs.prepare()
            return _bs

        raise Exception('Invalid Bootstrap json file')

    @staticmethod
    def help():
        method_list = [
            func for func in dir(Bootstrap)
            if callable(getattr(Bootstrap, func)) and not
            func.startswith("_") and not
               inspect.isclass(getattr(Bootstrap, func))
        ]

        Bootstrap.Console.log('Bootstrap methods\r\n')

        for bs_method in method_list:
            signature = inspect.signature(getattr(Bootstrap, bs_method))
            parameters = [a for a in signature.parameters if a != 'self']
            log = "    " + Bootstrap.Console.t(bs_method, Bootstrap.Console.OKGREEN) \
                  + ": " \
                  + Bootstrap.Console.t(' '.join(parameters), Bootstrap.Console.BOLD)
            Bootstrap.Console.log(log)

    @staticmethod
    def setup():
        if os.path.isfile('./bs.json'):
            raise Exception('Bootstrap already inited.')
        _bs = Bootstrap()
        _bs.name = input("Name of bootstrap: ")
        _bs.default_env = input("Default env(default" + _bs.default_env + "): ") or _bs.default_env

        default_root_directory = '~/' + _bs.name
        _bs.root_directory = input("Root directory(" + default_root_directory + "):") or default_root_directory
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

method = sys.argv[1] if 1 < len(sys.argv) else 'help'
args_obj = {}

for arg in sys.argv[2:]:
    if '=' in arg:
        sep = arg.find('=')
        key, value = arg[:sep], arg[sep + 1:]
        args_obj[key] = value

getattr(bs, method)(**args_obj)
