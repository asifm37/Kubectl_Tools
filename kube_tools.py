#!/usr/local/bin/python2.7
import ConfigParser
import os
import sys
import logging
import time

# These are the sequences need to get colored ouput
from string import Template

RESET_SEQ = "\033[0m"
RED_COLOR_SEQ = "\033[0;31m"
YELLOW_COLOR_SEQ = "\033[0;33m"
GREEN_COLOR_SEQ = "\033[0;32m"

logging.addLevelName(logging.INFO, GREEN_COLOR_SEQ + logging.getLevelName(logging.INFO))
logging.addLevelName(logging.WARNING, YELLOW_COLOR_SEQ + logging.getLevelName(logging.WARNING))
logging.addLevelName(logging.ERROR, RED_COLOR_SEQ + logging.getLevelName(logging.ERROR))
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(levelname)-1s: %(message)s' + RESET_SEQ)

logger = logging.getLogger()

CONF_FILENAME = 'ktoolrc.ini'
DEFAULT_CONF = {
    'container': {
        'podname': '',
        'namespace': os.getenv('USER')
    },
    'mapping': {
        'dst_package_dir': '/usr/local/lib/python3.6/dist-packages',
        'dst_test_dir': '/hwqe/hadoopqe',
        'dst_yaml_dir': '/ansible'
    },
    'command': {
        'kcp': "/usr/local/bin/kubectl cp $src_path ${namespace}/${podname}:${dest_path}",
        'kexec': "/usr/local/bin/kubectl exec -t $podname -n $namespace -c system-test -- $command",
        'sudo_login_and_run': "sudo su - hrt_qa -c \"$run_command\" ",
        'login_and_run': "su -c \"$run_command\" ",
        'texas_entry': "pkill supervisord && texas_test_entrypoint --test-type system_test --run-tests-path /ansible/system_test.yml",
        'ansible_play': "ansible-playbook $yaml_file -vvvv",
        'cd_and_run': "source /etc/profile && cd $test_dir && $test_command",
        'pytest': "python2.7 -m pytest -s $test_file_path --output=${test_name} --junitxml=${test_name}_junit.xml 2>&1 | tee /tmp/console_${test_name}.log"
    }
}


