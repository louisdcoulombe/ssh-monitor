import logging
import socket

# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class LinuxMemoryUsage:

    def __init__(self, host, port, session, path):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.destination = (host, port)
        self.session = session
        self.path = path

    def on_output(self, task, line):
        out = line.split()
        msg = '{}:{}|c\n'.format(self.path + '.memory.free', out[-1])
        msg += '{}:{}|c\n'.format(self.path + '.memory.used', out[-2])
        total = int(out[-1]) + int(out[-2])
        msg += '{}:{}|c'.format(self.path + '.memory.total', total)
        self.sock.sendto(msg, self.destination)
        logger.info('Sent:\n%s', msg)

    def on_swap_output(self, tak, line):
        out = line.split()
        msg = '{}:{}|c\n'.format(self.path + '.memory.swap_free', out[-1])
        msg += '{}:{}|c\n'.format(self.path + '.memory.swap_used', out[-2])
        msg += '{}:{}|c'.format(self.path + '.memory.swap_total', out[-3])
        self.sock.sendto(msg, self.destination)
        logger.info('Sent:\n%s', msg)

    def execute(self):
        self.session.execute('free -m | grep +', on_stdout=self.on_output)
        self.session.execute('free -m | grep Swap',
                             on_stdout=self.on_swap_output)
