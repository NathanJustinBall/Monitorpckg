import peewee
import socket
from threading import Thread
import select
import pika
# import fetch_yaml
import json
import time
import jobs_database
import results_database

# @FIXME currently reading from a yaml file, needs to read from database entryies,
# for user in user databse
# for site in user.get_sites()
# site_args = user.site.args()


class Main:
    def __init__(self):
        database = jobs_database.Main()
        # load jobs
        self.jobs, self.job_names = database.get()
        print(self.jobs)

        # establish connection to rabbit
        creds = pika.credentials.PlainCredentials(username="rabbitmq", password="rabbitmq")
        params = pika.ConnectionParameters("127.0.0.1", 5672, "/", creds)
        connection = pika.BlockingConnection(params)
        self.channel = connection.channel()
        self.channel.queue_declare(queue="jobs")

    def send_to_queue(self):
        for job in range(0, len(self.job_names)):
            send = self.jobs[self.job_names[job]]
            print(job, send)
            self.add_to_queue(json.dumps(send))

    def add_to_queue(self, job):
        print("", job)
        self.channel.basic_publish(exchange='',
                      routing_key='jobs',
                      body=job)


def nested():
    app = Main()

    while True:
        app.send_to_queue()
        time.sleep(1)

nested()
