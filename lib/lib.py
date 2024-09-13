import string
import random
import time
from requests_html import HTMLSession


class Main():
    def get_random_string(self, length):
        letters = string.ascii_lowercase
        return "".join(random.choice(letters) for i in range(length))

    def usernamecreator(self):
        while True:
            characters = string.ascii_letters + string.digits + '._-'
            username = ''.join(random.choice(characters) for _ in range(random.randint(5, 32)))
            request = HTMLSession()
            r = request.get(
                f"https://auth.roblox.com/v2/usernames/validate?request.username={username}&request.birthday=04%2F15%2F02&request.context=Signup"
            ).json()
            if r["code"] == 0:
                return username
            else:
                continue

if __name__ == "__main__":
    print("This is a library file. Please run main.py instead.")
