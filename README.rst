Overview
########

This is the a connector to use Origin Nexus' hosted `ELAN center <https://origin-nexus.com/elan/#elan-center>`_ with `ELAN agent <https://github.com/michael-mri/elan-agent>`_.

`ELAN center <https://origin-nexus.com/elan/#elan-center>`_ provides a web interface to configure and manage several ELAN agent with features such as delegated admin, GSuite authentication,...



Installation
############

ELAN Agent is designed to run on Ubuntu 18.04 (Bionic)

* Register an account on `ELAN center <https://elan-center.origin-nexus.com>`_
* On a fresh install of Ubuntu server 18.04:

  .. code-block::
  
    $ sudo add-apt-repository ppa:easy-lan/stable
    $ sudo apt-get update
    $ sudo apt install elan-center-connector

Note: This will modify your network configuration and create a bridge with the first 2 interfaces it finds, and obtain an address by DHCP.

* Navigate to the ip of the server or if the server bridges your network to the WAN: http://elan-agent.origin-nexus.com
* Enter the location of the agent and your ELAN center credentials.
* go to `ELAN center <https://elan-center.origin-nexus.com>`_ to manage your agent.
