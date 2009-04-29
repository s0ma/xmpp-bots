import ConfigParser
import inspect
import jabberbot
import xmlrpclib

class SupervisorBot(jabberbot.JabberBot):

    def __init__(self, jid, password, authorized, serverurl):
        super(SupervisorBot, self).__init__(jid, password, authorized)
        self.serverurl = serverurl
        self.cnn       = xmlrpclib.ServerProxy(self.serverurl)

    def get_supervisor(self):
        return self.cnn.supervisor

    def split_namespec(self, namespec):
        names = namespec.split(':', 1)

        if len(names) == 2:
            group_name, process_name = names
            if not process_name or process_name == '*':
                process_name = None
            return group_name, process_name

        return namespec, namespec

    def handle_message(self, message):
        return self.do_help()

    def do_help(self, *args):
        # Show help for a specific command.
        if len(args) > 0:
            cmd = 'help_' + args[0].lower()
            if hasattr(self, cmd):
                return getattr(self, cmd)()

        # Show help overview.
        commands = [name[3:] for name, value in inspect.getmembers(self)
                             if inspect.ismethod(value)
                             if name.startswith('do_')]
        commands.sort()
        commands.insert(0, 'available commands:');

        return "\n\t".join(commands)

    def do_tail(self, *args):
        if len(args) < 1:
            return 'Error: too few arguments'
        if len(args) > 3:
            return 'Error: too many arguments'

        bytes = 1600
        if args[0].startswith('-'):
            try:
                bytes = int(args[0][1:])
                args.pop(0)
            except:
                return 'Error: bad argument %s' % args[0]

        if len(args) == 1:
            name    = args[-1]
            channel = 'stdout'
        elif len(args) == 2:
            name    = args[0]
            channel = args[1].lower()
            if channel not in ('stderr', 'stdout'):
                return 'Error: bad channel %r' % channel
        else:
            return 'Error: tail requires process name'

        try:
            if channel is 'stdout':
                return self.get_supervisor().readProcessStdoutLog(name, -bytes, 0)
            else:
                return self.get_supervisor().readProcessStderrLog(name, -bytes, 0)
        except xmlrpclib.Fault, e:
            template = '%s: ERROR (%s)'
            if e.faultCode == xmlrpc.Faults.NO_FILE:
                return template % (name, 'no log file')
            if e.faultCode == xmlrpc.Faults.FAILED:
                return template % (name, 'unknown error reading log')
            if e.faultCode == xmlrpc.Faults.BAD_NAME:
                return template % (name, 'no such process name')

        return ''

    def help_tail(self):
        return "\n".join(["tail -100 <name>\tlast 100 *bytes* of process stdout",
                          "tail <name> stderr\tlast 1600 *bytes* of process stderr"])

    def do_maintail(self, *args):
        if len(args) > 1:
            return 'Error: too many arguments'

        bytes = 1600
        if args[0].startswith('-'):
            try:
                what = int(args[0][1:])
                args.pop(0)
            except:
                return 'Error: bad argument %s' % args[0]

        try:
            return self.get_supervisor().readLog(-bytes, 0)
        except xmlrpclib.Fault, e:
            template = '%s: ERROR (%s)'
            if e.faultCode == xmlrpc.Faults.NO_FILE:
                return template % ('supervisord', 'no log file')
            if e.faultCode == xmlrpc.Faults.FAILED:
                return template % ('supervisord', 'unknown error reading log')

        return ''

    def help_maintail(self):
        return "\n".join(["maintail -100\tlast 100 *bytes* of supervisord main log file",
                          "maintail\tlast 1600 *bytes* of supervisor main log file"])

    def do_status(self, *names):
        retval = []
        if len(names) == 0:
            retval.extend(self.get_supervisor().getAllProcessInfo())
        else:
            for name in names:
                try:
                    retval.append(self.get_supervisor().getProcessInfo(name))
                except xmlrpclib.Fault, e:
                    if e.faultCode == xmlrpc.Faults.BAD_NAME:
                        retval.append('No such process %s' % name)
                    continue

        return "\n".join([self._procrepr(r) for r in retval])

    def help_status(self):
        return "\n".join(["status\t\t\tGet all process status info.",
                          "status <name>\t\tGet status on a single process by name.",
                          "status <name> <name>\tGet status on multiple named processes."])

    def _procrepr(self, info):
        template = '%(name)-32s %(state)-10s %(desc)s'
        if info['name'] == info['group']:
            name = info['name']
        else:
            name = '%s:%s' % (info['group'], info['name'])

        return template % {'name':name, 'state':info['statename'], 'desc':info['description']}

    def do_start(self, *names):
        if len(names) == 0:
            return "Error: start requires a process name"

        retval = []
        if 'all' in names:
            retval.extend(self.get_supervisor().startAllProcesses())
        else:
            for name in names:
                group_name, process_name = self.split_namespec(name)
                if process_name is None:
                    results.extend(self.get_supervisor().startProcessGroup(group_name))
                else:
                    try:
                        self.get_supervisor().startProcess(name)
                    except xmlrpclib.Fault, e:
                        retval.append(
                            dict(status = e.faultCode, name = name, description = e.faultString))
                    else:
                        retval.append('%s: started' % name)

        return "\n".join([self.encode_result(r) for r in retval])

    def help_start(self):
        return "\n".join(["start <name>\t\tStart a process",
                          "start <gname>:*\t\tStart all processes in a group",
                          "start <name> <name>\tStart multiple processes or groups",
                          "start all\t\tStart all processes"])

    def do_stop(self, *names):
        if len(names) == 0:
            return 'Error: stop requires a process name'

        retval = []
        if 'all' in names:
            retval.extend(self.get_supervisor().stopAllProcesses())
        else:
            for name in names:
                group_name, process_name = self.split_namespec(name)
                if process_name is None:
                    retval.extend(self.get_supervisor().stopProcessGroup(group_name))
                else:
                    try:
                        self.get_supervisor().stopProcess(name)
                    except xmlrpclib.Fault, e:
                        retval.append(
                            dict(status = e.faultCode, name = name, description = e.faultString))
                    else:
                        retval.append('%s: stopped' % name)

        return "\n".join([self.encode_result(r) for r in retval])

    def help_stop(self):
        return "\n".join(["stop <name>\t\tStop a process",
                          "stop <gname>:*\t\tStop all processes in a group",
                          "stop <name> <name>\tStop multiple processes or groups",
                          "stop all\t\tStop all processes"])

    def do_restart(self, *names):
        if len(names) == 0:
            return 'Error: restart requires a process name'

        return "\n".join([self.do_stop(*names), self.do_start(*names)])

    def help_restart(self):
        return "\n".join(["restart <name>\t\tRestart a process",
                          "restart <gname>:*\tRestart all processes in a group",
                          "restart <name> <name>\tRestart multiple processes or groups",
                          "restart all\t\tRestart all processes"])

    def do_clear(self, *names):
        if len(names) == 0:
            return 'Error: clear requires a process name'

        retval = []
        if 'all' in names:
            retval.extend(self.get_supervisor().clearAllProcessLogs())
        else:
            for name in names:
                try:
                    self.get_supervisor().clearProcessLogs(name)
                except xmlrpclib.Fault, e:
                    retval.append(
                        dict(status = e.faultCode, name = name, description = e.faultString))
                else:
                    retval.append('%s: cleared' % name)

        return "\n".join([self.encode_result(r) for r in retval])

    def help_clear(self):
        return "\n".join(["clear <name>\t\tClear a process' log files.",
                          "clear <name> <name>\tClear multiple process' log files",
                          "clear all\t\tClear all process' log files"])

    def encode_result(self, result):
        if result.__class__ in (str, unicode):
            return result

        name = result['name']
        code = result['status']
        template = '%s: ERROR (%s)'
        
        if code == xmlrpc.Faults.ABNORMAL_TERMINATION:
            return template % (name, 'abnormal termination')
        
        if code == xmlrpc.Faults.ALREADY_STARTED:
            return template % (name,'already started')

        if code == xmlrpc.Faults.BAD_NAME:
            return template % (name, 'no such process')

        if code == xmlrpc.Faults.FAILED:
            return template % (name, getattr(result, 'description', 'failed'))

        if code == xmlrpc.Faults.NOT_RUNNING:
            return template % (name, 'not running')

        if code == xmlrpc.Faults.SUCCESS:
            return '%s: success' % name
        
        if code == xmlrpc.Faults.SPAWN_ERROR:
            return template % (name, 'spawn error')

        return 'Unknown result code %s for %s' % (code, name)

    def do_shutdown(self, *args):
        try:
            self.get_supervisor().shutdown()
        except xmlrpclib.Fault, e:
            if e.faultCode == xmlrpc.Faults.SHUTDOWN_STATE:
                return 'ERROR: already shutting down'
        else:
            return 'Shut down'

    def help_shutdown(self):
        return "shutdown \tShut the remote supervisord down."

    def do_reload(self, *args):
        try:
            self.get_supervisor().restart()
        except xmlrpclib.Fault, e:
            if e.faultCode == xmlrpc.Faults.SHUTDOWN_STATE:
                return 'ERROR: already shutting down'
        else:
            return 'Restarted supervisord'

    def help_reload(self):
        return "reload \t\tRestart the remote supervisord."

    def do_version(self, *args):
        return self.get_supervisor().getSupervisorVersion()

    def help_version(self):
        return "version\t\t\tShow the version of the remote supervisord process"


if __name__ == '__main__':
    config = ConfigParser.ConfigParser()
    config.read(['etc/supervisorbot.cfg', 'supervisorbot.cfg'])

    bot = SupervisorBot(config.get('supervisorbot', 'username'),
                        config.get('supervisorbot', 'password'),
                        eval(config.get('supervisorbot', 'authorized')),
                        config.get('supervisorbot', 'serverurl'))
    bot.run()
