import configparser


class Config:
    def __init__(self):
        # read the config file first
        self.cfile = configparser.RawConfigParser()
        self.cfile.read("/etc/snapgene-server/snapgene-server.conf")

    # lookup the tcp port to use for a particular server index.  If
    # the port is not specified or if enable=0, then 0 is returned.
    def lookup_port(self, server_index):
        sectionName = "server%s" % server_index

        # see if the server is enabled
        if not self.cfile.has_section(sectionName):
            raise Exception(
                "server index %s is not defined in configuration file" % server_index
            )

        if (
            not self.cfile.has_option(sectionName, "enable")
            or self.cfile.getint(sectionName, "enable") == 0
        ):
            raise Exception("server index %s is disabled" % server_index)

        # get the tcp port
        if not self.cfile.has_option(sectionName, "tcpPort"):
            raise Exception("server index %s does not define a tcpPort" % server_index)

        return self.cfile.getint(sectionName, "tcpPort")

    # Returns the list of enabled servers specified in the configuration file.
    def get_server_ports(self):
        ret = dict()
        for i in range(1, 100):
            sectionName = "server%s" % i
            if (
                self.cfile.has_section(sectionName)
                and (
                    not self.cfile.has_option(sectionName, "enable")
                    or self.cfile.getint(sectionName, "enable") != 0
                )
                and self.cfile.has_option(sectionName, "tcpPort")
            ):
                ret[i] = self.cfile.getint(sectionName, "tcpPort")
        return ret


# prase the pidfile
# pidfileDir = config.get("common","pidfileDir");
# print "dir is %s " % pidfileDir;
