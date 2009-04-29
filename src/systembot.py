import ConfigParser
import jabberbot
import os
import re

class SystemBot(jabberbot.JabberBot):
    def __init__(self, jid, password, authorized, commands):
        super(SystemBot, self).__init__(jid, password, authorized)
        self.commands = commands

    def run_command(self, command):
        pipe   = os.popen(command, 'r')
        result = pipe.read().strip()
        pipe.close()
        return result

    def do_help(self, *args):
        commands = [k + ': ' + v for k, v in self.commands.items()]
        commands.append('help')
        commands.sort()
        commands.insert(0, 'available commands:')
        return "\n\t".join(commands)

    def handle_message(self, message):
        args = message.split()
        cmd  = args[0].lower()

        if self.commands.has_key(cmd):
            args[0] = self.commands[cmd]
            return self.run_command(' '.join(args))
        else:
            return self.do_help()


if __name__ == '__main__':
    config = ConfigParser.ConfigParser()
    config.read(['etc/systembot.cfg', 'systembot.cfg'])

    bot = SystemBot(config.get('systembot', 'username'),
                    config.get('systembot', 'password'),
                    eval(config.get('systembot', 'authorized')),
                    dict(config.items('commands')))
    bot.run()
