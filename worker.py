import multiprocessing
import pika
import threading
import time
import sender
import results_database
import urllib.error
import urllib.request
import bs4
import sched
import re
import ast


"""
Begin errors
"""


class RabbitConnectionError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return "RabbitConnectionError, {0}".format(self.message)
        else:
            return "RabbitConnectionError"



"""
End errors
"""


class Alert:
    def __init__(self):
        self.address = None
        self.sendee = None

    def timeout(self, Atime, Etime):
        if self.address is not None:
            print("alerting")
            print(self.address)
            self.send_email(self.address + " took " + str(Atime)+" to load, ("+str(Etime) +
                            ") is your selected limit", self.address+" timed out")

    def error_code(self, code):
        if self.address is not None:
            self.send_email(self.address+" raised error: "+code, self.address+" showed an error code")

    def healthy_now(self):
        self.send_email(self.address+" is now Healthy!", "Health update")

    def set_addr(self, address):
        self.address = address

    def send_email(self, data_to_send, subject):
        mailer = sender.Main(data_to_send, subject, self.sendee)
        mailer.send()


class Analyse:
    def __init__(self):
        self.Database = results_database.Main()
        self.site = None
        self.headers = None
        self.alert = Alert()
        self.timeout = 5
        self.page_data, self.soup = None, None
        self.decoded_page_data = None
        self.page_fetch_time = 0
        self.site_dicts = {}
        self.current_check_site = None
        self.stop_loop = False
        self.sendee = None
        self.site_health = False 

    def get_page(self, page):
        start_time = time.time()

        try:
            req = urllib.request.Request(page, headers={'User-Agent': 'Mozilla/5.0'})

        except AttributeError:
            return None, None

        try:
            page_connect = urllib.request.urlopen(req, timeout=self.timeout)
            end_time = time.time()
            self.page_fetch_time = end_time - start_time

        except urllib.error.HTTPError as http_error:
            print(http_error)
            self.alert.error_code(http_error)
            self.headers = http_error
            return None, None

        except urllib.error.URLError as urlerror:
            print(urlerror)
            self.headers = urlerror
            return None, None

        except TimeoutError:
            self.alert.timeout(self.page_fetch_time, 5)

            return None, None

        try:
            webpage = page_connect.read()
            code = page_connect.getcode()
            self.headers = code
        except TimeoutError:
            print("TTT")
            return None, None

        print(self.current_check_site, "has a response code of", self.headers)
        soup = bs4.BeautifulSoup(webpage, "html.parser")

        return webpage, soup

    def check(self, elements, findstring):
        print(self.current_check_site+" has a page fetch time:", self.page_fetch_time)
        if elements is not None:
            elements_list = elements

            for element in elements_list:
                for item in self.soup.findAll(element):
                    print(item.get_text())

        if findstring is not None:
            for string in findstring:
                matches = re.findall(string, self.decoded_page_data)
                print("'", string, "'", "occured", len(matches), "times")

    def health(self, code, page_loadtime, page_name):
        # load alert engine
        engine = Alert()
        engine.address = page_name["url"]
        engine.sendee = self.sendee

        errorcounter = 0  # reset each time, but is used total errors in health tests
        if code is not None:
            if code is not self.headers:
                errorcounter += 1

                if self.site_health is not True:
                    engine.error_code(self.headers)

        if page_loadtime is not None:
            if self.page_fetch_time >= page_loadtime:
                errorcounter += 1
                if self.site_health is not True:
                    engine.timeout(self.page_fetch_time, page_loadtime)

        if errorcounter >0:
            self.site_health = True
        else:
            if self.site_health is True:
                self.site_health = False
                print("site now healthy")
                engine.healthy_now()

    def start(self, item):
        self.current_check_site = item["url"]
        current_site = item
        self.page_data, self.soup = self.get_page(current_site["url"])
        self.decoded_page_data = self.page_data.decode("utf-8")

        if "elements" in current_site:
            elements = current_site["elements"]
        else:
            elements = None

        if "strings" in current_site:
            strings = current_site["strings"]
        else:
            strings = None

        if "response" in current_site:
            response = current_site["response"]
        else:
            response = None

        if "timeout" in current_site:
            timeout = current_site["timeout"]
        else:
            timeout = None

        self.check(elements, strings)
        self.health(response, timeout, item)

        try:
            self.Database.append(self.current_check_site, self.page_fetch_time, self.headers, self.site_health)
        except results_database.DatabaseConnectionError:
            print("error appending to database")


class Worker:
    def __init__(self):
        # connect to pika
        # establish connection to rabbit
        self.anylyser = Analyse()

        self.channel = None

    def init_pika_connection(self):
        creds = pika.credentials.PlainCredentials(username="rabbitmq", password="rabbitmq")
        params = pika.ConnectionParameters("127.0.0.1", 5672, "/", creds)
        try:
            connection = pika.BlockingConnection(params)
        except pika.exceptions.AMQPConnectionError:
            raise RabbitConnectionError

        self.channel = connection.channel()
        self.channel.queue_declare(queue="jobs")

    def callback(self, ch, method, properties, body):
        print(" [x] Received %r" % body)

        self.anylyser.start(body)

    def get_stream(self):
        print("grabbing")

        for method_frame, properties, body in self.channel.consume("jobs"):
            # Display the message parts
            decoded = ast.literal_eval(body.decode("utf-8"))
            print(decoded)
            self.anylyser.start(decoded)
            print(decoded["url"])
            self.channel.basic_ack(method_frame.delivery_tag)
            # breaks after first ack
            break
        self.channel.cancel()


if __name__ == "__main__":
    a = Worker()
    # looper
    rabbit_connection = False

    while rabbit_connection is False:
        try:
            a.init_pika_connection()
            rabbit_connection = True
        except RabbitConnectionError:
            print("Rabbit connection failed")
            rabbit_connection = False

        time.sleep(1)

    while True:
        a.get_stream()
        # time.sleep(1)
