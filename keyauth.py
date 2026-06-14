# keyauth.py - Lightweight version for Linux
import requests
import json
import time

class api:
    def __init__(self, name, ownerid, version, hash_to_check=""):
        self.name = name
        self.ownerid = ownerid
        self.version = version
        self.hash_to_check = hash_to_check
        self.session_id = None
        
    def login(self, username, password):
        url = "https://keyauth.win/api/1.2/"
        data = {
            "type": "login",
            "username": username,
            "password": password,
            "name": self.name,
            "ownerid": self.ownerid,
            "version": self.version,
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            if result.get("success"):
                self.session_id = result.get("sessionid")
                return True
            else:
                raise Exception(result.get("message", "Login failed"))
        except Exception as e:
            print(f"[KeyAuth] Error: {e}")
            raise
