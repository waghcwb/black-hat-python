# not ready for use ..

import getpass
import paramiko
import sys
import threading
import socket
import select

if __name__ == '__main__':
    def handler(chan, host, port):
        sock = socket.socket()

        try:
            sock.connect((host, port))
        except Exception as error:
            verbose('Forwarding request to {host}:{port} failed: {error}'.format(host=host, port=port, error=error))
            return

        verbose('Connected! Tunnel open {origin_addr} -> {peer_name} -> {host}'.format(origin_addr=chan.origin_addr,
                                                                                       peer_name=chan.getpeername(),
                                                                                       host=(host, port)))

        while True:
            r, w, x = select.select([sock, chan], [], [])

            if sock in r:
                data = sock.recv(1024)

                if len(data) == 0:
                    break

                chan.send(data)

            if chan in r:
                data = chan.recv(1024)

                if len(data) == 0:
                    break

                sock.send(data)

        chan.close()
        sock.close()

        verbose('Tunnel closed from {origin_addr}'.format(origin_addr=chan.origin_addr))

    def reverse_forward_tunnel(server_port, remote_host, remote_port, transport):
        transport.request_port_forward('', server_port)

        while True:
            chan = transport.accept(1000)

            if chan is None:
                continue

            thr = threading.Thread(target=handler, args=(chan, remote_host, remote_port))
            thr.setDaemon(True)
            thr.start()

    def main():
        options, server, remote = parse_options()
        password = None

        if options.readpass:
            password = getpass.getpass('Enter SSH password: ')

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())

        verbose('Connecting to ssh host {host}:{port} ...'.format(host=server[0], port=server[1]))

        try:
            client.connect(server[0], server[1], username=options.user, key_filename=options.keyfile,
                           look_for_keys=options.look_for_keys, password=password)
        except Exception as error:
            print('*** Failed to connect to {host}:{port}: {error}'.format(host=server[0], port=server[1], error=error))
            sys.exit(1)

        verbose('Now forwading remote port {port} to {host}:{host_port} ...'.format(host=options.port, port=remote[0],
                                                                                    host_port=remote[1]))

        try:
            reverse_forward_tunnel(options.port, remote[0], remote[1], client.get_transport())
        except KeyboardInterrupt:
            print('C-c: Port forwarding stopped.')
            sys.exit(0)