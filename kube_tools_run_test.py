#!/usr/local/bin/python2.7

from kube_tools import KubectlTools


# This script will run the python test <$File/folder$> in CONTAINER
if __name__ == '__main__':
    kube_tool = KubectlTools()
    kube_tool.kubectl_run_test_on_container()
