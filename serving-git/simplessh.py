#!/usr/bin/env python
import sys
from twisted.cred.portal import Portal
from twisted.conch import checkers
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.conch.unix import UnixSSHRealm
from twisted.internet import reactor
from twisted.python import log
log.startLogging(sys.stderr)

class SSHServer(SSHFactory):
    'Simulate an OpenSSH server.'
    portal = Portal(UnixSSHRealm())
    portal.registerChecker(checkers.UNIXPasswordDatabase())
    # Doesn't work in version 9.0.0; fixed in trunk.
    portal.registerChecker(checkers.SSHPublicKeyDatabase())

    def __init__(self, privkey):
        pubkey = '.'.join((privkey, 'pub'))
        self.privateKeys = {'ssh-rsa': Key.fromFile(privkey)}
        self.publicKeys = {'ssh-rsa': Key.fromFile(pubkey)}

if __name__ == '__main__':
    reactor.listenTCP(2222, SSHServer(sys.argv[1]))
    reactor.run()
