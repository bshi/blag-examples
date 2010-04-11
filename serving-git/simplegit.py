#!/usr/bin/env python
import os
import sys
from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
from twisted.conch.avatar import ConchUser
from twisted.conch.ssh.session import SSHSession, ISession
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.cred.portal import IRealm, Portal
from twisted.internet import reactor
from twisted.python import components, log
from zope import interface
log.startLogging(sys.stderr)


def find_git_shell():
    # Find git-shell path.
    # Adapted from http://bugs.python.org/file15381/shutil_which.patch
    path = os.environ.get("PATH", os.defpath)
    for dir in path.split(os.pathsep):
        full_path = os.path.join(dir, 'git-shell')
        if (os.path.exists(full_path) and 
                os.access(full_path, (os.F_OK | os.X_OK))):
            return full_path
    raise Exception('Could not find git executable!')


class GitConchUser(ConchUser):
    shell = find_git_shell()

    def __init__(self, username):
        ConchUser.__init__(self)
        self.username = username
        self.channelLookup.update({"session": SSHSession})

    def logout(self): pass


class SimpleGitSession(object):
    interface.implements(ISession)

    def __init__(self, user):
        self.user = user

    def execCommand(self, proto, cmd):
        command = (self.user.shell, '-c', cmd)
        reactor.spawnProcess(proto, self.user.shell, command)

    def eofReceived(self): pass

    def closed(self): pass


class GitRealm(object):
    interface.implements(IRealm)

    def requestAvatar(self, username, mind, *interfaces):
        user = GitConchUser(username)
        return interfaces[0], user, user.logout


class SimpleGitServer(SSHFactory):
    portal = Portal(GitRealm())

    mockpasswd = InMemoryUsernamePasswordDatabaseDontUse()
    mockpasswd.addUser('bshi', 'bshi')
    portal.registerChecker(mockpasswd)

    def __init__(self, privkey):
        pubkey = '.'.join((privkey, 'pub'))
        self.privateKeys = {'ssh-rsa': Key.fromFile(privkey)}
        self.publicKeys = {'ssh-rsa': Key.fromFile(pubkey)}


if __name__ == '__main__':
    components.registerAdapter(SimpleGitSession, GitConchUser, ISession)
    reactor.listenTCP(2222, SimpleGitServer(sys.argv[1]))
    reactor.run()
