import random
import requests
import sys
import uuid
import time
import hmac
import os
import hashlib
from pymailtm import MailTm, Account

class UsernameGenerator:
    # SOURCE: https://github.com/mrsobakin/pungen. Kudos to mrsobakin for the original code.
    CONSONANTS = "bcdfghjklmnpqrstvwxyz"

    CONS_WEIGHTED = ("tn", "rshd", "lfcm", "gypwb", "vbjxq", "z")
    VOW_WEIGHTED = ("eao", "iu")
    DOUBLE_CONS = ("he", "re", "ti", "ti", "hi", "to", "ll", "tt", "nn", "pp", "th", "nd", "st", "qu")
    DOUBLE_VOW = ("ee", "oo", "ei", "ou", "ai", "ea", "an", "er", "in", "on", "at", "es", "en", "of", "ed", "or", "as")


    def __init__(self, min_length, max_length=None):
        self.set_length(min_length, max_length)

    
    def set_length(self, min_length, max_length):
        if not max_length:
            max_length = min_length
            
        self.min_length = min_length
        self.max_length = max_length
    
    
    def generate(self):
        username, is_double, num_length = "", False, 0  # reset variables
        
        if random.randrange(10) > 0:
            is_consonant = True
        else:
            is_consonant = False

        # pick a random length for this username given the ranges
        length = random.randrange(self.min_length, self.max_length+1)

        if random.randrange(5) == 0:  # decide if there will be numbers after the name
            num_length = random.randrange(3) + 1
            if length - num_length < 2:  # we don't want the username to be too short
                num_length = 0

        for j in range(length - num_length):  # we leave room for the numbers after the name here
            if len(username) > 0:
                if username[-1] in self.CONSONANTS:
                    is_consonant = False
                elif username[-1] in self.CONSONANTS:
                    is_consonant = True
            if not is_double:  # if the last character was a double, skip a letter
                # 1 in 8 chance of doubling if username is still short enough
                if random.randrange(8) == 0 and len(username) < int(length - num_length) - 1:
                    is_double = True  # this character will be doubled
                if is_consonant:
                    username += self._get_consonant(is_double)  # add consonant to username
                else:
                    username += self._get_vowel(is_double)  # add vowel to username
                is_consonant = not is_consonant  # swap consonant/vowel value for next time
            else:
                is_double = False  # reset double status so the next letter won't be skipped
        if random.randrange(2) == 0:
            # this was the best method I could find to only capitalize the first letter in Python 3
            username = username[:1].upper() + username[1:]
        if num_length > 0:
            for j in range(num_length):  # loop 1 - 3 times
                username += str(random.randrange(10))  # append a random number, 0 - 9
        
        return username
    
    
    def _get_consonant(self, is_double):
        if is_double:
            return random.choice(self.DOUBLE_CONS)  # add two consonants from our pre-defined tuple
        else:
            # we're just guessing at some good weights here. This is how more common letters get used more
            i = random.randrange(100)
            if i < 40:
                weight = 0
            elif 65 > i >= 40:
                weight = 1
            elif 80 > i >= 65:
                weight = 2
            elif 90 > i >= 80:
                weight = 3
            elif 97 > i >= 90:
                weight = 4
            else:
                # the last group is Z by itself. No point in going through extra code when we can finish it here
                return self.CONS_WEIGHTED[5]
            # return a random consonant based on the weight
            return self.CONS_WEIGHTED[weight][random.randrange(len(self.CONS_WEIGHTED[weight]))]


    def _get_vowel(self, is_double):
        if is_double:
            return random.choice(self.DOUBLE_VOW)  # add two vowels from our pre-defined tuple
        else:
            i = random.randrange(100)
            if i < 70:
                weight = 0
            else:
                weight = 1
            # return a random vowel based on the weight
            return self.VOW_WEIGHTED[weight][random.randrange(len(self.VOW_WEIGHTED[weight]))]

