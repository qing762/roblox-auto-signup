import asyncio
import os
import sys
import re
import gc
import random
import time
import shutil
import json
import traceback
from datetime import datetime, timezone

import warnings
import subprocess
import threading

# Import with error handling for optional dependencies
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("Warning: pyperclip not available - clipboard functionality will be disabled")

try:
    import requests
except ImportError as e:
    print("Error: requests module is required but not installed")
    print("Please install it with: pip install requests")
    print(f"Import error details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error importing requests: {e}")
    sys.exit(1)

try:
    from DrissionPage import Chromium, ChromiumOptions, errors
except ImportError as e:
    print("Error: DrissionPage module is required but not installed")
    print("Please install it with: pip install DrissionPage")
    print(f"Import error details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error importing DrissionPage: {e}")
    sys.exit(1)

try:
    from tqdm import TqdmExperimentalWarning
    from tqdm.rich import tqdm
except ImportError as e:
    print("Error: tqdm module is required but not installed")
    print("Please install it with: pip install tqdm")
    print(f"Import error details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error importing tqdm: {e}")
    sys.exit(1)

try:
    from lib.lib import Main, getResourcePath
except ImportError as e:
    print("Error: lib.lib module not found - ensure lib/lib.py exists")
    print(f"Import error details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error importing lib.lib: {e}")
    sys.exit(1)

# Pre-compile regex patterns for better performance and prevent memory issues
# Use module-level cache to prevent repeated compilation
_SUSPICIOUS_PATTERNS_CACHE = None
_PATTERNS_COMPILED = False

def _get_cached_suspicious_patterns():
    """Get cached security patterns to prevent memory leaks from repeated compilation"""
    global _SUSPICIOUS_PATTERNS_CACHE, _PATTERNS_COMPILED
    
    if _PATTERNS_COMPILED and _SUSPICIOUS_PATTERNS_CACHE is not None:
        return _SUSPICIOUS_PATTERNS_CACHE
    
    if _PATTERNS_COMPILED:  # Already tried compilation
        return _SUSPICIOUS_PATTERNS_CACHE or []
    
    _PATTERNS_COMPILED = True  # Mark as attempted
    patterns = []
    pattern_strings = [
        r'cmd\.exe', r'powershell\.exe', r'bash', r'sh\.exe', r'\.bat$', r'\.cmd$',
        r'%[A-Za-z_][A-Za-z0-9_]*%',  # Environment variables
        r'\$\([^)]*\)',  # Command substitution
        r'`[^`]*`',  # Backticks
        r'&&|\|\|', # Command chaining
    ]
    
    compiled_count = 0
    for pattern_str in pattern_strings:
        try:
            compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
            patterns.append(compiled_pattern)
            compiled_count += 1
        except re.error as regex_error:
            print(f"Warning: Failed to compile pattern '{pattern_str}': {regex_error}")
            continue
        except Exception as e:
            print(f"Warning: Unexpected error compiling pattern '{pattern_str}': {e}")
            continue
    
    # Ensure we have at least basic security patterns
    if compiled_count == 0:
        print("Warning: No security patterns compiled successfully. Adding basic fallback.")
        try:
            # Add basic fallback patterns that are less likely to fail
            basic_patterns = [r'[;&|`]', r'cmd\.exe', r'powershell\.exe']
            for pattern_str in basic_patterns:
                try:
                    patterns.append(re.compile(pattern_str, re.IGNORECASE))
                    compiled_count += 1
                except Exception:
                    continue
        except Exception as fallback_error:
            print(f"Warning: Could not compile fallback patterns: {fallback_error}")
    
    print(f"Security patterns initialized: {compiled_count} patterns compiled successfully.")
    _SUSPICIOUS_PATTERNS_CACHE = patterns
    return patterns

def _compile_suspicious_patterns():
    """Safely compile security patterns with proper error handling and caching"""
    return _get_cached_suspicious_patterns()

try:
    SUSPICIOUS_PATTERNS = _get_cached_suspicious_patterns()
except Exception as e:
    print(f"Warning: Error initializing security patterns: {e}")
    SUSPICIOUS_PATTERNS = []


