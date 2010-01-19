import os, os.path

__PASSWD_FILE = '.sqlpasswd'

class Configuration:
    def __init__(self, username, password, host="anoko", database="anoko", driver=None, kargs=False):
        if not driver: raise Exception("No driver!")
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        self.driver = driver
        self.drivername = driver.__name__
        self.kargs = kargs

    def connect(self, *args, **kargs):
        if self.kargs:
            return self.driver.connect("DSN=%s" % self.host, user=self.username, password=self.password, *args, **kargs)
        else:
            return self.driver.connect(self.host, self.username, self.password, *args, **kargs)
        
def default(**kargs):
    homedir = os.getenv('HOME')

    if not homedir:
        if 'SERVER_SOFTWARE' in os.environ:
            return amcatConfig()
        raise Exception('Could not determine home directory! Please specify the HOME environemnt variable')
    passwdfile = os.path.join(homedir, __PASSWD_FILE)
    if not os.access(passwdfile, os.R_OK):
        raise Exception('Could not find or read password file in "%s"!' % passwdfile)

    fields = open(passwdfile).read().strip().split(':')
    un, password = fields[:2]
    if os.name == 'nt':
        raise Exception("Windows currently not supported -- ask Wouter!")
    else:
        return amcatConfig(un, password,  **kargs)

def amcatConfig(username = "app", password = "eno=hoty", easysoft=False):
    
    if easysoft:
        host = "Easysoft-AmcatDB"
        import pyodbc as driver
        import dbtoolkit
        dbtoolkit.ENCODE_UTF8 = True
    else:
        host = "AmcatDB"
        import mx.ODBC.iODBC as driver
    return Configuration(username, password, host, driver=driver, kargs=easysoft)

if __name__ == '__main__':
    c = default()
    print "Config: host %s, username %s, passwd %s.., attempting to connect" % (c.host, c.username, c.password[:2])
    db = c.connect()
    print db