class Main():
    def usernameCreator(self, nameFormat=None, scrambled=False):
        counter = 0
        while True:
            if nameFormat:
                username = f"{nameFormat}_{counter}"
                counter += 1
            else:
                if scrambled is True:
                    username = self.generateUsername(scrambled=True)
                else:
                    username = self.generateUsername(scrambled=False)

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
                return currentVer
            else:
                print(f"You are running the latest version: {currentVer}")
                return currentVer
        except Exception as e:
            print(f"An error occurred: {e}")
            return currentVer

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
        username = self.generateUsername().lower()
        address = f"{username}@{domain}"
        while True:
            try:
                emailID = requests.post("https://api.mail.tm/accounts", json={"address": address, "password": password})
                if emailID.status_code == 201 and "id" in emailID.json():
                    break
                else:
                    print(f"Failed to create email with address {address}. Sleeping for 5 seconds then will retry...")
                    time.sleep(5)
                    username = self.generateUsername().lower()
                    address = f"{username}@{domain}"
            except Exception as e:
                print(f"Error creating email: {e}. Sleeping for 5 seconds then will retry...")
                time.sleep(5)
                username = self.generateUsername().lower()
                address = f"{username}@{domain}"
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

    def promptAnalytics(self):
        if not os.path.exists("analytics.txt"):
            while True:
                analytics = input("\nNo personal data is collected, but anonymous usage statistics help us improve. Allow data collection? [y/n] (Default: Yes): ").strip().lower()
                if analytics in ("y", "yes", ""):
                    userId = str(uuid.uuid4())
                    with open("analytics.txt", "w") as file:
                        file.write("DO NOT CHANGE ANYTHING IN THIS FILE\n")
                        file.write("analytics=1\n")
                        file.write(f"userID={userId}\n")
                    print("Analytics collection enabled.")
                    return True
                elif analytics in ("n", "no"):
                    with open("analytics.txt", "w") as file:
                        file.write("DO NOT CHANGE ANYTHING IN THIS FILE\n")
                        file.write("analytics=0\n")
                    print("Analytics collection disabled.")
                    return False
                else:
                    continue

    def checkAnalytics(self, version):
        with open("analytics.txt", "r") as file:
            lines = file.readlines()
            analytics = None
            userId = None
            for line in lines:
                if line.startswith("analytics="):
                    analytics = line.strip().split("=", 1)[1]
                elif line.startswith("userID="):
                    userId = line.strip().split("=", 1)[1]
            if analytics == "1":
                self.sendAnalytics(version, userId)
            elif analytics == "0":
                return False

    def sendAnalytics(self, version, userId=None):
        # DO NOT CHANGE THIS KEY, IT IS USED FOR SIGNING THE ANALYTICS DATA
        key = b"Qing762.chy"

        # THIS USERID IS NOT RELATED TO THE USER'S ROBLOX ACCOUNT, IT IS JUST A UNIQUE ID FOR ANALYTICS PURPOSES
        if userId is None:
            userIdValue = None
            try:
                with open("analytics.txt", "r") as file:
                    for line in file:
                        if line.startswith("userID="):
                            userIdValue = line.strip().split("=", 1)[1]
                            break
            except FileNotFoundError:
                userIdValue = str(uuid.uuid4())
            userId = userIdValue or str(uuid.uuid4())

        message = userId.encode()
        signature = hmac.new(key, message, hashlib.sha256).hexdigest()

        data = {
            "userId": userId,
            "signature": signature,
            "version": version
        }
        try:
            response = requests.post(
                "https://qing762.is-a.dev/analytics/roblox",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                pass
            else:
                print(f"\nFailed to send analytics data. Status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"\nAn error occurred while sending analytics data: {e}")

    def generateUsername(self, scrambled=None):
        if scrambled is False:
            verb = random.choice(open('./lib/verbs.txt').read().split()).strip()
            noun = random.choice(open('./lib/nouns.txt').read().split()).strip()
            adjective = random.choice(open('./lib/adjectives.txt').read().split()).strip()
            number = random.randint(10, 99)
            username = verb + noun + adjective + str(number)
            return username
        else:
            gen = UsernameGenerator(10, 15)
            return gen.generate()


if __name__ == "__main__":
    print("This is a library file. Please run main.py instead.")
