import urllib.error
import urllib.request
import bs4
import time
import sched
import re
import sender
import yaml
import results_database


class Main:
    def __init__(self, data):
        self.site = None
        self.data = data

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
        self.looper = sched.scheduler(time.time, time.sleep)
        self.interval = 0

        self.site_names = []

        self.db_user = ""
        self.db_pass = ""
        self.db_host = ""
        self.db_port = 0
        self.load_yaml()

        self.page_code = 0

        self.site_health = {}
        for site in self.site_names:
            self.site_health[site] = False

        self.Database = results_database.Main()

        self.looper.enter(self.interval, 1, self.loop, (self.looper, ))
        self.looper.run()

    def load_yaml(self):
        alldata = yaml.load_all(self.data)
        self.site = alldata
        for site in self.site:
            self.site_dicts.update(site)

            print("LOADING YAML")
            for item in site:
                if item == "SETUP":
                    self.interval = site[item]["interval"]
                    self.sendee = site[item]["sendee"]
                elif item == "DB":
                    self.db_user = site[item]["user"]
                    self.db_pass = site[item]["pass"]
                    self.db_host = site[item]["host"]
                    self.db_port = site[item]["port"]

                else:
                    self.site_names.append(item)

        print("YAML LOADED")

    def get_page(self, page):
        start_time = time.time()

        req = urllib.request.Request(page, headers={'User-Agent': 'Mozilla/5.0'})

        try:
            page_connect = urllib.request.urlopen(req, timeout=self.timeout)
            end_time = time.time()
            self.page_fetch_time = end_time - start_time

        except urllib.error.HTTPError as http_error:
            print(http_error)
            self.alert.error_code(http_error)
            self.headers = http_error
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
        engine.address = page_name
        engine.sendee = self.sendee

        errorcounter = 0  # reset each time, but is used total errors in health tests
        if code is not None:
            if code is not self.headers:
                errorcounter += 1

                if self.site_health[self.current_check_site] is not True:
                    engine.error_code(self.headers)

        if page_loadtime is not None:
            if self.page_fetch_time >= page_loadtime:
                errorcounter += 1
                if self.site_health[self.current_check_site] is not True:
                    engine.timeout(self.page_fetch_time, page_loadtime)

        if errorcounter >0:
            self.site_health[self.current_check_site] = True
        else:
            if self.site_health[self.current_check_site] is True:
                self.site_health[self.current_check_site] = False
                print("site now healthy")
                engine.healthy_now()

    def loop(self, sc):
        for item in self.site_names:
            self.current_check_site = item
            current_site = self.site_dicts[item]
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

            # store to DB
            self.Database.append(self.current_check_site, self.page_fetch_time, self.headers, self.site_health[self.current_check_site])

            # break a gap
            print("")

        print("reloop")
        self.looper.enter(self.interval, 1, self.loop, (sc, ))


class Alert:
    def __init__(self):
        self.address = None
        self.sendee = None

    def timeout(self, Atime, Etime):
        if self.address is not None:
            print("alerting")
            self.send_email(self.address + " took " + str(Atime)+" to load, ("+str(Etime)+") is your selected limit", self.address+" timed out")

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


class Start:
    def __init__(self):
        file = open("Config.yml", "r")
        data = file.read()

        app = Main
        app(data)


if __name__ == "__main__":
    app = Start
    app()
