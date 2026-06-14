import os
import json as jsond
import time
import binascii
import platform
import subprocess
import requests
from datetime import datetime, timezone, timedelta


class api:

    name = ownerid = version = hash_to_check = ""

    def __init__(self, name, ownerid, version, hash_to_check):
        if len(ownerid) != 10:
            raise Exception("Invalid owner ID. Visit https://keyauth.cc/app/")
        
        self.name = name
        self.ownerid = ownerid
        self.version = version
        self.hash_to_check = hash_to_check
        self.init()

    sessionid = enckey = ""
    initialized = False

    def init(self):
        if self.sessionid != "":
            raise Exception("Already initialized!")

        post_data = {
            "type": "init",
            "ver": self.version,
            "hash": self.hash_to_check,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        if response == "KeyAuth_Invalid":
            raise Exception("The application doesn't exist")

        json = jsond.loads(response)

        if json["message"] == "invalidver":
            raise Exception("Invalid application version")

        if not json["success"]:
            raise Exception(json["message"])

        self.sessionid = json["sessionid"]
        self.initialized = True

    def login(self, user, password):
        self.checkinit()
        hwid = others.get_hwid()

        post_data = {
            "type": "login",
            "username": user,
            "pass": password,
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid,
        }

        response = self.__do_request(post_data)
        json = jsond.loads(response)

        if json["success"]:
            self.__load_user_data(json["info"])
        else:
            raise Exception(json["message"])

    def checkinit(self):
        if not self.initialized:
            raise Exception("Initialize first")

    def __do_request(self, post_data):
        try:
            response = requests.post(
                "https://keyauth.win/api/1.3/", data=post_data, timeout=10
            )
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    user_data_class = type('user_data_class', (), {
        'username': '', 'ip': '', 'hwid': '', 'expires': '',
        'createdate': '', 'lastlogin': '', 'subscription': '', 'subscriptions': ''
    })
    user_data = user_data_class()

    def __load_user_data(self, data):
        self.user_data.username = data["username"]
        self.user_data.ip = data["ip"]
        self.user_data.hwid = data["hwid"] or "N/A"
        self.user_data.expires = data["subscriptions"][0]["expiry"]
        self.user_data.createdate = data["createdate"]
        self.user_data.lastlogin = data["lastlogin"]
        self.user_data.subscription = data["subscriptions"][0]["subscription"]
        self.user_data.subscriptions = data["subscriptions"]


class others:
    @staticmethod
    def get_hwid():
        if platform.system() == "Linux":
            with open("/etc/machine-id") as f:
                return f.read().strip()
        elif platform.system() == 'Windows':
            return os.getenv('COMPUTERNAME', 'unknown')
        elif platform.system() == 'Darwin':
            output = subprocess.Popen(
                "ioreg -l | grep IOPlatformSerialNumber",
                stdout=subprocess.PIPE, shell=True
            ).communicate()[0]
            serial = output.decode().split('=', 1)[1].replace(' ', '')
            return serial[1:-2]
        return "unknown"