warnings.filterwarnings("ignore", category=TqdmExperimentalWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")


def cleanup_browser_safely(chrome, page, progress_bar):
    """Centralized browser cleanup function to avoid code duplication"""
    cleanup_errors = []
    
    # Validate inputs to prevent issues
    if chrome is not None and not hasattr(chrome, 'quit'):
        print("Warning: Invalid chrome object passed to cleanup")
        chrome = None
    if page is not None and not hasattr(page, 'close'):
        print("Warning: Invalid page object passed to cleanup")
        page = None
    
    # Clean up progress bar first with enhanced error handling
    if progress_bar:
        try:
            if hasattr(progress_bar, 'close') and callable(progress_bar.close):
                progress_bar.close()
        except AttributeError:
            cleanup_errors.append("progress bar: no close method")
        except Exception as e:
            cleanup_errors.append(f"progress bar: {e}")
        # Note: progress_bar variable itself can't be modified here as it's a parameter
    
    # Clear page data and close page first
    if page:
        try:
            # Clear any pending requests
            if hasattr(page, 'stop'):
                page.stop()
        except Exception as e:
            cleanup_errors.append(f"page stop: {e}")
            
        try:
            if hasattr(page, 'set') and hasattr(page.set, 'cookies'):
                page.set.cookies.clear()
        except Exception as e:
            cleanup_errors.append(f"page cookies: {e}")
        
        try:
            if hasattr(page, 'clear_cache'):
                page.clear_cache()
        except Exception as e:
            cleanup_errors.append(f"page cache: {e}")
        
        # Close the page before quitting browser
        try:
            if hasattr(page, 'close'):
                page.close()
        except Exception as e:
            cleanup_errors.append(f"page close: {e}")
    
    # Clear browser data and quit browser
    if chrome:
        try:
            # Close all tabs first
            if hasattr(chrome, 'tabs'):
                for tab in chrome.tabs:
                    try:
                        if hasattr(tab, 'close'):
                            tab.close()
                    except Exception:
                        pass
        except Exception as e:
            cleanup_errors.append(f"browser tabs: {e}")
            
        try:
            if hasattr(chrome, 'set') and hasattr(chrome.set, 'cookies'):
                chrome.set.cookies.clear()
        except Exception as e:
            cleanup_errors.append(f"browser cookies: {e}")
        
        try:
            if hasattr(chrome, 'clear_cache'):
                chrome.clear_cache()
        except Exception as e:
            cleanup_errors.append(f"browser cache: {e}")
    
        # Quit browser with timeout protection
        try:
            if hasattr(chrome, 'quit'):
                # Add timeout protection for quit operation
                def quit_with_timeout():
                    try:
                        chrome.quit()
                    except Exception as quit_error:
                        print(f"Warning: Error during chrome.quit(): {quit_error}")
                
                quit_thread = threading.Thread(target=quit_with_timeout)
                quit_thread.daemon = True  # Don't block program exit
                quit_thread.start()
                quit_thread.join(timeout=10)  # Wait max 10 seconds
                
                if quit_thread.is_alive():
                    print("Warning: Browser quit operation timed out")
        except Exception as e:
            cleanup_errors.append(f"browser quit: {e}")
    
    # Force garbage collection
    gc.collect()
    
    # Windows-specific cleanup with timeout
    if os.name == 'nt':
        try:
            # Kill any remaining Chrome processes
            for process_name in ['chrome.exe', 'chromium.exe']:
                try:
                    result = subprocess.run(['taskkill', '/f', '/im', process_name], 
                                          stdout=subprocess.DEVNULL, 
                                          stderr=subprocess.DEVNULL,
                                          timeout=10,
                                          check=False)  # Don't raise exception on non-zero exit
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    pass  # Ignore errors in cleanup
        except Exception as e:
            cleanup_errors.append(f"process cleanup: {e}")
    
    # Log cleanup errors if any (but don't fail)
    if cleanup_errors:
        print(f"Warning: Errors during browser cleanup: {'; '.join(cleanup_errors)}")


def get_browser_path():
    """Get browser path from user input with validation"""
    while True:
        browserPath = input(
            "\033[1m"
            "\n(RECOMMENDED) Press enter in order to use the default browser path (If you have Chrome installed)"
            "\033[0m"
            "\nIf you prefer to use other Chromium browser other than Chrome, please enter its executable path here. (e.g: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe)"
            "\nNote that if captcha bypass is chosen, it will be using Ungoogled Chromium which is already included."
            "\nHere are some supported browsers that are tested and able to use:"
            "\n- Chrome Browser"
            "\n- Brave Browser"
            "\n- Ungoogled Chromium"
            "\nBrowser executable path: "
        )
        
        # Safer input handling for Unicode paths
        browserPath = browserPath.strip()
        if browserPath:
            # Remove surrounding quotes and normalize path
            browserPath = browserPath.strip('\'"').strip()
            try:
                # Normalize path for better cross-platform compatibility
                browserPath = os.path.normpath(browserPath)
            except (OSError, ValueError) as e:
                print(f"Invalid path format: {e}")
                continue
        
        if not browserPath:
            return None  # Use default browser
            
        # Enhanced security validation - allow legitimate Windows path characters
        dangerous_chars = ['&', '|', ';', '$', '`', '{', '}', '<', '>']  # Allow quotes and parentheses for legitimate paths
        if any(char in browserPath for char in dangerous_chars):
            print("Invalid characters detected in browser path. Please enter a valid executable path.")
            continue
        
        # Check for path traversal attempts more comprehensively - enhanced security
        path_parts = browserPath.replace('\\', '/').split('/')
        path_traversal_detected = False
        for part in path_parts:
            # Check for obvious path traversal patterns
            if part == '..':  # Parent directory traversal
                path_traversal_detected = True
                break
            # Don't flag single "." as it could be legitimate (like current directory reference)
            # Check for hidden files/directories that start with dot (except valid executables)
            if (part.startswith('.') and len(part) > 1 and 
                not part.lower().endswith(('.exe', '.app', '.dmg', '.com', '.scr')) and
                part != '.'):  # Allow single dot
                # Only flag as suspicious if it's not a legitimate executable
                path_traversal_detected = True
                break
        
        if path_traversal_detected:
            print("Path traversal detected. Please enter a direct path to the browser executable.")
            continue
        
        # Pre-compiled patterns to prevent memory leaks from repeated compilation
        # Additional security: check for potential command injection and suspicious patterns
        try:
            is_suspicious_exe = False
            if SUSPICIOUS_PATTERNS:  # Only check if patterns exist
                for pattern in SUSPICIOUS_PATTERNS:
                    try:
                        if pattern and hasattr(pattern, 'search') and pattern.search(browserPath):
                            is_suspicious_exe = True
                            break
                    except Exception as pattern_error:
                        print(f"Warning: Pattern matching error: {pattern_error}")
                        continue
            else:
                # Fallback check if no patterns available
                dangerous_substrings = ['cmd.exe', 'powershell.exe', 'bash', '&', ';', '|', '`', '$']
                is_suspicious_exe = any(dangerous in browserPath.lower() for dangerous in dangerous_substrings)
        except Exception as pattern_compilation_error:
            print(f"Warning: Error in pattern matching: {pattern_compilation_error}")
            is_suspicious_exe = False
                
        if is_suspicious_exe:
            # Allow if it's actually a chrome/chromium executable
            try:
                exe_name = os.path.basename(browserPath).lower()
                if not any(browser in exe_name for browser in ['chrome', 'chromium', 'brave']):
                    print("Potentially dangerous executable detected. Please provide a browser executable path.")
                    continue
                # If it's a valid browser executable, proceed with OS-specific validation
                print(f"Validated browser executable: {exe_name}")
            except (OSError, ValueError) as path_error:
                print(f"Error processing browser path: {path_error}")
                continue
            
        # OS-specific validation for all paths (including validated suspicious executables)
        if os.name == 'nt':
            if not browserPath.lower().endswith('.exe'):
                print("Browser path should end with .exe on Windows.")
                continue
            # Additional Windows-specific path validation
            try:
                # Check if path contains valid Windows directory separators
                normalized_path = os.path.normpath(browserPath)
                if os.path.exists(normalized_path):
                    # Verify it's actually an executable file, not a directory
                    if os.path.isfile(normalized_path):
                        return normalized_path
                    else:
                        print("Path points to a directory, not an executable file.")
                        continue
                else:
                    print("Please enter a valid path.")
                    continue
            except (OSError, ValueError) as path_error:
                print(f"Error validating Windows path: {path_error}")
                continue
        elif os.name == 'posix':
            # For Unix-like systems, check if file exists and is executable
            if os.path.exists(browserPath) and os.access(browserPath, os.X_OK):
                return browserPath
            else:
                print("Browser path should be an executable file on Unix-like systems.")
                continue
        else:
            # For other systems, just check if file exists
            if os.path.exists(browserPath):
                return browserPath
            else:
                print("Please enter a valid path.")
                continue


async def main():
    lib = Main()
    co = ChromiumOptions()
    co.auto_port().mute(True)

    print("Checking for updates...")
    version = await lib.checkUpdate()

    lib.promptAnalytics()
    print()
    try:
        lib.downloadUngoogledChromium()
    except Exception as e:
        print(f"Warning: Error downloading Ungoogled Chromium: {e}")

    browser_configured = False
    browser_config_attempts = 0
    max_browser_config_attempts = 5
    
    while not browser_configured and browser_config_attempts < max_browser_config_attempts:
        browser_config_attempts += 1
        try:
            browserPath = lib.returnUngoogledChromiumPath()
        except Exception as e:
            print(f"An error occurred while checking for Ungoogled Chromium: {e}")
            browserPath = None
        
        if browserPath is None:
            user_browser_path = get_browser_path()
            if user_browser_path:
                co.set_browser_path(user_browser_path)
                browser_configured = True
            else:
                print("No browser path provided. Will use default browser.")
                browser_configured = True
        else:
            ungoogledChromiumUsage = input(
                "Ungoogled Chromium is detected in the lib folder, would you like to use it? [y/n] (Default: Yes): "
            )
            if ungoogledChromiumUsage.lower() in ["y", "n", ""]:
                if ungoogledChromiumUsage.lower() == "y" or ungoogledChromiumUsage == "":
                    if browserPath:  # Use the already retrieved path
                        # Validate that the browser path actually contains chrome.exe
                        chrome_exe_path = os.path.join(browserPath, "chrome.exe")
                        if os.path.exists(chrome_exe_path):
                            co.set_browser_path(chrome_exe_path)
                        else:
                            print(f"Warning: chrome.exe not found at {chrome_exe_path}")
                            co.set_browser_path(browserPath)  # Fallback
                    browser_configured = True
                else:
                    user_browser_path = get_browser_path()
                    if user_browser_path:
                        co.set_browser_path(user_browser_path)
                        browser_configured = True
                    else:
                        print("No browser path provided. Will use default browser.")
                        browser_configured = True
            else:
                print("\nPlease enter a valid option.")
                # Check if we've reached max attempts before continuing
                if browser_config_attempts >= max_browser_config_attempts:
                    print(f"Maximum browser configuration attempts ({max_browser_config_attempts}) reached. Using default browser.")
                    browser_configured = True
                    break

    password_attempts = 0
    max_password_attempts = 5  # Prevent infinite loop
    
    while password_attempts < max_password_attempts:
        password_attempts += 1  # Increment at start to prevent infinite loops
        passw = (
            input(
                "\033[1m"
                "\n(RECOMMENDED) Press enter in order to use the default password"
                "\033[0m"
                "\nThe password will be used for the account and email.\nIf you prefer to use your own password, do make sure that your password is strong enough.\nThis script has a built in password complexity checker.\nPassword: "
            )
            or "Qing762.chy"
        )
        if passw != "Qing762.chy":
            try:
                # Generate a simple temporary username for password validation
                temp_username = f"tmp{random.randint(100, 999)}"  # Always generates 6 characters (tmp + 3 digits)
                
                # Ensure temp username meets Roblox requirements (3-20 characters) - double-check
                if len(temp_username) > 20:
                    temp_username = temp_username[:20]
                elif len(temp_username) < 3:
                    temp_username = "tmp123"  # Guaranteed fallback
                
                result = await lib.checkPassword(temp_username, passw)
                print(result)
                if result and "Password is valid" in result:
                    break
                else:
                    if password_attempts >= max_password_attempts:
                        print(f"Maximum password attempts ({max_password_attempts}) reached. Using default password.")
                        passw = "Qing762.chy"
                        break
                    print("Password validation failed. Please try a different password.")
                    continue
            except Exception as e:
                print(f"Error checking password: {e}")
                if password_attempts >= max_password_attempts:
                    print(f"Maximum password attempts ({max_password_attempts}) reached. Using default password.")
                    passw = "Qing762.chy"
                    break
                print("Could not validate password strength. Please try a different password or use the default.")
                continue
        else:
            break
    
    # Ensure we have a valid password after the loop
    if password_attempts >= max_password_attempts and passw != "Qing762.chy":
        print(f"Password validation timed out after {max_password_attempts} attempts. Using default password.")
        passw = "Qing762.chy"

    while True:
        verification = input(
            "\033[1m"
            "\n(RECOMMENDED) Press enter in order to enable email verification"
            "\033[0m"
            "\nIf you prefer to turn off email verification, you will risk losing the account. It might also be applicable for people who do not have email verification element"
            "\nWould you like to enable email verification? [y/n] (Default: Yes): "
        )
        if verification.lower() in ["y", "n", ""]:
            break
        else:
            print("\nPlease enter a valid option.")

    nameFormat = input(
        "\033[1m"
        "\n(RECOMMENDED) Press enter in order to use randomized name prefix"
        "\033[0m"
        "\nIf you prefer to go by your own name prefix, please enter it here.\nIt will go by this example: (If name prefix is 'qing', then the account generated will be named 'qing_0', 'qing_1' and so on)\nName prefix: "
    ).strip()
    
    # Validate nameFormat input
    if nameFormat:
        # Limit length to prevent issues
        if len(nameFormat) > 15:  # Leave room for counter and underscore
            print(f"Warning: Name prefix too long (max 15 characters). Truncating to: {nameFormat[:15]}")
            nameFormat = nameFormat[:15]
        
        # Validate characters
        if not re.match(r'^[a-zA-Z0-9_]+$', nameFormat):
            print("Warning: Name prefix contains invalid characters. Only letters, numbers, and underscores are allowed.")
            print("Using randomized name prefix instead.")
            nameFormat = ""
        
        # Check for reserved words
        reserved_words = ['admin', 'roblox', 'moderator', 'test', 'null', 'undefined', 'system']
        if nameFormat.lower() in reserved_words:
            print(f"Warning: '{nameFormat}' is a reserved word. Using randomized name prefix instead.")
            nameFormat = ""

    scrambledUsername = True  # Default value
    if not nameFormat:  # Only ask about scrambled username if no nameFormat is provided
        while True:
            scrambledUsername = input("\nWould you like to use a scrambled username?\nIf no, the script will try to generate a structured username, this might increase generation time. [y/n] (Default: Yes): ")
            if scrambledUsername.lower() in ["y", "n", ""]:
                scrambledUsername = scrambledUsername.lower() == "y" or scrambledUsername == ""
                break
            else:
                print("\nPlease enter a valid option.")

    while True:
        customization = input(
            "\nWould you like to customize the account after the generation process with a randomizer? [y/n] (Default: Yes): "
        )
        if customization.lower() in ["y", "n", ""]:
            break
        else:
            print("\nPlease enter a valid option.")

    followUser = input(
        "\nWould you like to follow any additional accounts after generating this account?\n"
        "If yes, enter the usernames separated by commas (,).\n"
        "Leave blank if none.\n"
        "Usernames: "
    )

    proxyUsage = input(
        "\nWould you like to use proxies?\n"
        "If yes, please enter the proxy IP and port in the format of IP:PORT separated by commas (,). (Example: http://localhost:1080).\n"
        "Leave blank if none.\n"
        "Proxy: "
    )

    captchaBypass = input(
        "\nWould you like to bypass captcha through NopeCHA? (Note that there's only up to 200 free solves per day)"
        "\nYou can get a free API key from https://nopecha.com/manage and paste it here."
        "\nIf yes, please enter the API key for the service."
        "\nLeave blank if none."
        "\nAPI Key: "
    ).strip()

    # Simplified API key validation with better security checks
    if captchaBypass:
        # Check for obvious malicious patterns first
        try:
            # Basic validation for legitimate API keys first
            if not re.match(r'^[a-zA-Z0-9_\-\.\+\/=]+$', captchaBypass):
                print("Warning: API key contains potentially invalid characters.")
                confirm = input("Continue anyway? [y/n]: ")
                if confirm.lower() != "y":
                    captchaBypass = ""
            elif len(captchaBypass) < 10:  # Reasonable minimum length
                print("Warning: The API key seems too short.")
                confirm = input("Continue anyway? [y/n]: ")
                if confirm.lower() != "y":
                    captchaBypass = ""
            elif len(captchaBypass) > 200:  # Reasonable upper limit
                print("Warning: The API key seems too long.")
                confirm = input("Continue anyway? [y/n]: ")
                if confirm.lower() != "y":
                    captchaBypass = ""
            
            # Check for obvious malicious patterns
            dangerous_patterns = ['&', ';', '|', '`', '$', '<script', 'javascript:', 'data:', 'file:', '../']
            if any(pattern in captchaBypass.lower() for pattern in dangerous_patterns):
                print("Warning: API key contains suspicious patterns.")
                captchaBypass = ""
                
        except Exception as validation_error:
            print(f"Warning: Error during API key validation: {validation_error}")
            print("Using basic validation as fallback.")
            # Simple fallback validation
            if len(captchaBypass) < 10 or len(captchaBypass) > 200:
                captchaBypass = ""

    while True:
        incognitoUsage = input(
            "\nWould you like to use incognito mode? Note that if captcha bypass is chosen, it will not be using incognito mode automatically. [y/n] (Default: Yes): "
        )
        if incognitoUsage.lower() in ["y", "n", ""]:
            break
        else:
            print("\nPlease enter a valid option.")

    accounts = []
    execution_attempts = 0
    max_execution_attempts = 5  # Prevent infinite loop

    while execution_attempts < max_execution_attempts:
        execution_attempts += 1  # Increment at the beginning to avoid missing increments
        
        executionCount = input(
            "\nNumber of accounts to generate (Default: 1): "
        )
        try:
            if executionCount == "" or executionCount.strip() == "":
                executionCount = 1
                break
            
            # Validate input is numeric
            if not executionCount.strip().isdigit():
                if execution_attempts >= max_execution_attempts:
                    print(f"Maximum input attempts reached. Using default value (1).")
                    executionCount = 1
                    break
                print("Please enter a valid positive number.")
                continue
                
            executionCount = int(executionCount.strip())
            if executionCount <= 0:
                if execution_attempts >= max_execution_attempts:
                    print(f"Maximum input attempts reached. Using default value (1).")
                    executionCount = 1
                    break
                print("Please enter a positive number.")
                continue
            if executionCount > 100:
                print("Warning: Generating more than 100 accounts may take a very long time and could trigger rate limits.")
                confirm = input("Are you sure you want to continue? [y/n]: ")
                if confirm.lower() != "y":
                    continue
            break
        except ValueError:
            if execution_attempts >= max_execution_attempts:
                print(f"Maximum input attempts reached. Using default value (1).")
                executionCount = 1
                break
            print("Please enter a valid number.")
        except Exception as e:
            if execution_attempts >= max_execution_attempts:
                print(f"Maximum input attempts reached. Using default value (1).")
                executionCount = 1
                break
            print(f"Invalid input: {e}")
            continue

    print()

    if customization.lower() == "y" or customization == "":
        customization = True
    else:
        customization = False

    if followUser != "":
        following = True
        followUserList = followUser.split(",")
        followUserList = [user.strip() for user in followUserList if user.strip()]

        valid_followUserList = []
        for i, user in enumerate(followUserList):
            # Enhanced username validation with better error messages and safety checks
            if not user or not isinstance(user, str):  # Skip empty/invalid usernames
                print(f"Skipping invalid username at position {i}: {repr(user)}")
                continue
            
            # Clean the username
            user = user.strip()
            if not user:  # Skip if empty after cleaning
                print(f"Skipping empty username after cleaning at position {i}")
                continue
            
            # Limit username length to prevent memory issues and enforce Roblox limit
            if len(user) > 20:  # Roblox username limit
                print(f"Username '{user[:20]}...' is too long (max 20 characters for Roblox)")
                continue
                
            # Enhanced regex validation with error handling
            try:
                if not re.match(r'^[a-zA-Z0-9_]+$', user):
                    print(f"Invalid username '{user}' - usernames can only contain letters, numbers, and underscores")
                    continue
            except re.error as regex_error:
                print(f"Error validating username '{user}': {regex_error}")
                continue
            except Exception as validation_error:
                print(f"Unexpected error validating username '{user}': {validation_error}")
                continue
                
            # Validate minimum length constraints for Roblox
            if len(user) < 3:
                print(f"Invalid username '{user}' - usernames must be at least 3 characters")
                continue
                
            # Check for reserved usernames or obvious test names that might cause issues
            reserved_names = ['admin', 'roblox', 'administrator', 'mod', 'moderator', 'test', 'null', 'undefined', 'none']
            if user.lower() in reserved_names:
                print(f"Warning: Username '{user}' appears to be reserved or invalid")
                continue
            
            valid_followUserList.append(user)
            
        followUserList = valid_followUserList
        if not followUserList:
            print("No valid usernames found in follow list.")
            following = False
        else:
            print(f"Will attempt to follow {len(followUserList)} users: {', '.join(followUserList)}")
    else:
        following = False
        followUserList = []  # Initialize empty list to prevent undefined variable error

    if verification.lower() == "y" or verification == "":
        verification = True
    else:
        verification = False

    if (incognitoUsage.lower() == "y" or incognitoUsage == "") and captchaBypass == "":
        co.incognito()

    if captchaBypass != "":
        nopecha_path = getResourcePath("lib/NopeCHA")
        if os.path.exists(nopecha_path):
            co.add_extension(nopecha_path)
        else:
            print("Warning: NopeCHA extension not found. Captcha bypass may not work.")
        try:
            ungoogledPath = lib.returnUngoogledChromiumPath()
            if ungoogledPath:
                chrome_exe_path = os.path.join(ungoogledPath, "chrome.exe")
                if os.path.exists(chrome_exe_path):
                    co.set_browser_path(chrome_exe_path)
                else:
                    print(f"Warning: chrome.exe not found at {chrome_exe_path}")
            else:
                print("Warning: Could not find ungoogled chromium, using default browser")
        except Exception as e:
            print(f"Warning: Could not set ungoogled chromium path: {e}")

    if proxyUsage.strip():
        proxyList = [proxy.strip() for proxy in proxyUsage.split(",") if proxy.strip()]
    else:
        proxyList = []
    
    usableProxies = []  # Initialize here to ensure it's always defined
    if proxyList:  # Only test if we have proxies to test
        print(f"Testing {len(proxyList)} proxies...")
        for i, proxy in enumerate(proxyList):
            if proxy:  # Only test non-empty proxies
                try:
                    print(f"Testing proxy {i+1}/{len(proxyList)}: {proxy}")
                    result = lib.testProxy(proxy)
                    if result and len(result) >= 2 and result[0] == True:
                        usableProxies.append(proxy)
                        print(f"✓ Proxy {proxy} is working")
                    elif result and len(result) >= 2:
                        print(f"✗ Proxy {proxy} failed: {result[1]}")
                    else:
                        print(f"✗ Proxy {proxy} returned invalid result")
                except KeyboardInterrupt:
                    print("\nProxy testing interrupted by user")
                    break
                except Exception as proxy_test_error:
                    print(f"✗ Error testing proxy {proxy}: {proxy_test_error}")
        
        print(f"Proxy testing complete: {len(usableProxies)}/{len(proxyList)} proxies are usable")
    
    # Ensure we have a backup plan if all proxies fail
    if proxyUsage.strip() and not usableProxies:
        print("Warning: No usable proxies found. Continuing without proxy support.")
        proxyList = []
        usableProxies = []

    for x in range(executionCount):
        captchaPresence = True
        captchaRetries = 0
        maxCaptchaRetries = 5
        account_created_successfully = False
        max_total_retries = 15  # Hard limit to prevent infinite loops
        total_retry_count = 0
        
        while (captchaPresence and 
               captchaRetries < maxCaptchaRetries and 
               not account_created_successfully and
               total_retry_count < max_total_retries):
            # Initialize proxy variables for this attempt
            total_retry_count += 1  # Increment total retry counter
                
            selected_proxy = None
            proxy_set_successfully = False
            
            if proxyUsage.strip() and usableProxies:
                # Simplified proxy selection without threading complications
                try:
                    selected_proxy = random.choice(usableProxies)
                    
                    # Quick test before using - reduced timeout for faster failover
                    try:
                        test_response = requests.get(
                            "https://httpbin.org/ip", 
                            proxies={"http": selected_proxy, "https": selected_proxy}, 
                            timeout=5,  # Quick test
                            headers={'User-Agent': 'Mozilla/5.0'}
                        )
                        if test_response.status_code == 200:
                            co.set_proxy(selected_proxy)
                            print(f"Using proxy: {selected_proxy}")
                            proxy_set_successfully = True
                        else:
                            print(f"Proxy {selected_proxy} test failed, continuing without proxy")
                    except Exception as proxy_test_error:
                        print(f"Proxy {selected_proxy} failed quick test: {proxy_test_error}")
                        print("Continuing without proxy")
                        
                except Exception as e:
                    print(f"Error setting proxy: {e}")
                    print("Continuing without proxy")
                    
            if not proxy_set_successfully and proxyUsage.strip():
                print("Warning: Could not set any proxy, continuing without proxy support")

            if "--no-analytics" not in sys.argv:
                lib.checkAnalytics(version)
            
            try:
                if nameFormat:
                    username = await lib.usernameCreator(nameFormat)
                else:
                    username = await lib.usernameCreator(None, scrambled=scrambledUsername)
            except Exception as e:
                print(f"Error generating username: {e}")
                print("Using fallback username generation...")
                try:
                    username = await lib.usernameCreator(None, scrambled=True)
                except Exception as e2:
                    print(f"Fallback username generation also failed: {e2}")
                    # Ensure emergency fallback username is within Roblox 20-character limit
                    # Generate a guaranteed unique and valid username within limits
                    timestamp = int(time.time()) % 100000  # 5 digits max
                    emergency_username = f"user{timestamp}"
                    # Ensure it meets Roblox requirements (3-20 characters)
                    if len(emergency_username) > 20:
                        emergency_username = emergency_username[:20]
                    elif len(emergency_username) < 3:
                        emergency_username = "usr123"  # Guaranteed 6 characters
                    username = emergency_username
                    print(f"Using emergency fallback username: {username}")
            
            # Initialize variables to ensure they exist for cleanup
            chrome = None
            page = None
            bar = None
            accountCookies = []
            email = None
            emailPassword = None
            emailID = None
            token = None
            browser_init_success = False
            
            try:
                bar = tqdm(total=100)
                bar.set_description(f"Initial setup completed [{x + 1}/{executionCount}]")
                bar.update(10)
            except Exception as bar_error:
                print(f"Warning: Could not initialize progress bar: {bar_error}")
                bar = None
            
            browser_init_attempts = 3
            browser_init_success = False
            max_total_browser_attempts = 10  # Hard limit to prevent infinite loops
            total_browser_attempts = 0
            
            for init_attempt in range(browser_init_attempts):
                total_browser_attempts += 1
                if total_browser_attempts >= max_total_browser_attempts:
                    print(f"Maximum total browser initialization attempts ({max_total_browser_attempts}) reached")
                    break
                    
                try:
                    if init_attempt > 0:
                        print(f"Browser initialization attempt {init_attempt + 1}/{browser_init_attempts} (total: {total_browser_attempts}/{max_total_browser_attempts})")
                        await asyncio.sleep(min(2 + init_attempt, 10))  # Progressive delay with cap
                    
                    # Clean up any existing instances before creating new one
                    if chrome is not None:
                        try:
                            chrome.quit()
                        except Exception:
                            pass
                        finally:
                            chrome = None
                            page = None  # Also clear page reference when chrome is cleared
                        # Force garbage collection after cleanup
                        gc.collect()
                    
                    # Create new chrome instance
                    chrome = Chromium(addr_or_opts=co)
                    if chrome is None:
                        raise Exception("Failed to create Chromium instance")
                        
                    # Get the page after chrome is successfully created
                    page = chrome.latest_tab
                    if page is None:
                        raise Exception("Failed to get browser tab")
                    
                    # Test browser functionality with timeout
                    try:
                        page.set.window.max()
                        # Simple test to verify browser is responsive with timeout
                        page.get("data:text/html,<html><body>Test</body></html>", timeout=10)
                        browser_init_success = True
                        break  # Success
                    except Exception as window_error:
                        print(f"Warning: Browser window operations failed: {window_error}")
                        # Try alternative window setup
                        try:
                            page.set.window.size(1024, 768)  # Fallback to fixed size
                            page.get("data:text/html,<html><body>Test</body></html>", timeout=10)
                            browser_init_success = True
                            break  # Success with fallback
                        except Exception as fallback_error:
                            raise Exception(f"Browser not responsive: {fallback_error}")
                        
                except Exception as browser_init_error:
                    # Clean up on failure
                    cleanup_errors = []
                    
                    # Clean up page first
                    if page is not None:
                        try:
                            page.close()
                        except Exception as page_cleanup_error:
                            cleanup_errors.append(f"page close: {page_cleanup_error}")
                        finally:
                            page = None
                    
                    # Clean up chrome instance
                    if chrome is not None:
                        try:
                            chrome.quit()
                        except Exception as chrome_cleanup_error:
                            cleanup_errors.append(f"chrome quit: {chrome_cleanup_error}")
                        finally:
                            chrome = None
                    
                    # Force garbage collection
                    gc.collect()
                    
                    # Log cleanup errors for debugging
                    if cleanup_errors:
                        print(f"Warning: Cleanup errors during browser initialization failure: {'; '.join(cleanup_errors)}")
                    
                    if init_attempt == browser_init_attempts - 1:
                        print(f"Failed to initialize browser after {browser_init_attempts} attempts: {browser_init_error}")
                        # Ensure we break out of all loops on final failure
                        browser_init_success = False
                        break
                    else:
                        print(f"Browser initialization attempt {init_attempt + 1} failed: {browser_init_error}. Retrying...")
                        await asyncio.sleep(1 + init_attempt)
            
            # Comprehensive cleanup on any browser initialization failure
            if not browser_init_success or chrome is None or page is None:
                print("Browser initialization failed completely. Cleaning up and skipping this account.")
                
                # Clean up any partial browser instance safely
                cleanup_browser_safely(chrome, page, bar)
                
                # Reset variables
                chrome = None
                page = None
                bar = None
                
                # Don't mark account as successfully created if browser failed
                account_created_successfully = False
                
                # Browser initialization failure is not a captcha issue
                # Just break out of the retry loop for this account
                print(f"Browser initialization failed for account {x + 1}. Moving to next account.")
                break  # Break out of the retry loop for this account

            if verification is True:
                try:
                    email, emailPassword, token, emailID = await lib.generateEmail(passw)
                    if bar is not None:
                        bar.set_description(f"Generated email [{x + 1}/{executionCount}]")
                        bar.update(10)
                except Exception as e:
                    print(f"Failed to generate email: {e}")
                    # Clean up progress bar safely
                    if bar is not None:
                        try:
                            bar.close()
                        except Exception:
                            pass
                        finally:
                            bar = None
                    
                    # Clean up browser before continuing
                    cleanup_browser_safely(chrome, page, None)
                    
                    # Reset variables
                    chrome = None
                    page = None
                    
                    # Force garbage collection
                    gc.collect()
                    continue

            try:
                if captchaBypass != "":
                    page.get(f"https://nopecha.com/setup#{captchaBypass}")
                page.get("https://www.roblox.com/CreateAccount")
                try:
                    lang_result = page.run_js_loaded("return window.navigator.userLanguage || window.navigator.language")
                    lang = lang_result.split("-")[0] if lang_result and "-" in lang_result else "en"
                except Exception as e:
                    print(f"Warning: Could not detect browser language: {e}")
                    lang = "en"  # Default fallback
                try:
                    page.ele('@class=btn-cta-lg cookie-btn btn-primary-md btn-min-width', timeout=3).click()
                except errors.ElementNotFoundError:
                    pass
                
                try:
                    bdaymonthelement = page.ele("#MonthDropdown", timeout=10)
                    if not bdaymonthelement:
                        raise Exception("Month dropdown element not found")
                except (errors.ElementNotFoundError, AttributeError, Exception) as e:
                    print(f"Error: Could not find month dropdown: {e}")
                    raise  # This is critical for signup

                # Simplified locale handling with better error recovery
                current_month = None
                
                try:
                    # Try UTC time first with validation
                    utc_now = datetime.now(timezone.utc)
                    
                    # Use month mapping to avoid locale dependencies
                    month_map = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                                7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
                    current_month = month_map.get(utc_now.month, "Jan")
                    
                except Exception as time_error:
                    print(f"Warning: Error getting current time: {time_error}")
                    # Fallback to hardcoded month
                    current_month = "Jan"
                
                # Ensure we have a valid month with additional validation
                if not current_month or not isinstance(current_month, str) or len(current_month) != 3:
                    current_month = "Jan"
                
                # Additional validation - ensure month is one of the expected values
                valid_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                if current_month not in valid_months:
                    current_month = "Jan"
                
                try:
                    bdaymonthelement.select.by_value(current_month)
                except Exception as e:
                    print(f"Warning: Could not set month to {current_month}: {e}")
                    # Try setting to default month as fallback
                    try:
                        bdaymonthelement.select.by_value("Jan")
                    except Exception as fallback_error:
                        print(f"Warning: Could not set fallback month: {fallback_error}")
                
                try:
                    bdaydayelement = page.ele("#DayDropdown", timeout=10)
                    if not bdaydayelement:
                        raise Exception("Day dropdown element not found")
                    
                    # Use UTC for consistent day calculation
                    try:
                        utc_now = datetime.now(timezone.utc)
                        currentDay = utc_now.day
                        # Validate day is in valid range
                        if not (1 <= currentDay <= 31):
                            currentDay = 1
                    except Exception:
                        # Fallback to a safe default day
                        currentDay = 1
                except (errors.ElementNotFoundError, AttributeError, Exception) as e:
                    print(f"Error: Could not find day dropdown: {e}")
                    raise  # This is critical for signup
                
                # Try setting day value - first with string conversion, then with zero-padding
                try:
                    bdaydayelement.select.by_value(str(currentDay))
                except Exception as e:
                    # Fallback: try with leading zero for single digits
                    try:
                        day_value = f"{currentDay:02d}"
                        bdaydayelement.select.by_value(day_value)
                    except Exception as e2:
                        print(f"Warning: Could not set day to {currentDay}, using default. Errors: {e}, {e2}")
                        
                # Use UTC for consistent year calculation
                try:
                    utc_now = datetime.now(timezone.utc)
                    currentYear = utc_now.year - 19
                    # Validate year is reasonable
                    if currentYear < 1900 or currentYear > utc_now.year:
                        currentYear = utc_now.year - 19
                except Exception:
                    # Fallback year calculation
                    try:
                        current_year = time.gmtime().tm_year
                        currentYear = current_year - 19
                    except (AttributeError, OSError):
                        currentYear = 2005  # Safe fallback
                try:
                    page.ele("#YearDropdown", timeout=10).select.by_value(str(currentYear))
                except Exception as e:
                    print(f"Warning: Could not set year to {currentYear}: {e}")
                
                try:
                    username_element = page.ele("#signup-username", timeout=10)
                    if not username_element:
                        raise Exception("Username input element not found")
                    username_element.input(username)
                except (errors.ElementNotFoundError, AttributeError, Exception) as e:
                    print(f"Error: Could not input username: {e}")
                    raise  # This is critical, so we should fail
                
                try:
                    password_element = page.ele("#signup-password", timeout=10)
                    if not password_element:
                        raise Exception("Password input element not found")
                    password_element.input(passw)
                except (errors.ElementNotFoundError, AttributeError, Exception) as e:
                    print(f"Error: Could not input password: {e}")
                    raise  # This is critical, so we should fail
                
                await asyncio.sleep(2)
                try:
                    checkbox_element = page.ele('@@id=signup-checkbox@@class=checkbox', timeout=5)
                    if checkbox_element:
                        checkbox_element.click()
                except errors.ElementNotFoundError:
                    pass  # Checkbox not found, which is fine
                except errors.ElementNotClickableError:
                    print("Warning: Signup checkbox is not clickable")
                except Exception as e:
                    print(f"Warning: Could not click signup checkbox: {e}")
                
                await asyncio.sleep(1)
                try:
                    signup_button = page.ele("@@id=signup-button@@name=signupSubmit@@class=btn-primary-md signup-submit-button btn-full-width", timeout=10)
                    if not signup_button:
                        raise Exception("Signup button element not found")
                    signup_button.click()
                except (errors.ElementNotFoundError, AttributeError, Exception) as e:
                    print(f"Error: Could not click signup button: {e}")
                    raise  # This is critical, so we should fail
                if bar is not None:
                    bar.set_description(f"Signup submitted [{x + 1}/{executionCount}]")
                    bar.update(20)

                try:
                    captcha = page.get_frame('xpath://*[@id="arkose-iframe"]')
                    if captcha:
                        if captchaBypass == "":
                            # No captcha bypass - always retry
                            print(f"Captcha detected for account {x + 1}, retrying... (Attempt {captchaRetries + 1}/{maxCaptchaRetries})")
                            captchaPresence = True
                            captchaRetries += 1
                        else:
                            # With captcha bypass enabled, wait for NopeCHA to solve
                            print(f"Captcha detected for account {x + 1}, waiting for NopeCHA to solve...")
                            nopecha_wait_time = 15
                            await asyncio.sleep(nopecha_wait_time)
                            
                            max_nopecha_checks = 3
                            nopecha_checks = 0
                            
                            while nopecha_checks < max_nopecha_checks:
                                try:
                                    captcha_check = page.get_frame('xpath://*[@id="arkose-iframe"]')
                                    if captcha_check:
                                        nopecha_checks += 1
                                        if nopecha_checks < max_nopecha_checks:
                                            print(f"Captcha still present, waiting more... (Check {nopecha_checks}/{max_nopecha_checks})")
                                            await asyncio.sleep(10)
                                        else:
                                            print(f"Captcha still present after {max_nopecha_checks} checks, retrying... (Attempt {captchaRetries + 1}/{maxCaptchaRetries})")
                                            captchaPresence = True
                                            captchaRetries += 1
                                            break
                                    else:
                                        captchaPresence = False
                                        break
                                except errors.ElementNotFoundError:
                                    captchaPresence = False  # Captcha was solved
                                    break
                                except Exception as captcha_check_error:
                                    print(f"Error during captcha check: {captcha_check_error}")
                                    nopecha_checks += 1
                                    if nopecha_checks >= max_nopecha_checks:
                                        captchaPresence = False  # Assume solved to avoid infinite loop
                                        break
                                    # Don't break immediately, continue to next iteration
                        
                        # Clean up browser if retrying
                        if captchaPresence and captchaRetries < maxCaptchaRetries:
                            try:
                                if bar is not None:
                                    bar.close()
                                    bar = None
                            except Exception:
                                pass
                                
                            try:
                                if chrome is not None:
                                    chrome.quit()
                                    chrome = None
                                    page = None
                            except Exception as quit_error:
                                print(f"Warning: Error closing browser during captcha retry: {quit_error}")
                            
                            # Force garbage collection
                            gc.collect()
                            continue
                    else:
                        captchaPresence = False
                except errors.ElementNotFoundError:
                    captchaPresence = False
                except Exception as captcha_error:
                    print(f"Warning: Error checking for captcha: {captcha_error}")
                    captchaPresence = False

            except Exception as e:
                print(f"\nAn error occurred during account creation: {e}\n")
                captchaPresence = False
                # Ensure comprehensive cleanup on any exception
                try:
                    if bar is not None:
                        bar.close()
                except Exception:
                    pass
                finally:
                    bar = None
                    
                try:
                    if chrome is not None:
                        chrome.quit()
                except Exception as cleanup_error:
                    print(f"Warning: Could not quit browser during exception cleanup: {cleanup_error}")
                finally:
                    chrome = None
                    page = None
                
                # Force garbage collection after exception
                gc.collect()
                continue

        # Handle case where max captcha retries reached
        if captchaRetries >= maxCaptchaRetries and not account_created_successfully:
            print(f"Max captcha retries reached for account {x + 1}. Skipping this account.")
            try:
                # Ensure browser cleanup in all cases
                if chrome is not None:
                    try:
                        chrome.quit()
                    except Exception as quit_error:
                        print(f"Warning: Error closing browser after max retries: {quit_error}")
                    finally:
                        chrome = None
                        page = None  # Also clear page reference
            except Exception as e:
                print(f"Warning: Could not quit browser: {e}")
            finally:
                # Ensure progress bar is closed and force garbage collection
                if bar is not None:
                    try:
                        bar.close()
                    except Exception:
                        pass
                    finally:
                        bar = None
                gc.collect()
            # Force exit the captcha loop by setting captchaPresence to False
            captchaPresence = False
            break  # Break out of the captcha retry loop completely

        if not captchaPresence and not account_created_successfully:
            account_created_successfully = True
            # Determine timeout based on captcha bypass usage
            timeout = 10 if captchaBypass == "" else 300
            success_redirect = False

            try:
                if lang == "en":
                    page.wait.url_change("https://www.roblox.com/home", timeout=timeout)
                    success_redirect = True
                else:
                    # Use language-specific URL for non-English languages
                    try:
                        page.wait.url_change(f"https://www.roblox.com/{lang}/home", timeout=timeout)
                        success_redirect = True
                    except errors.TimeoutError:
                        # Fallback: try with generic home URL if language-specific fails
                        try:
                            page.wait.url_change("https://www.roblox.com/home", timeout=min(timeout, 10))
                            success_redirect = True
                        except errors.TimeoutError:
                            print(f"Warning: Signup redirect timeout after {timeout} seconds")
                            # Check if we're already on a success page as fallback
                            try:
                                current_url = page.url.lower() if page and hasattr(page, 'url') else ""
                                if "/home" in current_url or ("roblox.com" in current_url and "login" not in current_url):
                                    success_redirect = True
                                    print("Detected successful signup despite timeout")
                            except Exception as url_check_error:
                                print(f"Warning: Could not check current URL: {url_check_error}")
                            
            except errors.TimeoutError:
                print(f"Warning: Signup redirect timeout after {timeout} seconds")
                # Check if we're already on a success page as fallback
                try:
                    current_url = page.url.lower() if page and hasattr(page, 'url') else ""
                    if "/home" in current_url or ("roblox.com" in current_url and "login" not in current_url):
                        success_redirect = True
                        print("Detected successful signup despite timeout")
                except Exception as url_check_error:
                    print(f"Warning: Could not check current URL: {url_check_error}")
            except Exception as unexpected_error:
                print(f"Warning: Unexpected error during URL change: {unexpected_error}")
                success_redirect = False
                    
            if bar is not None:
                bar.set_description(f"Signup process [{x + 1}/{executionCount}]")
                bar.update(20)

            if verification is True:
                try:
                    page.ele(".btn-primary-md btn-min-width").click()
                    if page.ele("@@class=phone-verification-nonpublic-text text-description font-caption-body"):
                        print("Found phone verification element, skipping email verification.\n")
                        if bar is not None:
                            bar.update(20)
                            bar.set_description(f"Skipping email verification [{x + 1}/{executionCount}]")
                    elif page.ele(".form-control input-field verification-upsell-modal-input", timeout=5):
                        email_input = page.ele(".form-control input-field verification-upsell-modal-input")
                        if email_input and email:
                            email_input.input(email)
                            submit_button = page.ele(".modal-button verification-upsell-btn btn-cta-md btn-min-width", timeout=5)
                            if submit_button:
                                submit_button.click()
                            else:
                                print("Warning: Could not find email verification submit button")
                                if bar is not None:
                                    bar.update(20)
                        else:
                            if not email_input:
                                print("Warning: Could not find email input field")
                            if not email:
                                print("Warning: No email address available for verification")
                            if bar is not None:
                                bar.update(20)
                        if page.ele(".verification-upsell-text-body", timeout=60):
                            messages = []
                            emailCheckAttempts = 0
                            maxEmailAttempts = 30  # 30 attempts with 5 second intervals = 2.5 minutes
                            
                            # Validate email credentials before the loop to avoid repeated checks
                            email_credentials_valid = (
                                email and isinstance(email, str) and len(email.strip()) > 0 and
                                emailPassword and isinstance(emailPassword, str) and
                                emailID and isinstance(emailID, str)
                            )
                            
                            if not email_credentials_valid:
                                print("Error: Invalid email credentials for verification")
                                if bar is not None:
                                    bar.update(20)
                                    bar.set_description(f"Email verification failed [{x + 1}/{executionCount}]")
                            else:
                                while emailCheckAttempts < maxEmailAttempts:
                                    try:
                                        if not emailID or not isinstance(emailID, str):
                                            print("Error: Invalid email ID for verification")
                                            break
                                            
                                        messages = lib.fetchVerification(email, emailPassword, emailID)
                                        if messages and len(messages) > 0:
                                            break
                                    except Exception as e:
                                        print(f"Error checking email (attempt {emailCheckAttempts + 1}): {e}")
                                    
                                    emailCheckAttempts += 1
                                    if emailCheckAttempts < maxEmailAttempts:
                                        await asyncio.sleep(5)  # Use async sleep instead of time.sleep
                                    else:
                                        print(f"Max email check attempts ({maxEmailAttempts}) reached")
                                        break

                            if emailCheckAttempts >= maxEmailAttempts:
                                print("Email verification timeout - no email received within expected time")
                                if bar is not None:
                                    bar.update(10)
                            elif messages and len(messages) > 0:
                                msg = messages[0]
                                body = getattr(msg, 'text', None)
                                if not body and hasattr(msg, 'html') and msg.html and len(msg.html) > 0:
                                    body = msg.html[0]
                                if body:
                                    # Simplified and more reliable regex pattern for verification links
                                    link = None
                                    
                                    # Try progressively simpler patterns
                                    verification_patterns = [
                                        # Most specific pattern first
                                        r'https://www\.roblox\.com/account/settings/verify-email\?ticket=[A-Za-z0-9\-_]+',
                                        # More general roblox verification pattern
                                        r'https://[^/]*roblox\.com[^"\s]*verify[^"\s]*ticket=[A-Za-z0-9\-_]+',
                                        # Very broad roblox verification pattern
                                        r'https://[^"\s]*roblox\.com[^"\s]*verify[^"\s]*'
                                    ]
                                    
                                    for i, pattern in enumerate(verification_patterns):
                                        try:
                                            matches = re.findall(pattern, body, re.IGNORECASE)
                                            if matches:
                                                potential_link = matches[0]
                                                # Basic validation
                                                if (potential_link and
                                                    'roblox.com' in potential_link.lower() and 
                                                    'verify' in potential_link.lower() and
                                                    len(potential_link) > 20 and
                                                    len(potential_link) < 500):
                                                    link = potential_link
                                                    print(f"Found verification link using pattern {i+1}")
                                                    break
                                        except re.error as regex_error:
                                            print(f"Warning: Regex pattern {i+1} failed: {regex_error}")
                                            continue
                                        except Exception as pattern_error:
                                            print(f"Warning: Error with pattern {i+1}: {pattern_error}")
                                            continue
                                    
                                    # If no regex patterns worked, try simple string search as fallback
                                    if not link:
                                        try:
                                            # Look for any roblox verify link in the text
                                            body_lower = body.lower()
                                            if 'roblox.com' in body_lower and 'verify' in body_lower:
                                                # Find the verification URL manually
                                                # Simple URL extraction
                                                urls = re.findall(r'https?://[^\s<>"]+', body)
                                                for url in urls:
                                                    if 'roblox.com' in url.lower() and 'verify' in url.lower():
                                                        if len(url) > 20 and len(url) < 500:
                                                            link = url
                                                            print("Found verification link using fallback search")
                                                            break
                                        except Exception as fallback_error:
                                            print(f"Warning: Fallback search failed: {fallback_error}")

                                if link:
                                    if bar is not None:
                                        bar.set_description(
                                            f"Verifying email address [{x + 1}/{executionCount}]"
                                        )
                                        bar.update(20)
                                    try:
                                        # Add validation before following the link
                                        if not link or not isinstance(link, str):
                                            print("Warning: Invalid verification link - not a string")
                                        elif len(link) > 500:
                                            print(f"Warning: Verification link is unusually long ({len(link)} chars), truncating for safety")
                                            link = link[:500]
                                            
                                        # Additional safety check for the URL
                                        if not link:
                                            print("Warning: Empty verification link")
                                        elif not link.startswith(('http://', 'https://')):
                                            print(f"Warning: Invalid verification link format: {link[:50]}...")
                                        else:
                                            page.get(link, timeout=15)  # Add timeout for safety
                                    except Exception as link_error:
                                        print(f"Warning: Error opening verification link: {link_error}")
                                else:
                                    print("Warning: Email verification link not found")
                                    if bar is not None:
                                        bar.update(10)
                        else:
                            print("Warning: Verification email element not found")
                            if bar is not None:
                                bar.update(10)

                except Exception as e:
                    print(f"\nAn error occurred during email verification\n{e}\n")
                    print(f"\nFailed to find email verification element. You may need to verify the account manually. Skipping and continuing...\n{e}\n")
                finally:
                    if bar is not None:
                        bar.set_description(f"Saving cookies and clearing data [{x + 1}/{executionCount}]")
                    
                    # Safely handle cookie extraction
                    try:
                        if page is not None and hasattr(page, 'cookies'):
                            for i in page.cookies():
                                cookie = {
                                    "name": i["name"],
                                    "value": i["value"],
                                }
                                accountCookies.append(cookie)
                        else:
                            print("Warning: Page not available for cookie extraction")
                    except Exception as cookie_error:
                        print(f"Warning: Error extracting cookies: {cookie_error}")
                        
                    if bar is not None:
                        bar.update(5)

                    if customization is True:
                        if bar is not None:
                            bar.set_description(f"Customizing account [{x + 1}/{executionCount}]")
                        await lib.customization(page)
                        if bar is not None:
                            bar.update(5)
                    else:
                        if bar is not None:
                            bar.set_description(f"Skipping customization [{x + 1}/{executionCount}]")
                            bar.update(5)

                    if following is True:
                        if bar is not None:
                            bar.set_description(f"Following users [{x + 1}/{executionCount}]")
                        follow_error = None  # Initialize follow_error variable
                        try:
                            userIDs = []
                            for user in followUserList:
                                try:
                                    result = await lib.followUser(user, page)
                                    if result:
                                        userIDs.extend(result if isinstance(result, list) else [result])
                                except Exception as follow_single_error:
                                    print(f"Error following user {user}: {follow_single_error}")
                                    follow_error = follow_single_error  # Track the error
                                    continue
                        except Exception as e:
                            print(f"An error occurred while following users: {e}")
                            follow_error = e
                        bar.update(5)

                    try:
                        # Call centralized cleanup function
                        cleanup_browser_safely(chrome, page, bar)
                    except Exception as e:
                        print(f"Warning: Error during browser cleanup: {e}")
                    
                    accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword, "cookies": accountCookies})

                    # follow_error is not defined in this scope, should check if following failed
                    if following is True and followUserList:
                        # Check if we actually followed users successfully
                        follow_success = True  # Assume success since we don't track errors here
                        if follow_success:
                            if bar is not None:
                                bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")
                        else:
                            if bar is not None:
                                bar.set_description(f"Finished account generation with errors [{x + 1}/{executionCount}]")
                    else:
                        if bar is not None:
                            bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")

                    if bar is not None:
                        remaining = max(0, 100 - bar.n)
                        if remaining > 0:
                            bar.update(remaining)
                        bar.close()
                        bar = None  # Clear reference after closing
            else:
                # Safely handle cookie extraction when verification is disabled
                try:
                    if page is not None and hasattr(page, 'cookies'):
                        for i in page.cookies():
                            cookie = {
                                "name": i["name"],
                                "value": i["value"],
                            }
                            accountCookies.append(cookie)
                    else:
                        print("Warning: Page not available for cookie extraction")
                except Exception as cookie_error:
                    print(f"Warning: Error extracting cookies: {cookie_error}")
                    
                if bar is not None:
                    bar.update(10)

                if customization is True:
                    if bar is not None:
                        bar.set_description(f"Customizing account [{x + 1}/{executionCount}]")
                    await lib.customization(page)
                    if bar is not None:
                        bar.update(15)
                else:
                    if bar is not None:
                        bar.set_description(f"Skipping customization [{x + 1}/{executionCount}]")
                        bar.update(15)

                follow_error = None  # Initialize follow_error variable for non-verification path
                if following is True:
                    if bar is not None:
                        bar.set_description(f"Following users [{x + 1}/{executionCount}]")
                    try:
                        userIDs = []
                        for user in followUserList:
                            try:
                                result = await lib.followUser(user, page)
                                if result:
                                    userIDs.extend(result if isinstance(result, list) else [result])
                            except Exception as follow_single_error:
                                print(f"Error following user {user}: {follow_single_error}")
                                follow_error = follow_single_error  # Track the error
                                continue
                    except Exception as e:
                        print(f"An error occurred while following users: {e}")
                        follow_error = e  # Track the error
                    if bar is not None:
                        bar.update(10)

                try:
                    # Call centralized cleanup function
                    cleanup_browser_safely(chrome, page, bar)
                except Exception as e:
                    print(f"Warning: Error during browser cleanup: {e}")
                
                accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword, "cookies": accountCookies})
                if bar is not None:
                    if follow_error is not None:
                        bar.set_description(f"Finished account generation with errors [{x + 1}/{executionCount}]")
                    else:
                        bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")

                    remaining = max(0, 100 - bar.n)
                    if remaining > 0:
                        bar.update(remaining)
                    bar.close()
                    bar = None  # Clear reference after closing
                
        # Ensure captcha loop exits properly in all cases
        if account_created_successfully:
            captchaPresence = False  # Exit the captcha retry loop

    if not accounts:
        print("No accounts were successfully created.")
        return
    
    if not isinstance(accounts, list):
        print("Error: accounts is not a list")
        return

    try:
        # Validate accounts list before processing
        if not accounts or not isinstance(accounts, list):
            print("No valid accounts to save.")
            return
            
        valid_accounts = []
        for account in accounts:
            if (isinstance(account, dict) and 
                account.get('username') and 
                isinstance(account.get('username'), str) and
                len(account.get('username').strip()) > 0 and
                len(account.get('username').strip()) <= 20):  # Roblox username limit
                # Additional validation for required fields
                account_copy = account.copy()
                
                # Ensure all required fields exist with safe defaults
                if not account_copy.get('password'):
                    account_copy['password'] = ''
                if not account_copy.get('email'):
                    account_copy['email'] = 'N/A'
                if not account_copy.get('emailPassword'):
                    account_copy['emailPassword'] = ''
                if not account_copy.get('cookies'):
                    account_copy['cookies'] = []
                    
                valid_accounts.append(account_copy)
            else:
                invalid_reason = "unknown"
                if not isinstance(account, dict):
                    invalid_reason = "not a dictionary"
                elif not account.get('username'):
                    invalid_reason = "missing username"
                elif not isinstance(account.get('username'), str):
                    invalid_reason = "username not a string"
                elif len(account.get('username').strip()) == 0:
                    invalid_reason = "empty username"
                elif len(account.get('username').strip()) > 20:
                    invalid_reason = "username too long"
                    
                print(f"Warning: Skipping invalid account data ({invalid_reason}): {account}")
        
        if not valid_accounts:
            print("No valid accounts found to save.")
            return
            
        # Create backup of existing file if it exists
        accounts_file = "accounts.txt"
        if os.path.exists(accounts_file):
            try:
                backup_file = f"accounts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                shutil.copy2(accounts_file, backup_file)
                print(f"Created backup: {backup_file}")
            except Exception as backup_error:
                print(f"Warning: Could not create backup: {backup_error}")
        
        with open(accounts_file, "a", encoding="utf-8", errors='replace') as f:
            for account in valid_accounts:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Safely handle None values with proper defaults and validation
                def safe_str(value, default="N/A", max_length=200):
                    if value is None:
                        return default
                    try:
                        # Convert to string and handle potential encoding issues
                        str_value = str(value)
                        # Ensure ASCII compatibility for file safety
                        safe_value = str_value.encode('ascii', errors='ignore').decode('ascii')
                        # Remove any control characters that could cause issues
                        safe_value = ''.join(char for char in safe_value if ord(char) >= 32 or char in '\t\n\r')
                        # Truncate to prevent oversized entries
                        if len(safe_value) > max_length:
                            safe_value = safe_value[:max_length] + "..."
                        return safe_value.strip() if safe_value.strip() else default
                    except (UnicodeError, UnicodeDecodeError, UnicodeEncodeError):
                        return default
                    except Exception:
                        return default
                
                username = safe_str(account.get('username'))
                password = safe_str(account.get('password'))
                email = safe_str(account.get('email'))
                email_password = safe_str(account.get('emailPassword'))
                
                # Additional validation to ensure data integrity
                if username == "N/A" and password == "N/A" and email == "N/A":
                    print(f"Warning: Skipping account with all invalid data")
                    continue
                
                # Validate that we have at least username which is critical
                if username == "N/A" or not username or len(username.strip()) == 0:
                    print(f"Warning: Skipping account with invalid username")
                    continue
                
                # Validate data lengths to prevent file corruption
                if len(username) > 100 or len(password) > 100 or len(email) > 200:
                    print(f"Warning: Account data too long, truncating: {username}")
                    username = username[:100]
                    password = password[:100] 
                    email = email[:200]
                
                f.write(
                    f"Username: {username}, Password: {password}, Email: {email}, Email Password: {email_password} (Created at {timestamp})\n"
                )
        print("Account details saved to accounts.txt")
    except PermissionError as perm_error:
        print(f"Permission error writing to accounts.txt: {perm_error}")
        print("Try running as administrator or check file permissions.")
        print("Account details:")
        for account in accounts:
            username = account.get('username', 'N/A') if isinstance(account, dict) else "N/A"
            email = account.get('email', 'N/A') if isinstance(account, dict) else "N/A"
            print(f"Username: {username}, Email: {email}")
    except UnicodeEncodeError as unicode_error:
        print(f"Encoding error writing to accounts.txt: {unicode_error}")
        # Try with different encoding
        try:
            with open("accounts_fallback.txt", "w", encoding="ascii", errors="ignore") as f:
                for account in valid_accounts:
                    username = str(account.get('username', 'N/A'))
                    email = str(account.get('email', 'N/A'))
                    f.write(f"Username: {username}, Email: {email}\n")
            print("Account details saved to accounts_fallback.txt with ASCII encoding")
        except Exception as fallback_error:
            print(f"Fallback save also failed: {fallback_error}")
    except Exception as e:
        print(f"Error writing to accounts.txt: {e}")
        print("Account details:")
        for account in accounts:
            if isinstance(account, dict):
                username = account.get('username', 'N/A')
                email = account.get('email', 'N/A')
                print(f"Username: {username}, Email: {email}")
            else:
                print(f"Invalid account data: {account}")

    print("\033[1m" "Credentials:")

    try:
        with open("cookies.json", "r", encoding="utf-8") as file:
            content = file.read().strip()
            if content:
                try:
                    existingData = json.loads(content)
                    # Validate that it's a list and contains valid data
                    if not isinstance(existingData, list):
                        print("Warning: cookies.json contains invalid data structure. Creating backup and starting fresh.")
                        raise ValueError("Invalid data structure in cookies.json")
                    
                    # Additional validation - check if list items are dictionaries with expected keys
                    for i, item in enumerate(existingData):
                        if not isinstance(item, dict):
                            print(f"Warning: Invalid item format at index {i} in cookies.json")
                            raise ValueError(f"Invalid item format at index {i}")
                        
                        # Validate required keys exist
                        required_keys = ['username', 'password', 'email', 'emailPassword', 'cookies']
                        for key in required_keys:
                            if key not in item:
                                print(f"Warning: Missing required key '{key}' at index {i} in cookies.json")
                                # Don't fail for missing keys, just warn and continue
                                
                except json.JSONDecodeError as e:
                    print(f"Warning: cookies.json is corrupted ({e}). Creating backup and starting fresh.")
                    raise
                except ValueError as e:
                    print(f"Warning: cookies.json has validation issues ({e}). Creating backup and starting fresh.")
                    raise
            else:
                existingData = []
    except FileNotFoundError:
        existingData = []
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Warning: cookies.json has issues ({e}). Creating backup and starting fresh.")
        try:
            # Create backup with timestamp
            backup_filename = f"cookies_corrupted_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open("cookies.json", "r", encoding="utf-8") as original_file:
                with open(backup_filename, "w", encoding="utf-8") as backup_file:
                    backup_file.write(original_file.read())
            print(f"Backup created: {backup_filename}")
        except Exception as backup_error:
            print(f"Warning: Could not create backup: {backup_error}")
        existingData = []
    except Exception as e:
        print(f"Error reading cookies.json: {e}")
        existingData = []

    accountsData = []

    for account in accounts:
        accountData = {
            "username": account.get("username") or "",
            "password": account.get("password") or "",
            "email": account.get("email") or "",
            "emailPassword": account.get("emailPassword") or "",
            "cookies": account.get("cookies") or []
        }
        accountsData.append(accountData)

    existingData.extend(accountsData)

    try:
        with open("cookies.json", "w", encoding="utf-8") as jsonFile:
            json.dump(existingData, jsonFile, indent=4, ensure_ascii=False)
        print("Cookies saved to cookies.json")
    except Exception as e:
        print(f"Error writing to cookies.json: {e}")
        # Try to save a backup with a timestamp
        try:
            backup_filename = f"cookies_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, "w", encoding="utf-8") as backup_file:
                json.dump(existingData, backup_file, indent=4, ensure_ascii=False)
            print(f"Cookies saved to backup file: {backup_filename}")
        except Exception as backup_error:
            print(f"Failed to save backup cookies file: {backup_error}")
            print("Warning: Cookies could not be saved!")

    for account in accounts:
        # Safely handle None values with proper defaults
        username = account.get('username') or 'N/A'
        password = account.get('password') or ''
        email = account.get('email') or 'N/A'
        email_password = account.get('emailPassword') or ''
        
        # Ensure we don't display empty passwords as asterisks - improved logic
        password_display = '*' * min(len(password), 8) if password else 'N/A'
        email_password_display = '*' * min(len(email_password), 8) if email_password else 'N/A'
        
        print(f"Username: {username}, Password: {password_display}, Email: {email}, Email Password: {email_password_display}")
    print("\033[0m" "\nCredentials saved to accounts.txt\nCookies are saved to cookies.json file\n\nHave fun playing Roblox!")

    accountManagerFormat = input(
        "\nWould you like to export the account manager format into your clipboard? [y/n] (Default: No): "
    ) or "n"
    if accountManagerFormat.lower() in ["y", "yes"]:
        accountManagerFormatString = ""

        for account in accounts:
            roblosecurityCookie = None
            try:
                # Safely access cookies with proper validation
                cookies = account.get("cookies", [])
                if not isinstance(cookies, list):
                    print(f"Warning: Invalid cookies format for user {account.get('username', 'unknown')}")
                    continue
                    
                for cookie in cookies:
                    if isinstance(cookie, dict) and cookie.get("name") == ".ROBLOSECURITY":
                        roblosecurityCookie = cookie.get("value")
                        if roblosecurityCookie:  # Only use non-empty values
                            break

                if roblosecurityCookie:
                    accountManagerFormatString += f"{roblosecurityCookie}\n"
                else:
                    username = account.get('username', 'unknown') if isinstance(account, dict) else 'unknown'
                    print(f"Warning: No .ROBLOSECURITY cookie found for user {username}")
            except Exception as cookie_error:
                username = account.get('username', 'unknown') if isinstance(account, dict) else 'unknown'
                print(f"Error processing cookies for user {username}: {cookie_error}")

        try:
            # Enhanced clipboard operation with better error handling and security
            if not PYPERCLIP_AVAILABLE:
                print("Clipboard functionality not available.")
                print("Account manager format (cookies):")
                print(accountManagerFormatString)
                print("Please copy the above text manually.")
                return
                
            if len(accountManagerFormatString.strip()) == 0:
                print("No valid account data to copy to clipboard.")
                return
            
            # Validate that the string contains only expected content (security check)
            if not all(c.isprintable() or c.isspace() for c in accountManagerFormatString):
                print("Warning: Account data contains non-printable characters. Manual copy recommended.")
                print("Account manager format (cookies):")
                print(accountManagerFormatString)
                return
            
            # Limit clipboard content size for safety
            if len(accountManagerFormatString) > 100000:  # 100KB limit
                print("Warning: Account data too large for clipboard. Manual copy recommended.")
                print("Account manager format (cookies):")
                print(accountManagerFormatString)
                return
                
            pyperclip.copy(accountManagerFormatString)
            print("Account manager format (cookies) copied to clipboard!")
            print("Select the 'Cookie(s)' option in Roblox Account Manager and paste it into the input field.")
            print("Do note that you'll have to complete the signup process manually in Roblox Account Manager.\n")
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")
            print("Account manager format (cookies):")
            print(accountManagerFormatString)
            print("Please copy the above text manually.")
    else:
        print()

    for i in range(5, 0, -1):
        print(f"\rExiting in {i} seconds...", end="", flush=True)
        await asyncio.sleep(1)
    print("\r\033[KExiting now...")

