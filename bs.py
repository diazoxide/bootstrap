from __future__ import annotations

import inspect
import os
import shlex
import subprocess
import sys
import yaml
from pathlib import Path


class Bootstrap(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!Bootstrap'

    name: str

    root_dir: str | dict = '~/bs-project'
    ssh_keys_dir: str | dict | None = '~/.ssh'

    modules: list = []
    default_env: str = 'dev'

    variables: dict = {}
    __version: str = '2.0.6'
    __modules_dir: str = os.path.abspath('modules')
    __src_dir: str = os.path.dirname(os.path.realpath(__file__))
    __bootstrap_project_dir: str = os.environ.get('BS_PROJECT_FILE', os.getcwd())

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

    class Module(yaml.YAMLObject):
        yaml_loader = yaml.SafeLoader
        yaml_tag = u'!Module'
        name: str
        repo: str | None | dict = None

        root_dir: str | dict | None = None
        ssh_keys_dir: str | dict | None = None

        root_dir_name: str | None = None
        docker_compose_file: str = 'dockercompose.yml'
        commands: list = []
        variables: dict = {}

        class Command(yaml.YAMLObject):
            yaml_loader = yaml.SafeLoader
            yaml_tag = u'!Command'
            on: str = 'up'
            condition: str | list = []
            module: str | None = None
            service: str
            command: str | list

    def __yaml(self):
        serialized = yaml.dump(self)
        return serialized

    def __get_module_root_dir(self, module: Module | str, env: str) -> str:
        module = self.__get_module(module)
        root_dir = self.__get_root_dir(module=module, env=env)
        return root_dir + '/' \
               + (module.root_dir_name or module.name)

    def __get_module_ssh_keys_dir(self, module: Module | str, env: str) -> str:
        keys_dir = module.ssh_keys_dir if module.ssh_keys_dir is not None else self.ssh_keys_dir
        return self.__get_property_for_env(keys_dir, env)

    def __get_root_dir(self, module: Module | str, env: str) -> str:
        keys_dir = module.root_dir if module.root_dir is not None else self.root_dir
        p = self.__get_property_for_env(keys_dir, env)
        p = os.path.expanduser(p)
        return p

    def __get_module_env_variables(self, module: Module | str, env: str) -> dict:
        module = self.__get_module(module)

        variables = os.environ.copy()
        variables['BS_ROOT_DIR'] = self.__get_module_root_dir(module=module, env=env)
        variables['BS_SSH_KEYS_DIR'] = self.__get_module_ssh_keys_dir(module=module, env=env)
        variables['BS_ENV'] = env
        for _module in self.modules:
            variables['BS_' + _module.name.upper().replace('-', '_') + "_MODULE"] = self.__get_service_name(
                _module,
                env
            )
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
        variables = self.__get_module_env_variables(module=module, env=env)
        os.chdir(self.__get_module_root_dir(module=module, env=env))
        command = [
            'docker-compose',
        ]

        command += [
            '-p',
            self.__get_stack_name(module, env),
            'down',
            '--remove-orphans'
        ]
        subprocess.run(command, env=variables)

    @staticmethod
    def __get_property_for_env(var: str | dict | None, env: str):
        if type(var) is dict:
            return var[env] if env in var else None
        return var

    def __get_module(self, module: str | Module) -> Module:
        if isinstance(module, Bootstrap.Module):
            return module

        for _module in self.modules:
            if _module.name == module:
                return _module

        raise Exception('Module ' + module + ' not found.')

    def __get_service_name(self, module: Module, env: str) -> str:
        return self.name + '-' + env + '-' + module.name

    def __assert_service_running(
            self, module: Module | str,
            env: str | None = None,
            service: str | None = None
    ):
        module = self.__get_module(module)
        env = env or self.default_env

        res = self.exec(module=module, service=service, env=env, command="/bin/sh -c 'echo OK'")
        if res.returncode != 0:
            Bootstrap.Console.log(service.upper() + ' is not running.', Bootstrap.Console.WARNING)
            answer = input('Run ' + module.name.upper() + ' to continue? (y|yes)').lower()
            if answer == 'yes' or answer == 'y':
                self.up_module(module=module, env=env)

    # region Public methods
    def up(
            self,
            env: str | None = None,
            rebuild: bool | str = False,
    ):
        rebuild = True if rebuild == 'true' or rebuild else False
        env = env or self.default_env
        for module in self.modules:
            self.up_module(module=module, rebuild=rebuild, env=env)

    def list(self):
        i = 1
        for module in self.modules:
            repo_url = module.repo.get('src', 'n/a') if isinstance(module.repo, dict) else module.repo
            Bootstrap.Console.log(str(i) + '. ' + module.name + ' > ' + repo_url, Bootstrap.Console.OKCYAN)
            i = i + 1

    def down(
            self,
            env: str | None = None,
    ):
        for module in self.modules:
            self.down_module(module=module, env=env)

    def up_module(
            self,
            module: Module | str,
            env: str | None = None,
            rebuild: bool | str = False,
            repo_branch: str | None = None
    ):
        rebuild = True if rebuild == 'true' or rebuild else False

        module = self.__get_module(module)
        env = env or self.default_env
        variables = self.__get_module_env_variables(module=module, env=env)
        module_root_dir = self.__get_module_root_dir(module=module, env=env)

        Bootstrap.Console.log('Module directory: ' + module_root_dir)

        Path(module_root_dir).mkdir(parents=True, exist_ok=True)

        os.chdir(module_root_dir)

        if not module.repo:
            Bootstrap.Console.log('Module repo not defined', Bootstrap.Console.FAIL)
            return

        if isinstance(module.repo, str):
            repo_src = module.repo
        else:
            repo_src = module.repo.get('src')
            repo_branch = module.repo.get('branch', repo_branch) if repo_branch is None else repo_branch

        check_first_clone_proc = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], capture_output=True)
        if check_first_clone_proc.returncode != 0:
            pull_command_proc = subprocess.run(['git', 'clone', repo_src, '.'])
            if pull_command_proc.returncode != 0:
                Bootstrap.Console.log("Failed cloning from remote git repository!", Bootstrap.Console.WARNING)
                return

        if repo_branch:
            checkout_proc = subprocess.run(['git', 'checkout', repo_branch])
            if checkout_proc.returncode != 0:
                Bootstrap.Console.log("Checkout failed!", Bootstrap.Console.WARNING)

        command = [
            'docker-compose',
            '-p',
            self.__get_stack_name(module, env),
            'up', '-d', '--force-recreate', '--wait', '--remove-orphans'
        ]

        if rebuild:
            Bootstrap.Console.log('Rebuild containers', Bootstrap.Console.OKCYAN)
            command += ['--build']

        res = subprocess.run(command, env=variables)

        if res.returncode == 0:
            Bootstrap.Console.log(module.name.upper() + ': Running up scripts...', Bootstrap.Console.UNDERLINE)
            self.exec_module_commands(
                module,
                on='up',
                env=env,
                auto_scripts=True
            )

    def exec_module_commands(
            self,
            module: Module | str,
            on: str,
            env: str,
            auto_scripts: bool = True,
    ):
        module = self.__get_module(module)
        for command in module.commands:
            if command.on == on:
                self.exec_module_command(module=module, command=command, env=env, auto_scripts=auto_scripts)

    def exec_module_command(
            self,
            module: Module | str,
            command: Module.Command,
            env: str | None = None,
            auto_scripts: bool = True
    ):
        module = self.__get_module(module)
        command_list = [command.command] if isinstance(command.command, str) else command.command

        for single_command in command_list:
            self.__assert_service_running(
                module=command.module or module,
                env=env,
                service=command.service
            )
            self.exec(
                module=command.module or module,
                service=command.service,
                command=single_command,
                env=env
            )
            if auto_scripts:
                self.exec_module_commands(
                    module=command.module or module,
                    on='after-command-exec',
                    env=env,
                    auto_scripts=False
                )

    def exec(self, module: Module | str, service: str, command: str, env: str | None = None):
        env = env or self.default_env
        module = self.__get_module(module)
        os.chdir(self.__get_module_root_dir(module=module, env=env))
        variables = self.__get_module_env_variables(module=module, env=env)

        _command_str = (
            'docker-compose -p{0} exec {1} {2}'.format(
                self.__get_stack_name(module, env),
                service,
                command
            )
        ).format(**variables)
        _command = shlex.split(_command_str)

        return subprocess.run(_command, env=variables)

    @staticmethod
    def init_from_yaml(yaml_name: str = 'bs.yaml'):
        Bootstrap.__branding()
        file_name = Bootstrap.__bootstrap_project_dir + '/' + yaml_name

        if not os.path.isfile(file_name):
            raise Exception('Bootstrap bs.yaml file not found')

        with open(Bootstrap.__bootstrap_project_dir + '/' + yaml_name, 'r') as yaml_file:
            data = yaml_file.read()
        _bs = yaml.safe_load(data)
        if isinstance(_bs, Bootstrap):
            return _bs
        else:
            raise Exception('Invalid Bootstrap bs.yaml file')

    @staticmethod
    def setup():
        if os.path.isfile('./bs.yaml'):
            raise Exception('Bootstrap already inited.')
        _bs = Bootstrap()
        _bs.name = input("Name of bootstrap: ")
        _bs.default_env = input("Default env(default" + _bs.default_env + "): ") or _bs.default_env

        default_root_dir = '~/' + _bs.name
        _bs.root_dir = input("Root dir(" + default_root_dir + "):") or default_root_dir
        _bs.modules = []

        f = open("./bs.yaml", "w")
        f.write(_bs.__yaml())
        f.close()

    @staticmethod
    def help():
        method_list = [
            func for func in dir(Bootstrap)
            if callable(getattr(Bootstrap, func)) and not
            func.startswith("_") and not inspect.isclass(getattr(Bootstrap, func))
        ]

        Bootstrap.Console.log('Bootstrap methods')

        for bs_method in method_list:
            signature = inspect.signature(getattr(Bootstrap, bs_method))
            parameters = [a for a in signature.parameters if a != 'self']
            log = "    " + Bootstrap.Console.t(bs_method, Bootstrap.Console.OKGREEN) \
                  + ": " \
                  + Bootstrap.Console.t(' '.join(parameters), Bootstrap.Console.BOLD)
            Bootstrap.Console.log(log)

    @staticmethod
    def version():
        Bootstrap.Console.log('Diazoxide Bootstrap', Bootstrap.Console.OKCYAN)
        Bootstrap.Console.log('Version: ' + Bootstrap.__version, Bootstrap.Console.OKGREEN)

    @staticmethod
    def update():
        result = subprocess.run([
            'sh',
            '-c',
            'eval "$(curl -fsSL https://raw.githubusercontent.com/diazoxide/bootstrap/HEAD/install.sh)"'
        ], capture_output=True)

        if result.returncode == 0:
            Bootstrap.Console.log('Successfully updated.')
            subprocess.run(['bs', 'version'])
        elif result.returncode == 128:
            Bootstrap.Console.log("Permission denied. Run update command with super user.")
        else:
            Bootstrap.Console.log("Update failed.")

    # endregion Public methods
    @staticmethod
    def __branding():
        with open(Bootstrap.__src_dir + '/branding', 'r') as branding_txt:
            Bootstrap.Console.log(branding_txt.read(), Bootstrap.Console.WARNING)


try:
    bs = Bootstrap.init_from_yaml()
except Exception as e:
    Bootstrap.Console.log(str(e))
    bs = Bootstrap

method = sys.argv[1] if 1 < len(sys.argv) else 'help'
method = method.replace('-', '_')
args_obj = {}

for arg in sys.argv[2:]:
    if '=' in arg:
        sep = arg.find('=')
        key, value = arg[:sep].replace('-', '_'), arg[sep + 1:]
        args_obj[key] = value

getattr(bs, method)(**args_obj)
