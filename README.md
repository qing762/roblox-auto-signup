> [!NOTE]  
> Join the [Discord server](https://qing762.is-a,dev/discord) for issues. Thanks a lot!

> [!WARNING]
> Please be advised that usage of this tool is entirely at your own risk. I assumes no responsibility for any adverse consequences that may arise from its use, and users are encouraged to exercise caution and exercise their own judgment in utilizing this tool.

# Roblox auto signup

A tool that auto fetch a temporary email address and creates an account at https://roblox.com/.

## How it works

The process begins by utilizing the [Mail.tm](https://mail.tm/) service to obtain a temporary email address. Then it will create an [Roblox](https://roblox.com) account. The email address is then utilized for verification for the [Roblox](https://roblox.com) account. Subsequently, another request is made to [Mail.tm](https://mail.tm/) to retrieve the email confirmation link. Upon activation of the account, the user is able to log in to Roblox and enjoy the game with the account generated.


## Features

- Be able to prompt to change to your own password instead of using the default one.
- Password complexity checker for custom password.
- Automatically checks if the username generated is taken or not. If yes, a new one would be generated.
- Error handling.
- The script does all the job itself
- No webdriver required
- Fast execution time

> **Warning**
> The script does not solves FunCaptcha from Roblox, I haven't found an efficient way to do so. For now, you have to solve it by yourself.

## Installation / Usage

### [>>> VIDEO GUIDE <<<](https://qing762.is-a.dev/roblox-guide)

#### 1. Portable executable method:
- Just download the executable from the [releases tab](https://github.com/qing762/roblox-auto-signup/releases) and run it to generate accounts.
- If your antivirus has flagged for potential malware, that should be a false flag so feel free to safely ignore. If you dont trust it enough somehow, feel free to use [Step 2](https://github.com/qing762/roblox-auto-signup#2-python-file-method) instead.
- The account details should be generated at the `accounts.txt` file under the same directory.

#### 2. Python file method:
 - First, clone this repository:
 ```shell
 git clone https://github.com/qing762/roblox-auto-signup/
 ```

 - Install the necessary dependencies:
 ```shell
 pip install -r requirements.txt
 ```

 - Finally, run the Python file:
 ```shell
 python main.py
 ```

And you're all set! Follow the instructions while interacting with the Python file.


## Contributing

Contributions are always welcome!

To contribute, fork this repository and do anything you wish. After that, make a pull request.


## Feedback / Issues

If you have any feedback or issues running the code, please join the [Discord server](https://qing762.is-a.dev/discord)

### FOR ROBLOX CORPORATION EMPLOYEES IF YOU WISH TO REQUEST FOR TAKING DOWN THIS PROJECT

If the company wishes to discontinue or terminate this project, please do not hesitate to reach out to me. I can be reached at [Discord/qing762](https://discord.com/users/635765555277725696). Thank you for your attention to this matter.


## License

[MIT LICENSE](https://choosealicense.com/licenses/mit/)


---


![Alt](https://repobeats.axiom.co/api/embed/aac39ff8dcde3dfb590a680b382ffb8b1a06ed49.svg "Repobeats analytics image")


---