class KubectlTools:
    def __init__(self):
        self.file_path = None
        self.project_name = None
        self.ktoolrc_file = None
        self.cur_config = ConfigParser.ConfigParser()
        self.dest_path = None

        self.__check_and_validate_parameters()
        self.__read_and_validate_config_file()
        self.__map_src_to_dest_path()

    def __check_and_validate_parameters(self):
        len_arg = len(sys.argv[1:])

        # Checking for Required Argument FilePath
        if len_arg >= 1 and sys.argv[1]:
            self.file_path = sys.argv[1]
            logger.info("file_path = %s", self.file_path)
        else:
            logger.error("$FilePath$ is missing from Arguments")
            self.__print_usage_and_exit()

        # Checking for Required Argument ProjectName
        if len_arg >= 2 and sys.argv[2]:
            self.project_name = sys.argv[2]
            logger.info("project_name = %s", self.project_name)
        else:
            logger.error("$ModuleName$ is missing from Arguments")
            self.__print_usage_and_exit()

        # Checking for config file ktoolrc & creating if not exist
        if len_arg >= 3 and sys.argv[3]:
            self.ktoolrc_file = sys.argv[3]
            logger.warn("Using config file from %s", self.ktoolrc_file)
        else:
            self.ktoolrc_file = os.path.join(os.getcwd(), CONF_FILENAME)
            if os.path.isfile(self.ktoolrc_file):
                logger.warn("Using config file from %s", self.ktoolrc_file)
            else:
                logger.warn("No config file found! Using default configurations")
                self.__write_conf_to_file()

    def __read_and_validate_config_file(self):
        self.cur_config.optionxform = str
        if os.path.isfile(self.ktoolrc_file):
            self.cur_config.read(self.ktoolrc_file)
        else:
            logger.error("Give Config File [%s] doesn't exists!", self.ktoolrc_file)
            exit(1)
        # Checking for podname
        st_podname = self.cur_config.get('container', 'podname')
        if st_podname:
            logger.warn("Using podname = <%s>!\n\t--> If you want to change the podname, change it at <%s> file <--",
                        st_podname, self.ktoolrc_file)
        else:
            logger.error("Please set the value for 'podname' in the file %s", self.ktoolrc_file)
            exit(1)

    def __map_src_to_dest_path(self):
        if self.project_name == "texas_test_entrypoint":  # self.file_path.endswith(('.yaml', '.yml'))
            from pathlib import Path
            target_path = self.file_path[self.file_path.index(self.project_name) + len(self.project_name + "/files"):]
            logger.info(self.file_path)
            self.dest_path = os.path.join(self.cur_config.get(section='mapping', option='dst_yaml_dir'),
                                          target_path)
        else:
            self.dest_path = self.cur_config.get(
                section='mapping',
                option='dst_package_dir' if self.project_name in ['beaver-qe', 'beaver-common'] else 'dst_test_dir'
            ) + self.file_path.split(self.project_name)[1]

    # Helper Functions
    def __write_conf_to_file(self):
        config_parser = ConfigParser.ConfigParser()
        config_parser.optionxform = str
        for sec, prop_dict in DEFAULT_CONF.iteritems():
            config_parser.add_section(sec)
            for k, v in prop_dict.iteritems():
                config_parser.set(sec, k, v)
        try:
            with open(self.ktoolrc_file, 'wb') as configfile:
                config_parser.write(configfile)
        except IOError as e:
            logger.error(e)
            logger.error("Unable to write the config to config file %s", self.ktoolrc_file)
        return True

    @staticmethod
    def __print_usage_and_exit():
        print "%s %s <$FilePath$> <$ProjectName$> [ktoolrc_filepath] %s" % (YELLOW_COLOR_SEQ, sys.argv[0], RESET_SEQ)
        exit(-1)

    @staticmethod
    def __run_command(command):
        if os.system(command) == 0:
            logger.info("Command Ran Successfully")
            return True
        else:
            logger.error("Command Execution Failed")
            return False

    # Exposed Functions
    def kubectl_copy_to_container(self):
        if os.path.exists(self.file_path) and self.project_name in self.file_path:
            st_podname = self.cur_config.get('container', 'podname')
            namespace = self.cur_config.get('container', 'namespace')

            dest_path = self.dest_path
            if os.path.isdir(self.file_path):
                dest_path = os.path.dirname(self.dest_path)

            cmd_template = Template(self.cur_config.get('command', 'kcp'))
            kcp_commad = cmd_template.substitute(src_path=self.file_path, namespace=namespace,
                                                 podname=st_podname, dest_path=dest_path)

            logger.info("[Running] cmd = %s", kcp_commad)
            return self.__run_command(kcp_commad)
        else:
            logger.warn("Please check if [%s] exists & is part of project [%s]", self.file_path, self.project_name)
            return False

    def kubectl_run_test_on_container(self):
        st_podname = self.cur_config.get('container', 'podname')
        namespace = self.cur_config.get('container', 'namespace')

        if self.file_path.endswith(('.yaml', '.yml')):
            if os.path.basename(self.file_path) == 'system_test.yml':
                cmd = self.cur_config.get('command', 'texas_entry')
            else:
                cmd = Template(self.cur_config.get('command', 'ansible_play')).substitute(yaml_file=self.dest_path)
            login_run_cmd = Template(self.cur_config.get('command', 'login_and_run')).substitute(run_command=cmd)
        else:
            # Assuming Pytest Run on File or Folder
            test_dir = self.cur_config.get('mapping', 'dst_test_dir')
            relative_path = os.path.relpath(self.dest_path, test_dir)
            test_name = os.path.basename(self.dest_path).split('.')[0] + '_' + str(int(time.time()))

            pytest_cmd = Template(self.cur_config.get('command', 'pytest')).substitute(test_file_path=relative_path,
                                                                                       test_name=test_name)
            cmd = Template(self.cur_config.get('command', 'cd_and_run')).substitute(test_dir=test_dir,
                                                                                    test_command=pytest_cmd)
            login_run_cmd = Template(self.cur_config.get('command', 'sudo_login_and_run')).substitute(run_command=cmd)
        kexec_cmd = Template(self.cur_config.get('command', 'kexec')).substitute(podname=st_podname,
                                                                                 namespace=namespace,
                                                                                 command=login_run_cmd)

        logger.info("[Running] cmd = %s", kexec_cmd)
        return self.__run_command(kexec_cmd)


if __name__ == '__main__':
    kube_tool = KubectlTools()
    if kube_tool.kubectl_copy_to_container():
        kube_tool.kubectl_run_test_on_container()
    else:
        time.sleep(1)
        logger.warn("Skipping KubeTool Run Test as Copy failed")
