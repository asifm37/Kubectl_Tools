#!/usr/bin/python3

from kube_tools import KubectlTools


# This script will Copy <$FILE_PATH$> to relevant <$PROJECT_NAME$> in the Container passed in 'ktoolrc.ini' file
if __name__ == '__main__':
    kube_tool = KubectlTools()
    kube_tool.kubectl_copy_to_container()
