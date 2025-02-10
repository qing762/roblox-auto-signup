import string
import random
import requests
import sys


class Main():
    def usernamecreator(self, nameFormat=None):
        counter = 0
        while True:
            if nameFormat:
                username = f"{nameFormat}_{counter}"
                counter += 1
            else:
                characters = string.ascii_letters + string.digits + '._-'
                username = ''.join(random.choice(characters) for _ in range(random.randint(5, 32)))
            
            r = requests.get(
                f"https://auth.roblox.com/v2/usernames/validate?request.username={username}&request.birthday=04%2F15%2F02&request.context=Signup"
            ).json()
            
            if r["code"] == 0:
                return username
            else:
                continue

    async def checkUpdate(self):
        try:
            resp = requests.get(
                "https://api.github.com/repos/qing762/roblox-auto-signup/releases/latest"
            )
            latestVer = resp.json()["tag_name"]

            if getattr(sys, 'frozen', False):
                import version
                currentVer = version.__version__
            else:
                with open("version.txt", "r") as file:
                    currentVer = file.read().strip()

            if currentVer < latestVer:
                print(f"Update available: {latestVer} (Current version: {currentVer})\nYou can download the latest version from: https://github.com/qing762/roblox-auto-signup/releases/latest")
            else:
                print(f"You are running the latest version: {currentVer}")
                pass
        except Exception as e:
            print(f"An error occurred: {e}")
            pass

    async def checkPassword(self, username, password):
        token = requests.post("https://auth.roblox.com/v2/login", headers={"User-Agent": "Mozilla/5.0"}).headers.get("x-csrf-token")
        data = {
            "username": username,
            "password": password
        }
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.6",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://www.roblox.com",
            "referer": "https://www.roblox.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "x-csrf-token": token
        }
        resp = requests.post("https://auth.roblox.com/v2/passwords/validate", json=data, headers=headers).json()
        if resp["code"] == 0:
            return "\nPassword is valid"
        else:
            return f"\nPassword does not meet the requirements: {resp['message']}"


if __name__ == "__main__":
    print("This is a library file. Please run main.py instead.")
