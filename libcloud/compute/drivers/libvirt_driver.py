# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeState
from libcloud.compute.types import Provider

try:
    import libvirt
    have_libvirt = True
except ImportError:
    have_libvirt = False


class LibvirtNodeDriver(NodeDriver):
    """
    Libvirt (http://libvirt.org/) node driver.

    Usage: LibvirtNodeDriver(uri='vbox:///session').
    To enable debug mode, set LIBVIR_DEBUG environment variable.
    """

    type = Provider.LIBVIRT
    name = 'Libvirt'
    website = 'http://libvirt.org/'

    NODE_STATE_MAP = {
        0: NodeState.TERMINATED,  # no state
        1: NodeState.RUNNING,  # domain is running
        2: NodeState.PENDING,  # domain is blocked on resource
        3: NodeState.TERMINATED,  # domain is paused by user
        4: NodeState.TERMINATED,  # domain is being shut down
        5: NodeState.TERMINATED,  # domain is shut off
        6: NodeState.UNKNOWN,  # domain is crashed
        7: NodeState.UNKNOWN,  # domain is suspended by guest power management
    }

    def __init__(self, uri):
        """
        :param  uri: Hypervisor URI (e.g. vbox:///session, qemu:///system,
                     etc.).
        :type   uri: ``str``
        """
        if not have_libvirt:
            raise RuntimeError('Libvirt driver requires \'libvirt\' Python ' +
                               'package')

        self._uri = uri
        self.connection = libvirt.open(uri)

    def list_nodes(self):
        domains = self.connection.listAllDomains()

        nodes = []
        for domain in domains:
            state, max_mem, memory, vcpu_count, used_cpu_time = domain.info()

            if state in self.NODE_STATE_MAP:
                state = self.NODE_STATE_MAP[state]
            else:
                state = NodeState.UNKNOWN

            # TODO: Use XML config to get Mac address and then parse ips
            extra = {'uuid': domain.UUIDString(), 'os_type': domain.OSType(),
                     'types': self.connection.getType(),
                     'used_memory': memory / 1024, 'vcpu_count': vcpu_count,
                     'used_cpu_time': used_cpu_time}

            node = Node(id=domain.ID(), name=domain.name(), state=state,
                        public_ips=[], private_ips=[], driver=self,
                        extra=extra)
            node._uuid = domain.UUIDString()  # we want to use a custom UUID
            nodes.append(node)

        return nodes

    def reboot_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.reboot(flags=0) == 0

    def destroy_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.destroy() == 0

    def ex_start_node(self, node):
        """
        Start a stopped node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        domain = self._get_domain_for_node(node=node)
        return domain.create() == 0

    def ex_shutdown_node(self, node):
        """
        Shutdown a running node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        domain = self._get_domain_for_node(node=node)
        return domain.shutdown() == 0

    def ex_suspend_node(self, node):
        """
        Suspend a running node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        domain = self._get_domain_for_node(node=node)
        return domain.suspend() == 0

    def ex_resume_node(self, node):
        """
        Resume a suspended node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        domain = self._get_domain_for_node(node=node)
        return domain.resume() == 0

    def _get_domain_for_node(self, node):
        """
        Return libvirt domain object for the provided node.
        """
        domain = self.connection.lookupByUUIDString(node.uuid)
        return domain
