import string
import random
import requests
import sys
from pymailtm import MailTm, Account
from pymailtm.pymailtm import generate_username, CouldNotGetAccountException


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
                import version  # type: ignore
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

    async def customization(self, tab):
        tab.listen.start('https://avatar.roblox.com/v1/recent-items/all/list')
        tab.get("https://www.roblox.com/my/avatar")
        result = tab.listen.wait()
        content = result.response.body
        assetDict = {}
        for item in content['data']:
            if 'assetType' in item:
                assetType = item["assetType"]["name"]
                if assetType not in assetDict:
                    assetDict[assetType] = []
                assetDict[assetType].append(item)
        tab.listen.stop()

        selectedAssets = {}
        for assetType, assets in assetDict.items():
            selectedAssets[assetType] = random.choice(assets)

        for assetType, asset in selectedAssets.items():
            for z in tab.ele(".hlist item-cards-stackable").eles("tag:li"):
                if z.ele("tag:a").attr("data-item-name") == asset["name"]:
                    z.ele("tag:a").click()
                    break

        bodyType = random.choice([i for i in range(0, 101, 5)])
        tab.run_js_loaded(f'document.getElementById("body type-scale").value = {bodyType};')
        tab.run_js_loaded('document.getElementById("body type-scale").dispatchEvent(new Event("input"));')

    def testProxy(self, proxy):
        try:
            response = requests.get("http://www.google.com", proxies={"http": proxy, "https": proxy}, timeout=5)
            return True, response.status_code
        except Exception:
            return False, "Proxy test failed! Please ensure that the proxy is working correctly. Skipping proxy usage..."

    def generateEmail(self, password="Qing762.chy"):
        if not hasattr(self, 'mailtm'):
            self.mailtm = MailTm()
        domainList = self.mailtm._get_domains_list()
        domain = random.choice(domainList)
        username = generate_username(1)[0].lower()
        address = f"{username}@{domain}"
        while True:
            try:
                emailID = self.mailtm._make_account_request("accounts", address, password)
                break
            except (CouldNotGetAccountException):
                print("Failed to create account. Retrying...")
                continue
        token = requests.post(
            "https://api.mail.tm/token",
            json={"address": address, "password": password}
        ).json()["token"]
        return address, password, token, emailID

    def fetchVerification(self, address=None, password=None, emailID=None):
        if not address or not password or not emailID:
            raise ValueError("Address, password, and emailID must be provided.")
        if not hasattr(self, 'mailtm'):
            self.mailtm = MailTm()
        if not hasattr(self, 'account'):
            self.account = Account(emailID, address, password)
        messages = self.account.get_messages()
        return messages


if __name__ == "__main__":
    print("This is a library file. Please run main.py instead.")
