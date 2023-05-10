import peewee
import datetime
import yaml
from pymysql import *

# default
db_name = None
db_user = None
db_pass = None
db_host = None
db_port = None


class DatabaseConnectionError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return "DatabaseConnectionError, {0}".format(self.message)
        else:
            return "DatabaseConnectionError"


file = open("Config.yml", "r")
data = file.read()

alldata = yaml.load_all(data)
for obj in alldata:
    for item in obj:
        if item == "DB":
            db_name = obj[item]["name"]
            db_user = obj[item]["user"]
            db_pass = obj[item]["pass"]
            db_host = obj[item]["host"]
            db_port = obj[item]["port"]

try:
    myDB = peewee.MySQLDatabase(db_name, user=db_user, passwd=db_pass, host=db_host, port=db_port)
except ConnectionRefusedError("Cannot connect to database"):
    pass


class BaseModel(peewee.Model):
    class Meta:
        database = myDB


class Site(BaseModel):
    id = peewee.IntegerField().auto_increment
    user_id = peewee.IntegerField()
    name = peewee.CharField()
    time = peewee.DateTimeField()
    timeout = peewee.FloatField()
    response_code = peewee.IntegerField()
    site_results = peewee.CharField()
    ishealthy = peewee.BooleanField()


class Main:
    def __init__(self):
        myDB.init(db_name, host=db_host, user=db_user)
        print(myDB.connection_context())

        passer = True
        try:
            myDB.connect()
        except peewee.OperationalError:
            passer = False
            print("Database not open!")

        if passer:
            myDB.create_tables([Site])

    def append(self, name, timeout, response, mark, results=None):
        print(datetime.datetime.now())
        try:
            a = Site.create(name=name, time=datetime.datetime.now(), timeout=timeout, response_code=response, site_results=results, ishealthy=mark)
            a.save()
        except peewee.DatabaseError:
            raise DatabaseConnectionError

    def query_id(self, number):
        j = Site.get(Site.id == number)
        return j

