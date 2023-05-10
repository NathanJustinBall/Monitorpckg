import smtplib


class Main:
    def __init__(self, message, subject, recipient):
        self.server = "smtp.gmail.com"
        self.port = 465
        self.msg = message
        self.sub = subject

        self.data = 'Subject: {}\n\n{}'.format(self.sub, self.msg)
        self.recipient = recipient

        self.user = "mailbot183457@gmail.com"
        self.password = "sDG8h*)GH0wrHJ45HJ)9rH0-W$Rh"
        try:
            self.connection = smtplib.SMTP_SSL(self.server, self.port)
        except:
            print("failed")

    def send(self):
        try:
            self.connection = smtplib.SMTP_SSL(self.server, self.port)
            self.connection.ehlo()
            self.connection.login(self.user, self.password)

            self.connection.sendmail(self.user, self.recipient, self.data)

            self.connection.close()

        except:
            print("break")

