#!/usr/bin/env python
import os
import shlex
import sys
from twisted.conch.avatar import ConchUser
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.conch.error import ConchError
from twisted.conch.ssh import common
from twisted.conch.ssh.session import (ISession,
                                       SSHSession,
                                       SSHSessionProcessProtocol)
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.cred.portal import IRealm, Portal
from twisted.internet import reactor
from twisted.python import components, log
from zope import interface
log.startLogging(sys.stderr)


class IGitMetadata(interface.Interface):
    'API for authentication and access control.'

    def repopath(self, username, reponame):
        '''
        Given a username and repo name, return the full path of the repo on
        the file system.
        '''

    def pubkeys(self, username):
        '''
        Given a username return a list of OpenSSH compatible public key
        strings.
        '''

BSHIPK = r'ssh-dss AAAAB3NzaC1kc3MAAACBAJW6g6QMZ7n7SJG3WBUcMTlgYJiuX61CPOMQj0F3srftuB81T5Y7r7T72zsov81crIi+PU5GRO80Umhu68nSPQmfXmYzkqNgU0XFHXuZXYnCW9l6hxn94Qr+XBPZMLwHUQvVzaFneFuFXS0Lx3iKa3HH43OOCjDkDnLVx39rvvUdAAAAFQCEBsryZKy+t8iNwGjKd4Q34F2T/wAAAIAV0CwoJHYCks4WXKTOLA080JaeFwBQEBJZgi5itrHMZJpISPQNrXV7EUTTMYLk5m4rWdiWYX24Witbu8VBwrRW8FMqLpd1x5fXvJrfqFxcJryASl6fCM3PVSmRgRMiJ1MyqKfovjur959k7LEtQsMEDgMnDgBwawHy8t38fMA7rwAAAIAEqVDoUOoZHr6l0Q/I+YpbZiCj1c6Ny5tfl+fy5bt2Ab6I7R3bUMUM2I5ycpGgFpIU96JiXbA35ga7VXOCn5qmAOjOk4DtmGIomi+z4k6kViQr1IFAb366Dyh/CV/Dkm7b9klugjZW/xsiBibS5kgTD1eFxbvvW10a8+8iJLgoiQ== bshi@Bo-Shis-MacBook-Pro.local'

class BallinMockMeta(object):
    'Mock persistence layer.'
    interface.implements(IGitMetadata)
    # To test, you need to fill in pubkeys sequences with real public keys.
    def __init__(self):
        self.db = {
            'jane': {
                'pubkeys': ('a', 'b'),
                'repos': {
                    '/foobar.git': '/path/to/foobar.git',
                    '/project.git': '/path/to/project.git',
                },
            },
            'john': {
                'pubkeys': ('c', 'd'),
                'repos': {
                    '/helloworld.git': '/path/to/helloworld.git',
                },
            },
            'bshi': {
                'pubkeys': (BSHIPK,),
                'repos': {
                    '/poop.git': '/Users/bshi/sandbox/poop/',
                },
            }
        }

    def repopath(self, username, reponame):
        if username not in self.db:
            return None
        return self.db[username]['repos'].get(reponame, None)

    def pubkeys(self, username):
        if username not in self.db:
            return None
        return self.db[username]['pubkeys']


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


class GitSession(object):
    interface.implements(ISession)

    def __init__(self, user):
        self.user = user

    def execCommand(self, proto, cmd):
        argv = shlex.split(cmd)
        reponame = argv[-1]
        sh = self.user.shell

        # Check permissions by mapping requested path to file system path
        repopath = self.user.meta.repopath(self.user.username, reponame)
        if repopath is None:
            raise ConchError('Invalid repository.')
        command = ' '.join(argv[:-1] + ["'%s'" % (repopath,)])
        reactor.spawnProcess(proto, sh,(sh, '-c', command))

    def eofReceived(self): pass

    def closed(self): pass


class GitConchUser(ConchUser):
    shell = find_git_shell()

    def __init__(self, username, meta):
        ConchUser.__init__(self)
        self.username = username
        self.channelLookup.update({"session": SSHSession})
        self.meta = meta

    def logout(self): pass


class GitRealm(object):
    interface.implements(IRealm)

    def __init__(self, meta):
        self.meta = meta

    def requestAvatar(self, username, mind, *interfaces):
        user = GitConchUser(username, self.meta)
        return interfaces[0], user, user.logout


class GitPubKeyChecker(SSHPublicKeyDatabase):
    def __init__(self, meta):
        self.meta = meta

    def checkKey(self, credentials):
        for k in self.meta.pubkeys(credentials.username):
            if Key.fromString(k).blob() == credentials.blob:
                return True
        return False


class GitServer(SSHFactory):
    authmeta = BallinMockMeta()
    portal = Portal(GitRealm(authmeta))
    portal.registerChecker(GitPubKeyChecker(authmeta))

    def __init__(self, privkey):
        pubkey = '.'.join((privkey, 'pub'))
        self.privateKeys = {'ssh-rsa': Key.fromFile(privkey)}
        self.publicKeys = {'ssh-rsa': Key.fromFile(pubkey)}


if __name__ == '__main__':
    components.registerAdapter(GitSession, GitConchUser, ISession)
    reactor.listenTCP(2222, GitServer(sys.argv[1]))
    reactor.run()
