> [!NOTE]  
> Join the [Discord server](https://qing762.is-a.dev/discord) for issues. Thanks a lot!

> [!WARNING]
> Please be advised that usage of this tool is entirely at your own risk. I assumes no responsibility for any adverse consequences that may arise from its use, and users are encouraged to exercise caution and exercise their own judgment in utilizing this tool.

# Roblox auto signup

A tool that auto fetch a temporary email address and creates an account at https://roblox.com/.

## How it works

The process begins by utilizing the [Mail.tm](https://mail.tm/) service to obtain a temporary email address. Then it will create an [Roblox](https://roblox.com) account. The email address is then utilized for verification for the [Roblox](https://roblox.com) account. Subsequently, another request is made to [Mail.tm](https://mail.tm/) to retrieve the email confirmation link. Upon activation of the account, the user is able to log in to Roblox and enjoy the game with the account generated.


## Features

- Able to use any Chromium-based browser.
- Able to use non authenticated proxy.
- Be able to prompt to change to your own password instead of using the default one.
- Password complexity checker for custom password.
- Automatically checks if the username generated is taken or not. If yes, a new one would be generated.
- Customizable username prefix.
- Able to randomly customize the account avatar (Clothes, Body size, etc)
- Error handling.
- Update checker functionality.
- The script does all the job by itself.
- No webdriver required.
- Fast execution time.

> **Warning**
> The script does not solves FunCaptcha from Roblox, I haven't found an efficient way to do so. For now, you have to solve it by yourself.

## Installation / Usage

### [>>> VIDEO GUIDE <<<](https://qing762.is-a.dev/roblox-guide)

#### 1. Portable executable method:
- Just download the executable from the [releases tab](https://github.com/qing762/roblox-auto-signup/releases) and run it to generate accounts.
- If your antivirus has flagged for potential malware, that should be a false flag so feel free to safely ignore. If you dont trust it enough somehow, feel free to use [Step 2](https://github.com/qing762/roblox-auto-signup#2-python-file-method) and build it yourself instead.
- The account details should be generated at the `accounts.txt` file under the same directory.

#### 2. Python file method:
 - First, ensure that Python is installed:
 ``` shell
 https://www.python.org/downloads/
 ```
 - Run the following command:
 ```shell
 git clone https://github.com/qing762/roblox-auto-signup/ && cd roblox-auto-signup && pip install -r requirements.txt && python main.py
 ```

And you're all set! Follow the instructions while interacting with the Python file.


## Anonymous Usage Analytics

This tool collects **anonymous usage data** to help to improve its features. 

Here are the list of data that will be collected:
- Tool version
- Anonymous user ID (a randomly generated UUID stored locally to distinguish sessions from unique users)

> The UUID is generated once on first run and saved locally. It is not tied to any of your identity.

<ins>**No personal information or sensitive data will be collected.**</ins>

To opt out, you can disable analytics at any time by:
- Enter `n`or `N` when prompted on the first run of the script.
- Running the script with `--no-analytics` argument
- Edit the analytics.txt file and change the value from `analytics=1` to `analytics=0`


## Contributing

Contributions are always welcome!

To contribute, fork this repository and do anything you wish. After that, make a pull request.


## Feedback / Issues

If you have any feedback or issues running the code, please join the [Discord server](https://qing762.is-a.dev/discord)

### FOR ROBLOX CORPORATION EMPLOYEES IF YOU WISH TO REQUEST FOR TAKING DOWN THIS PROJECT

If the company wishes to discontinue or terminate this project, please do not hesitate to reach out to me. I can be reached at [Discord/qing762](https://discord.com/users/635765555277725696). Thank you for your attention to this matter.


## License

Licensed under the GNU General Public License v3.0. See [LICENSE](https://github.com/qing762/roblox-auto-signup/blob/main/LICENSE) for details.


---


[![Star History Chart](https://api.star-history.com/svg?repos=qing762/roblox-auto-signup&type=Date&theme=dark)](https://www.star-history.com/#qing762/roblox-auto-signup&Date)


---