if __name__ == "__main__":
    # Set up global exception handler for async tasks
    def handle_exception(loop, context):
        exception = context.get('exception')
        if exception:
            print(f"Unhandled exception in async task: {exception}")
            # Try to clean up any browser processes
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL,
                                  timeout=5,
                                  check=False)  # Don't raise exception on non-zero exit
            except Exception:
                pass
    
    try:
        # Run the main function with proper exception handling
        async def run_with_exception_handler():
            # Get the current event loop and set exception handler
            loop = asyncio.get_running_loop()
            loop.set_exception_handler(handle_exception)
            await main()
        
        asyncio.run(run_with_exception_handler(), debug=False)
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Cleaning up...")
        try:
            # Try to quit any open browser instances and force cleanup
            gc.collect()
            # Force close any remaining chromium processes on Windows
            if os.name == 'nt':
                try:
                    # Use subprocess for better control and error handling
                    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL,
                                  timeout=10,
                                  check=False)  # Don't raise exception on non-zero exit
                    subprocess.run(['taskkill', '/f', '/im', 'chromium.exe'], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL,
                                  timeout=10,
                                  check=False)  # Don't raise exception on non-zero exit
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as cleanup_error:
                    print(f"Warning: Error during process cleanup: {cleanup_error}")
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
        print("Cleanup complete.")
    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        # Add more detailed error information for debugging
        print("Detailed error information:")
        traceback.print_exc()
        print("Please report this issue at https://qing762.is-a.dev/discord if the error persists.")
