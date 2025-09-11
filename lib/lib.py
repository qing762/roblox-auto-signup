import random
import platform
import requests
import sys
import uuid
import hmac
import os
import hashlib
import re
import asyncio
import time
from DrissionPage import errors, SessionPage
from zipfile import ZipFile

# Import pymailtm with error handling
try:
    from pymailtm import MailTm, Account
    PYMAILTM_AVAILABLE = True
except ImportError:
    PYMAILTM_AVAILABLE = False
    print("Warning: pymailtm not available - email verification will be disabled")
    # Create dummy classes to prevent import errors
    class MailTm:
        pass
    class Account:
        pass

# Import threading with global error handling
try:
    import threading
    THREADING_AVAILABLE = True
except ImportError:
    THREADING_AVAILABLE = False
    print("Warning: Threading module not available - some features may have reduced performance")

# Pre-compiled regex patterns for better performance and error prevention
# Safely compile patterns with error handling
def _compile_regex_patterns():
    """Safely compile regex patterns with proper error handling"""
    patterns = {}
    
    pattern_definitions = {
        'USERNAME_PATTERN': r'^[a-zA-Z0-9_]+$',
        'VERSION_PATTERN': r'^[a-zA-Z0-9_\-\.\+\/=]+$',
        'IP_PORT_PATTERN': r'^(\d{1,3}\.){3}\d{1,3}:\d{1,5}$'
    }
    
    for name, pattern_str in pattern_definitions.items():
        try:
            compiled_pattern = re.compile(pattern_str)
            patterns[name] = compiled_pattern
        except re.error as pattern_error:
            print(f"Warning: Error compiling {name}: {pattern_error}")
            patterns[name] = None
        except Exception as e:
            print(f"Warning: Unexpected error compiling {name}: {e}")
            patterns[name] = None
    
    return patterns

# Initialize patterns safely
try:
    _compiled_patterns = _compile_regex_patterns()
    USERNAME_PATTERN = _compiled_patterns.get('USERNAME_PATTERN')
    VERSION_PATTERN = _compiled_patterns.get('VERSION_PATTERN') 
    IP_PORT_PATTERN = _compiled_patterns.get('IP_PORT_PATTERN')
except Exception as init_error:
    print(f"Warning: Error initializing regex patterns: {init_error}")
    USERNAME_PATTERN = None
    VERSION_PATTERN = None
    IP_PORT_PATTERN = None

# Compile dangerous proxy patterns with error handling
DANGEROUS_PROXY_PATTERNS = []

def _compile_security_patterns():
    """Safely compile security patterns with proper error handling"""
    global DANGEROUS_PROXY_PATTERNS
    DANGEROUS_PROXY_PATTERNS = []
    
    dangerous_pattern_strings = [
        r'[;&|`$(){}<>]',   # Shell metacharacters
        r'\\[rnt]',         # Escape sequences  
        r'%[0-9a-fA-F]{2}', # URL encoded characters that could be dangerous
        r'javascript:',     # JavaScript protocol
        r'data:',           # Data protocol
        r'file:',           # File protocol
        r'ftp:',            # FTP protocol
        r'ldap:',           # LDAP protocol
        r'\\\\',            # UNC paths
        r'[<>"\']',         # HTML/XML injection chars
        r'\.\./',           # Path traversal
        r'%2e%2e%2f',       # Encoded path traversal
        r'\\x[0-9a-fA-F]{2}', # Hex escape sequences
        r'exec\s*\(',       # Execution functions
        r'eval\s*\(',       # Evaluation functions
        r'system\s*\(',     # System calls
    ]
    
    compiled_count = 0
    for i, pattern_str in enumerate(dangerous_pattern_strings):
        try:
            compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
            DANGEROUS_PROXY_PATTERNS.append(compiled_pattern)
            compiled_count += 1
        except re.error as e:
            print(f"Warning: Failed to compile regex pattern '{pattern_str}': {e}")
            continue
        except Exception as e:
            print(f"Warning: Unexpected error compiling pattern '{pattern_str}': {e}")
            continue
    
    # Ensure we have at least basic security patterns
    if compiled_count == 0:
        print("Warning: No security patterns compiled successfully. Adding basic fallback patterns.")
        try:
            # Add basic fallback patterns that are less likely to fail
            basic_patterns = [
                (r'[;&|`]', 'basic shell chars'),
                (r'javascript:', 'javascript protocol'),
                (r'<script', 'script tag')
            ]
            for pattern_str, description in basic_patterns:
                try:
                    DANGEROUS_PROXY_PATTERNS.append(re.compile(pattern_str, re.IGNORECASE))
                    compiled_count += 1
                    print(f"Added fallback pattern: {description}")
                except Exception as fallback_error:
                    print(f"Warning: Could not compile fallback pattern '{description}': {fallback_error}")
                    continue
        except Exception as fallback_error:
            print(f"Warning: Could not compile fallback patterns: {fallback_error}")
    
    # Ultimate fallback - if nothing works, create a minimal security check
    if compiled_count == 0:
        print("Warning: No security patterns available. Security validation will be minimal.")
        # Create a simple function-based check as fallback
        def basic_security_check(text):
            if not isinstance(text, str):
                return True  # Consider non-strings as suspicious
            dangerous_chars = ['&', ';', '|', '`', '$']
            return any(char in text for char in dangerous_chars)  # Return True if dangerous
        
        # Store the function as a fallback in the module scope
        _basic_security_check = basic_security_check
        DANGEROUS_PROXY_PATTERNS = []  # Empty list but we have the function
    else:
        print(f"Security patterns initialized: {compiled_count} patterns compiled successfully.")

# Initialize patterns safely
try:
    _compile_security_patterns()
except Exception as init_error:
    print(f"Warning: Error initializing security patterns: {init_error}")
    # Ensure we have at least one basic pattern for security
    try:
        DANGEROUS_PROXY_PATTERNS = [re.compile(r'[;&|`]', re.IGNORECASE)]
        print("Using minimal fallback security patterns.")
    except Exception:
        DANGEROUS_PROXY_PATTERNS = []
        print("Warning: No security patterns available - security validation will be disabled!")


def getResourcePath(relative_path):
    """Get absolute path to resource, works for both development and PyInstaller bundle"""
    # Enhanced input validation - prevent path traversal attacks
    if not relative_path or not isinstance(relative_path, str):
        raise ValueError("Invalid relative_path parameter")
    
    # Length validation to prevent DoS
    if len(relative_path) > 500:
        raise ValueError("Path too long")
    
    # Normalize path separators for the current OS
    relative_path = relative_path.replace('/', os.sep).replace('\\', os.sep)
    
    # Enhanced security check for path traversal with stricter validation
    path_parts = relative_path.split(os.sep)
    for part in path_parts:
        # Reject any path traversal attempts
        if part in ('..', '.'):
            raise ValueError(f"Path traversal detected: {relative_path}")
        # Reject hidden files/directories that don't have safe extensions
        if part.startswith('.') and part != '.':
            safe_extensions = {'.txt', '.py', '.json', '.js', '.css', '.html', 
                             '.png', '.ico', '.jpg', '.jpeg', '.gif', '.svg', '.md'}
            if not any(part.endswith(ext) for ext in safe_extensions):
                raise ValueError(f"Hidden path component detected: {relative_path}")
        # Reject parts with null bytes or other dangerous characters
        if '\x00' in part or any(ord(c) < 32 for c in part if c not in '\t\n\r'):
            raise ValueError(f"Dangerous characters in path: {relative_path}")
        # Additional check for very long path components that could cause buffer issues
        if len(part) > 255:  # Max filename length on most systems
            raise ValueError(f"Path component too long: {relative_path}")
    
    # Additional security: ensure relative path doesn't start with separator
    if relative_path.startswith(os.sep) or relative_path.startswith('/') or relative_path.startswith('\\'):
        raise ValueError(f"Absolute path not allowed: {relative_path}")
    
    # Whitelist allowed path prefixes for additional security
    allowed_prefixes = ['lib/', 'lib\\', 'version.txt', 'accounts.txt', 'cookies.json', 'analytics.txt']
    normalized_relative = relative_path.replace('\\', '/')
    
    # Check if path matches any allowed prefix or is exactly an allowed file
    is_allowed = False
    for prefix in allowed_prefixes:
        normalized_prefix = prefix.replace('\\', '/')
        if (normalized_relative.startswith(normalized_prefix) or 
            normalized_relative == normalized_prefix.rstrip('/')):
            is_allowed = True
            break
    
    if not is_allowed:
        raise ValueError(f"Path not in allowed locations: {relative_path}")
    
    # PyInstaller creates a temporary folder and stores path in _MEIPASS
    try:
        if hasattr(sys, '_MEIPASS') and sys._MEIPASS:
            base_path = sys._MEIPASS
        else:
            # Normal execution - get directory of current file or script directory
            if '__file__' in globals():
                base_path = os.path.dirname(os.path.abspath(__file__))
                # Go up one level since we're in lib/
                base_path = os.path.dirname(base_path)
            else:
                base_path = os.path.abspath(".")
    except (AttributeError, OSError):
        # Enhanced fallback - try multiple approaches
        try:
            # Try to get the directory of the main script
            if sys.argv and sys.argv[0]:
                base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
            else:
                base_path = os.path.abspath(".")
        except (OSError, IndexError):
            base_path = os.getcwd()  # Last resort
    
    try:
        full_path = os.path.join(base_path, relative_path)
        # Normalize and ensure absolute path
        normalized_path = os.path.abspath(os.path.normpath(full_path))
        
        # Enhanced security check: ensure the resolved path is still within the base directory
        normalized_base = os.path.abspath(os.path.normpath(base_path))
        common_path = os.path.commonpath([normalized_path, normalized_base])
        if common_path != normalized_base:
            raise ValueError(f"Path escapes base directory: {relative_path}")
        
        # Additional check: ensure no symbolic link traversal
        try:
            real_path = os.path.realpath(normalized_path)
            real_base = os.path.realpath(normalized_base)
            common_real = os.path.commonpath([real_path, real_base])
            if common_real != real_base:
                raise ValueError(f"Symbolic link traversal detected: {relative_path}")
        except (OSError, ValueError):
            # If realpath fails, use the normalized path but log warning
            print(f"Warning: Could not verify symbolic links for {relative_path}")
        
        return normalized_path
    except (OSError, ValueError) as path_error:
        print(f"Warning: Error constructing path for {relative_path}: {path_error}")
        raise ValueError(f"Invalid path: {relative_path}")
    except Exception as unexpected_error:
        print(f"Warning: Unexpected error in getResourcePath: {unexpected_error}")
        raise ValueError(f"Path processing failed: {relative_path}")


class UsernameGenerator:
    # SOURCE: https://github.com/mrsobakin/pungen. Kudos to mrsobakin for the original code.
    CONSONANTS = "bcdfghjklmnpqrstvwxyz"
    VOWELS = "aeiou"

    CONS_WEIGHTED = ("tn", "rshd", "lfcm", "gypwb", "vbjxq", "z")
    VOW_WEIGHTED = ("eao", "iu")
    DOUBLE_CONS = ("he", "re", "ti", "hi", "to", "ll", "tt", "nn", "pp", "th", "nd", "st", "qu")
    DOUBLE_VOW = ("ee", "oo", "ei", "ou", "ai", "ea", "an", "er", "in", "on", "at", "es", "en", "of", "ed", "or", "as")

    def __init__(self, min_length, max_length=None):
        self.set_length(min_length, max_length)

    def set_length(self, min_length, max_length):
        if not max_length:
            max_length = min_length

        # Ensure minimum length is at least 3 (Roblox requirement)
        min_length = max(3, min_length)
        # Ensure maximum length doesn't exceed Roblox limit
        max_length = min(20, max_length)
        
        # Validate length parameters
        if min_length > max_length:
            max_length = min_length
            
        self.min_length = min_length
        self.max_length = max_length

    def generate(self):
        username, is_double, num_length = "", False, 0

        if random.randrange(10) > 0:
            is_consonant = True
        else:
            is_consonant = False

        length = random.randrange(self.min_length, self.max_length + 1)
        
        # Ensure length doesn't exceed Roblox's limit
        length = min(length, 20)
        # Ensure minimum length
        length = max(length, 3)

        # Initialize variables with safe defaults
        letterLength = max(3, length)  # Minimum 3 letters
        num_length = 0  # Default no numbers
        
        if random.randrange(5) == 0:
            num_length = min(random.randrange(3) + 1, max(0, length - 3))  # Ensure minimum letters
            letterLength = length - num_length
            
            # Safety check to ensure valid ranges
            if letterLength < 3:
                letterLength = 3
                num_length = max(0, length - letterLength)
            
            # Validate that total length doesn't exceed limits
            if letterLength + num_length > 20:
                letterLength = min(17, letterLength)  # Cap letters at 17 to allow for numbers
                num_length = max(0, min(3, 20 - letterLength))  # Cap numbers at remaining space
                
        # Additional validation to ensure we don't exceed limits
        if letterLength + num_length > 20:
            letterLength = 17
            num_length = 3
        
        # Ensure we have at least minimum length
        if letterLength + num_length < 3:
            letterLength = 3
            num_length = 0
                
        for j in range(letterLength):
            if len(username) > 0:
                if username[-1] in self.CONSONANTS:
                    is_consonant = False
                elif username[-1] in self.VOWELS:
                    is_consonant = True
            if not is_double:
                if random.randrange(8) == 0 and len(username) < max(3, letterLength - 1):  # Ensure minimum 3
                    is_double = True
                if is_consonant:
                    username += self._get_consonant(is_double)
                else:
                    username += self._get_vowel(is_double)
                is_consonant = not is_consonant
            else:
                is_double = False
        if random.randrange(2) == 0:
            username = username[:1].upper() + username[1:]
        if num_length > 0:
            for j in range(num_length):
                username += str(random.randrange(10))

        # Comprehensive final length and validation checks with strict boundaries
        # First ensure we don't exceed Roblox's limit (enforce strictly)
        max_length = 20  # Roblox hard limit
        min_length = 3   # Roblox minimum
        
        if len(username) > max_length:
            username = username[:max_length]
        
        # Ensure minimum length with proper validation
        if len(username) < min_length:
            # Add numbers to reach minimum length, but ensure total doesn't exceed max
            needed_chars = min_length - len(username)
            available_space = max_length - len(username)
            chars_to_add = min(needed_chars, available_space)
            
            for i in range(chars_to_add):
                if len(username) < max_length:
                    username += str(random.randint(0, 9))
                else:
                    break
            
            # If still too short after adding numbers, use guaranteed valid fallback
            if len(username) < min_length:
                # Create a username that exactly meets requirements
                fallback_num = random.randint(100, 999)
                username = f"usr{fallback_num}"  # Exactly 6 characters
                if len(username) > max_length:
                    username = username[:max_length]
        
        # Final boundary enforcement - ensure we never exceed limits
        username = username[:max_length]  # Hard truncation
        if len(username) < min_length:
            username = "usr123"  # Emergency fallback that meets all requirements
            
        # Ensure username contains only valid characters
        try:
            if USERNAME_PATTERN and USERNAME_PATTERN.match(username):
                pass  # Username is valid
            elif not USERNAME_PATTERN:
                # Fallback validation if pattern compilation failed
                if not re.match(r'^[a-zA-Z0-9_]+$', username):
                    username = f"user{random.randint(100, 999)}"
            else:
                # Username doesn't match pattern
                username = f"user{random.randint(100, 999)}"
        except (re.error, AttributeError):
            # Fallback to simple safe username
            username = f"user{random.randint(100, 999)}"

        # Final safety check - ensure the username is not empty
        if not username or len(username.strip()) == 0:
            username = f"fallback{random.randint(100, 999)}"
        
        # Absolute final check to ensure length constraints
        username = username[:20]  # Truncate if somehow still too long
        if len(username) < 3:
            username = "usr123"  # Emergency fallback

        return username

    def _get_consonant(self, is_double):
        if is_double:
            return random.choice(self.DOUBLE_CONS)
        else:
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
                weight = 5  # Set weight to 5 for the else case
            
            # Bounds checking with safety fallback
            try:
                if 0 <= weight < len(self.CONS_WEIGHTED) and len(self.CONS_WEIGHTED[weight]) > 0:
                    selected_consonant_group = self.CONS_WEIGHTED[weight]
                    if len(selected_consonant_group) > 0:  # Extra safety check
                        return selected_consonant_group[random.randrange(len(selected_consonant_group))]
                    else:
                        return random.choice(self.CONSONANTS)
                else:
                    # Fallback to basic consonant if weight is out of bounds
                    return random.choice(self.CONSONANTS)
            except (IndexError, ValueError):
                # Safety fallback for any unexpected issues
                return random.choice(self.CONSONANTS)

    def _get_vowel(self, is_double):
        if is_double:
            return random.choice(self.DOUBLE_VOW)
        else:
            i = random.randrange(100)
            if i < 70:
                weight = 0
            else:
                weight = 1
            # return a random vowel based on the weight with bounds checking
            try:
                if 0 <= weight < len(self.VOW_WEIGHTED) and len(self.VOW_WEIGHTED[weight]) > 0:
                    selected_vowel_group = self.VOW_WEIGHTED[weight]
                    if len(selected_vowel_group) > 0:  # Extra safety check
                        return selected_vowel_group[random.randrange(len(selected_vowel_group))]
                    else:
                        return random.choice(self.VOWELS)
                else:
                    # Fallback to basic vowel if weight is out of bounds
                    return random.choice(self.VOWELS)
            except (IndexError, ValueError):
                # Safety fallback for any unexpected issues
                return random.choice(self.VOWELS)


class Main():
    # Constants to avoid magic numbers
    CACHE_TTL = 3600  # 1 hour cache TTL
    MAX_USERNAME_ATTEMPTS = 100
    MAX_API_FAILURES = 5
    ROBLOX_USERNAME_LIMIT = 20
    MAX_EMAIL_RETRIES = 5
    MAX_FOLLOWS_PER_MINUTE = 10
    
    def __init__(self):
        self._ungoogled_path_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # Cache for 5 minutes to prevent memory leaks
        
        # Word lists cache to improve performance
        self._word_lists_cache = None
        self._word_lists_cache_timestamp = None
        self._word_lists_cache_ttl = 1800  # Cache word lists for 30 minutes
        
        # Add thread safety for cache operations using global threading availability
        if THREADING_AVAILABLE:
            self._cache_lock = threading.RLock()  # Use RLock for reentrant access
        else:
            self._cache_lock = None  # Fallback if threading not available
        
    def downloadUngoogledChromium(self):
        system = platform.system()
        page = None
        versions = []
        try:
            if system == "Windows":
                page = SessionPage()
                page.get("https://ungoogled-software.github.io/ungoogled-chromium-binaries/releases/windows/64bit/")
                for x in page.eles("@tag()=li"):
                    try:
                        version_element = x.ele("@tag()=a")
                        if version_element:
                            versionText = version_element.text
                            if versionText:
                                versions.append(versionText)
                    except Exception as e:
                        print(f"Warning: Error parsing version element: {e}")
                        continue
            else:
                print(f"{system} OS is not supported for automated installation yet. Please make sure Ungoogled Chromium is installed in order to use NopeCHA.")
                return f"{system} OS is not supported for automated installation."
        except Exception as e:
            print(f"Error fetching ungoogled chromium versions: {e}")
            return f"Error fetching versions: {e}"
        finally:
            # Improved cleanup process with better error handling
            if page:
                try:
                    # Close page first
                    if hasattr(page, 'close'):
                        page.close()
                except Exception as close_error:
                    print(f"Warning: Error during page close: {close_error}")
                
                try:
                    # Then quit
                    if hasattr(page, 'quit'):
                        page.quit()
                except Exception as quit_error:
                    print(f"Warning: Error during page quit: {quit_error}")
                finally:
                    page = None  # Ensure reference is cleared
                    
                # Force garbage collection to help with cleanup
                try:
                    import gc
                    gc.collect()
                except Exception:
                    pass
        try:
            filtered_versions = []
            for ver in versions:
                if ver and "." in ver and len(ver.split(".")) >= 2:
                    try:
                        major_version = int(ver.split(".")[0])
                        # Simple range check - use reasonable bounds
                        if 70 <= major_version <= 200:  # Reasonable range for Chrome versions
                            filtered_versions.append(ver)
                    except (ValueError, IndexError):
                        continue
            
            if not filtered_versions:
                # Use any version with dots as fallback
                filtered_versions = [v for v in versions if v and "." in v and len(v.split(".")) >= 2]
                
            versions = filtered_versions
        except Exception as e:
            print(f"Error during version filtering: {e}")
            # Basic fallback filtering
            versions = [v for v in versions if v and "." in v]
        if not versions:
            return "No compatible versions found."
        if system == "Windows":
            unGoogledChromium = f"./lib/ungoogled-chromium_{versions[0]}.1_windows_x64"
            if os.path.exists(unGoogledChromium):
                return "Ungoogled Chromium already exists."
        prompt = input("Would you like to install Ungoogled Chromium for NopeCHA to work? [y/n] (Default: Yes): ")
        if prompt.lower() == "y" or prompt == "" or prompt == "yes":
            if system == "Windows":
                if not os.path.exists(f"{unGoogledChromium}.zip"):
                    print(f"Downloading Ungoogled Chromium version {versions[0]} for Windows...")
                    print("This may take a while, please be patient.... Please do not close the program/terminal.")
                    try:
                        url = f"https://github.com/ungoogled-software/ungoogled-chromium-windows/releases/download/{versions[0]}.1/ungoogled-chromium_{versions[0]}.1_windows_x64.zip"
                        r = requests.get(url, stream=True)
                        r.raise_for_status()
                        try:
                            with open(f"{unGoogledChromium}.zip", "wb") as file:
                                for chunk in r.iter_content(chunk_size=1024):
                                    if chunk:
                                        file.write(chunk)
                        finally:
                            r.close()
                        print("Download complete. Proceeding to extract the zip file...")
                    except requests.exceptions.RequestException as e:
                        return f"Download failed: {e}"
                    except PermissionError as e:
                        return f"Permission error: {e}. Please check file permissions or run with administrator privileges."
                    except IOError as e:
                        return f"File I/O error: {e}"
                else:
                    print("Zip file already exists. Proceeding to extract...")
                try:
                    with ZipFile(f"{unGoogledChromium}.zip", 'r') as browserObject:
                        browserObject.extractall(unGoogledChromium)
                    print("Extraction complete. Deleting zip file...")
                    os.remove(f"{unGoogledChromium}.zip")
                    return "Ungoogled Chromium has been downloaded successfully."
                except Exception as e:
                    # Clean up zip file even if extraction fails
                    try:
                        os.remove(f"{unGoogledChromium}.zip")
                    except Exception:
                        pass  # If cleanup fails, continue anyway
                    return f"Extraction failed: {e}"
            else:
                return f"{system} OS is not supported for automated installation."
        else:
            return "Download cancelled by user."

    def returnUngoogledChromiumPath(self):
        import time
        system = platform.system()
        if system != "Windows":
            return None
        
        # Use cache if available and recent (within 1 hour) - with better validation and thread safety
        current_time = time.time()
        
        def check_cache():
            if (self._ungoogled_path_cache is not None and 
                self._cache_timestamp is not None and 
                current_time - self._cache_timestamp < 3600):
                # Verify cached path still exists
                try:
                    if os.path.exists(self._ungoogled_path_cache):
                        chrome_exe_path = os.path.join(self._ungoogled_path_cache, "chrome.exe")
                        if os.path.exists(chrome_exe_path) and os.path.isfile(chrome_exe_path):
                            return self._ungoogled_path_cache
                        else:
                            print("Warning: Cached ungoogled chromium path exists but chrome.exe not found, invalidating cache")
                    else:
                        print("Warning: Cached ungoogled chromium path no longer exists, invalidating cache")
                        
                    # Invalidate cache if validation fails
                    self._ungoogled_path_cache = None
                    self._cache_timestamp = None
                    return None
                except (OSError, PermissionError) as cache_check_error:
                    print(f"Warning: Error checking cached path: {cache_check_error}, invalidating cache")
                    self._ungoogled_path_cache = None
                    self._cache_timestamp = None
                    return None
            return None
        
        # Check cache with thread safety
        if self._cache_lock:
            with self._cache_lock:
                cached_result = check_cache()
                if cached_result:
                    return cached_result
        else:
            cached_result = check_cache()
            if cached_result:
                return cached_result
            
        page = None
        try:
            page = SessionPage()
            versions = []
            try:
                page.get("https://ungoogled-software.github.io/ungoogled-chromium-binaries/releases/windows/64bit/")
                for x in page.eles("@tag()=li"):
                    try:
                        version_element = x.ele("@tag()=a")
                        if version_element:
                            versionText = version_element.text
                            if versionText and isinstance(versionText, str) and versionText.strip():
                                versions.append(versionText.strip())
                    except Exception as e:
                        print(f"Warning: Error parsing version element: {e}")
                        continue
            except Exception as e:
                print(f"Error fetching ungoogled chromium versions: {e}")
                return self._ungoogled_path_cache  # Return cached value if available
        except Exception as outer_e:
            print(f"Error initializing session: {outer_e}")
            return self._ungoogled_path_cache  # Return cached value if available
        finally:
            # Ensure page is properly closed to prevent memory leaks in all cases
            if page:
                try:
                    # More comprehensive cleanup process
                    # First close any downloads or active operations
                    if hasattr(page, 'stop'):
                        try:
                            page.stop()
                        except Exception:
                            pass
                    
                    # Then close any open tabs
                    if hasattr(page, 'tabs') and page.tabs:
                        for tab in page.tabs:
                            try:
                                if hasattr(tab, 'close'):
                                    tab.close()
                            except Exception:
                                pass
                    
                    # Close the main page/session
                    if hasattr(page, 'close'):
                        page.close()
                        
                except Exception as close_error:
                    print(f"Warning: Error during page cleanup: {close_error}")
                
                try:
                    # Then try to quit properly with timeout
                    if hasattr(page, 'quit'):
                        page.quit()
                except Exception as quit_error:
                    print(f"Warning: Error during page quit: {quit_error}")
                
                # Clear the page reference
                page = None
                    
                # Force garbage collection to help with cleanup
                try:
                    import gc
                    gc.collect()
                except Exception:
                    pass
            
        try:
            filtered_versions = []
            for ver in versions:
                if ver and "." in ver:
                    try:
                        # More robust version validation
                        version_parts = ver.split(".")
                        if len(version_parts) >= 2 and version_parts[0].isdigit():
                            major_version = int(version_parts[0])
                            # Use dynamic version range with more generous upper bound
                            try:
                                current_year = time.gmtime().tm_year
                                # Chrome started in 2008, increased multiplier for future versions
                                max_reasonable_version = (current_year - 2008) * 20
                            except Exception:
                                # Fallback to a reasonable static upper bound
                                max_reasonable_version = 500
                            if 50 <= major_version <= min(500, max_reasonable_version):
                                filtered_versions.append(ver)
                    except (ValueError, IndexError) as e:
                        print(f"Warning: Skipping invalid version format '{ver}': {e}")
                        continue
            versions = filtered_versions
        except Exception as filter_error:
            print(f"Warning: Error filtering versions: {filter_error}")
            # Fallback to basic filtering
            versions = [v for v in versions if v and "." in v and len(v.split(".")) >= 2]
        if not versions:
            print("No compatible versions found.")
            return None
        
        unGoogledChromium = f"./lib/ungoogled-chromium_{versions[0]}.1_windows_x64"
        result = unGoogledChromium if os.path.exists(unGoogledChromium) else None
        
        # Cache the result with thread safety
        if self._cache_lock:
            with self._cache_lock:
                self._ungoogled_path_cache = result
                self._cache_timestamp = current_time
        else:
            self._ungoogled_path_cache = result
            self._cache_timestamp = current_time
        
        return result
    
    def generateUsername(self, scrambled=False):
        """Generate a username based on word combinations or scrambled format"""
        if scrambled is False:
            try:
                # Check if we have cached word lists that are still valid with thread safety
                current_time = time.time()
                
                def get_cached_words():
                    if (self._word_lists_cache is not None and 
                        self._word_lists_cache_timestamp is not None and 
                        current_time - self._word_lists_cache_timestamp < self._word_lists_cache_ttl):
                        return self._word_lists_cache
                    return None
                
                def set_cached_words(word_lists):
                    self._word_lists_cache = word_lists
                    self._word_lists_cache_timestamp = current_time
                
                # Thread-safe cache access
                if self._cache_lock:
                    with self._cache_lock:
                        cached_words = get_cached_words()
                else:
                    cached_words = get_cached_words()
                
                if cached_words:
                    # Use cached word lists
                    verbs, nouns, adjectives = cached_words
                else:
                    # Load word lists and cache them
                    # Use getResourcePath for proper path resolution with better error handling
                    verbs_path = getResourcePath('lib/verbs.txt')
                    nouns_path = getResourcePath('lib/nouns.txt')
                    adjectives_path = getResourcePath('lib/adjectives.txt')
                    
                    # Verify files exist before reading
                    required_files = [
                        (verbs_path, 'verbs.txt'),
                        (nouns_path, 'nouns.txt'), 
                        (adjectives_path, 'adjectives.txt')
                    ]
                    
                    for file_path, file_name in required_files:
                        if not os.path.exists(file_path):
                            raise FileNotFoundError(f"Required file {file_name} not found at {file_path}")
                    
                    # Read files with explicit encoding and better error handling
                    def read_word_file(file_path, file_name):
                        try:
                            # Try UTF-8 first (most common), then fallback to other encodings
                            encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1', 'ascii']
                            
                            words = []
                            successful_encoding = None
                            
                            for encoding in encodings_to_try:
                                try:
                                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                                        raw_words = [line.strip() for line in f if line.strip()]
                                    
                                    if raw_words:  # If we successfully read some words
                                        words = raw_words
                                        successful_encoding = encoding
                                        break
                                except (UnicodeDecodeError, UnicodeError):
                                    continue  # Try next encoding
                                except (FileNotFoundError, PermissionError, OSError) as file_error:
                                    raise Exception(f"File access error for {file_name}: {file_error}")
                                except Exception as read_error:
                                    print(f"Warning: Error reading {file_name} with {encoding}: {read_error}")
                                    continue
                            
                            if not words:
                                raise ValueError(f"No words could be read from {file_name} with any encoding")
                            
                            if successful_encoding and successful_encoding != 'utf-8':
                                print(f"Successfully read {file_name} using {successful_encoding} encoding")
                                
                            # Filter words to ensure they're valid for usernames
                            valid_words = []
                            for word in words:
                                # Clean the word first
                                cleaned_word = word.strip()
                                if (cleaned_word and 
                                    isinstance(cleaned_word, str) and
                                    len(cleaned_word) >= 2 and 
                                    len(cleaned_word) <= 15 and  # Reasonable max length
                                    cleaned_word.replace('_', '').replace('-', '').isalpha() and  # Allow some special chars but check that the rest is alpha
                                    cleaned_word.isascii()):  # Ensure ASCII for compatibility
                                    valid_words.append(cleaned_word.lower())  # Normalize to lowercase
                            
                            if not valid_words:
                                raise ValueError(f"No valid words found in {file_name} after filtering")
                                
                            print(f"Successfully loaded {len(valid_words)} valid words from {file_name}")
                            return valid_words
                            
                        except Exception as read_error:
                            raise Exception(f"Failed to read {file_name}: {read_error}")
                    
                    verbs = read_word_file(verbs_path, 'verbs.txt')
                    nouns = read_word_file(nouns_path, 'nouns.txt')
                    adjectives = read_word_file(adjectives_path, 'adjectives.txt')

                    if not verbs or not nouns or not adjectives:
                        raise ValueError("One or more word lists are empty after reading")

                    # Ensure words are not empty strings and have minimum length
                    valid_verbs = [v for v in verbs if v and len(v) >= 2 and v.replace('_', '').replace('-', '').isalpha()]
                    valid_nouns = [n for n in nouns if n and len(n) >= 2 and n.replace('_', '').replace('-', '').isalpha()]
                    valid_adjectives = [a for a in adjectives if a and len(a) >= 2 and a.replace('_', '').replace('-', '').isalpha()]
                    
                    if not valid_verbs or not valid_nouns or not valid_adjectives:
                        raise ValueError("No valid words found in word lists after filtering")
                    
                    # Cache the word lists with thread safety
                    word_lists_to_cache = (valid_verbs, valid_nouns, valid_adjectives)
                    if self._cache_lock:
                        with self._cache_lock:
                            set_cached_words(word_lists_to_cache)
                    else:
                        set_cached_words(word_lists_to_cache)
                    
                    verbs, nouns, adjectives = valid_verbs, valid_nouns, valid_adjectives
                verb = random.choice(verbs)
                noun = random.choice(nouns) 
                adjective = random.choice(adjectives)
                number = random.randint(10, 99)
                
                # Create username with length checking
                base_username = f"{verb}{noun}{adjective}"
                
                # Ensure the combination doesn't exceed limits before adding number
                max_base_length = self.ROBLOX_USERNAME_LIMIT - 2  # Reserve 2 chars for number
                if len(base_username) > max_base_length:
                    # Truncate proportionally with safety checks
                    total_length = len(verb) + len(noun) + len(adjective)
                    if total_length > 0 and max_base_length > 0:  # Prevent division by zero
                        verb_ratio = len(verb) / total_length
                        noun_ratio = len(noun) / total_length
                        adjective_ratio = len(adjective) / total_length
                        
                        verb_len = max(1, int(max_base_length * verb_ratio))
                        noun_len = max(1, int(max_base_length * noun_ratio))
                        adjective_len = max(1, max_base_length - verb_len - noun_len)
                        
                        # Ensure no negative lengths and total doesn't exceed limit
                        if adjective_len < 1:
                            adjective_len = 1
                            available = max_base_length - adjective_len
                            if available > 0:
                                verb_len = max(1, min(verb_len, available // 2))
                                noun_len = max(1, available - verb_len)
                            else:
                                verb_len = 1
                                noun_len = 1
                        
                        # Additional bounds checking to prevent index errors
                        verb_len = min(verb_len, len(verb))
                        noun_len = min(noun_len, len(noun))
                        adjective_len = min(adjective_len, len(adjective))
                        
                        verb = verb[:verb_len]
                        noun = noun[:noun_len]
                        adjective = adjective[:adjective_len]
                    else:
                        # Fallback if calculations fail or inputs are invalid
                        if max_base_length > 9:  # Ensure we have enough space for meaningful truncation
                            verb_len = min(3, len(verb), max_base_length // 3)
                            noun_len = min(3, len(noun), max_base_length // 3)
                            adjective_len = min(3, len(adjective), max_base_length - verb_len - noun_len)
                            if adjective_len < 1:
                                adjective_len = 1
                        else:
                            # Very small max_base_length, use minimal values
                            # Prevent division by zero in the 'or' expression
                            fallback_len = max(1, max_base_length // 3) if max_base_length >= 3 else 1
                            verb_len = min(1, len(verb), fallback_len)
                            noun_len = min(1, len(noun), fallback_len) 
                            adjective_len = max(1, max_base_length - verb_len - noun_len)
                        
                        verb = verb[:verb_len]
                        noun = noun[:noun_len]
                        adjective = adjective[:adjective_len]
                
                username = f"{verb}{noun}{adjective}{number}"
                
                # Ensure minimum length and that result is still valid
                if len(username) < 3:
                    username = username + "123"
                    username = username[:20]  # Ensure it doesn't exceed after adding
                    
                # Final validation - ensure username contains only valid characters
                try:
                    if USERNAME_PATTERN and USERNAME_PATTERN.match(username):
                        # Additional validation for edge cases
                        if username and len(username.strip()) >= 3 and len(username) <= 20:
                            return username  # Username is valid
                        else:
                            print(f"Warning: Generated username '{username}' has invalid length")
                            username = f"user{random.randint(100, 999)}"
                            return username
                    elif not USERNAME_PATTERN:
                        # Fallback validation if pattern compilation failed
                        if re.match(r'^[a-zA-Z0-9_]+$', username) and len(username.strip()) >= 3 and len(username) <= 20:
                            return username
                        else:
                            username = f"user{random.randint(100, 999)}"
                            return username
                    else:
                        # Username doesn't match pattern
                        username = f"user{random.randint(100, 999)}"
                        return username
                except (re.error, AttributeError) as pattern_error:
                    print(f"Warning: Pattern matching error: {pattern_error}")
                    # Fallback to simple safe username
                    username = f"user{random.randint(100, 999)}"
                    return username
                
                # Additional safety check - ensure the username is not empty or whitespace
                if not username or len(username.strip()) == 0:
                    username = f"fallback{random.randint(100, 999)}"
                
                return username
                
            except Exception as e:
                print(f"Error creating structured username: {e}")
                # Fall back to scrambled generation
                print("Falling back to scrambled username generation...")
                # Ensure fallback doesn't fail
                try:
                    gen = UsernameGenerator(3, 15)  # Safe range for Roblox
                    username = gen.generate()
                    if not username or len(username) < 3:
                        username = f"backup{random.randint(100, 999)}"
                    return username
                except Exception as fallback_error:
                    print(f"Error in fallback username generation: {fallback_error}")
                    # Emergency fallback
                    return f"emergency{random.randint(100, 999)}"
        else:
            # Scrambled username generation
            try:
                gen = UsernameGenerator(3, 15)  # Safe range for Roblox
                username = gen.generate()
                if not username or len(username) < 3:
                    username = f"scrambled{random.randint(100, 999)}"
                return username
            except Exception as scrambled_error:
                print(f"Error in scrambled username generation: {scrambled_error}")
                # Emergency fallback
                return f"generic{random.randint(100, 999)}"

    async def usernameCreator(self, nameFormat=None, scrambled=False):
        counter = 0
        maxAttempts = self.MAX_USERNAME_ATTEMPTS  # Use constant
        api_failures = 0
        max_api_failures = self.MAX_API_FAILURES  # Use constant

        for attempt in range(maxAttempts):
            try:
                if nameFormat:
                    username = f"{nameFormat}_{counter}"
                    # Ensure username doesn't exceed Roblox's character limit
                    if len(username) > self.ROBLOX_USERNAME_LIMIT:  # Use constant
                        # Calculate maximum allowed nameFormat length
                        counter_str = str(counter)
                        max_format_length = self.ROBLOX_USERNAME_LIMIT - len(counter_str) - 1  # Reserve space for counter and underscore
                        if max_format_length > 0:
                            truncated_format = nameFormat[:max_format_length]
                            username = f"{truncated_format}_{counter}"
                        else:
                            # If even truncated version is too long, use fallback
                            username = f"u{counter}"
                            if len(username) > self.ROBLOX_USERNAME_LIMIT:  # Final safety check
                                username = username[:self.ROBLOX_USERNAME_LIMIT]
                else:
                    if scrambled is True:
                        username = self.generateUsername(scrambled=True)
                    else:
                        username = self.generateUsername(scrambled=False)

                try:
                    r = requests.get(
                        f"https://auth.roblox.com/v2/usernames/validate?request.username={username}&request.birthday=04%2F15%2F02&request.context=Signup",
                        timeout=10,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )
                    if r.status_code != 200:
                        print(f"API returned status code {r.status_code} for username {username}")
                        api_failures += 1
                        if api_failures >= max_api_failures:
                            print("Too many API failures, using fallback username generation")
                            return self.generateUsername(scrambled=True)
                        continue
                    
                    r_json = r.json()
                    api_failures = 0  # Reset API failure counter on success
                except requests.exceptions.Timeout:
                    print(f"Timeout validating username {username}")
                    api_failures += 1
                    if api_failures >= max_api_failures:
                        print("Too many API timeouts, using fallback username generation")
                        return self.generateUsername(scrambled=True)
                    # Exponential backoff
                    backoff_time = min(2 ** api_failures, 30)  # Cap at 30 seconds
                    await asyncio.sleep(backoff_time)
                    continue
                except (requests.exceptions.RequestException, ValueError, KeyError, AttributeError) as e:
                    print(f"Error validating username {username}: {e}")
                    api_failures += 1
                    if api_failures >= max_api_failures:
                        print("Too many API failures, using fallback username generation")
                        return self.generateUsername(scrambled=True)
                    # Exponential backoff
                    backoff_time = min(2 ** api_failures, 30)  # Cap at 30 seconds
                    await asyncio.sleep(backoff_time)
                    continue

                if r_json.get("code") == 0:
                    return username
                else:
                    # Handle different response codes appropriately
                    error_message = r_json.get("message", "Unknown error")
                    print(f"Username '{username}' validation failed: {error_message}")
                    
                    # Only increment counter for nameFormat when username is invalid
                    if nameFormat:
                        counter += 1
                        # Check if counter gets too large to prevent infinite loops
                        if counter > 99999:  # Reasonable upper limit
                            print("Warning: Too many attempts with nameFormat, switching to scrambled generation")
                            return self.generateUsername(scrambled=True)
                        # Also check if we've made too many total attempts with this nameFormat
                        if attempt > self.MAX_USERNAME_ATTEMPTS // 2:  # Switch to scrambled after half attempts
                            print(f"Warning: Switching to scrambled generation after {attempt} attempts with nameFormat")
                            return self.generateUsername(scrambled=True)
                    # For scrambled usernames, we don't increment counter, just try again
                    
                    # Add small delay to prevent overwhelming the API
                    await asyncio.sleep(0.1)
                    continue
            except Exception as e:
                print(f"Error validating username: {e}")
                continue

        # If we reach here and used nameFormat, try with scrambled as fallback
        if nameFormat:
            print(f"Warning: Could not generate valid username with format '{nameFormat}' after {maxAttempts} attempts. Using scrambled username as fallback.")
            try:
                fallback_username = self.generateUsername(scrambled=True)
                if fallback_username and len(fallback_username) >= 3:
                    return fallback_username
            except Exception as fallback_error:
                print(f"Warning: Scrambled fallback also failed: {fallback_error}")
        
        # Final fallback with maximum safety
        try:
            print(f"Warning: Could not generate valid username after {maxAttempts} attempts. Using emergency fallback.")
            # Simple emergency fallback with multiple attempts
            for emergency_attempt in range(10):
                timestamp = int(time.time() % 10000)
                random_suffix = random.randint(100, 999)
                fallback_username = f"user{timestamp}{random_suffix}"
                
                # Ensure it doesn't exceed character limit
                if len(fallback_username) > self.ROBLOX_USERNAME_LIMIT:
                    fallback_username = fallback_username[:self.ROBLOX_USERNAME_LIMIT]
                
                # Ensure minimum length and valid format
                if (fallback_username and 
                    len(fallback_username) >= 3 and 
                    len(fallback_username) <= self.ROBLOX_USERNAME_LIMIT and
                    fallback_username.replace('_', '').isalnum()):
                    return fallback_username
            
            # Ultimate emergency fallback - ensure it meets requirements
            return "user123"[:self.ROBLOX_USERNAME_LIMIT]
        except Exception as ultimate_error:
            print(f"Warning: Emergency fallback failed: {ultimate_error}")
            # Absolute last resort - ensure it meets requirements
            return "user123"[:self.ROBLOX_USERNAME_LIMIT]

    async def checkUpdate(self):
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                resp = requests.get(
                    "https://api.github.com/repos/qing762/roblox-auto-signup/releases/latest",
                    timeout=10,
                    headers={'User-Agent': 'roblox-auto-signup'}  # Add user agent to avoid rate limiting
                )
                resp.raise_for_status()
                response_data = resp.json()
                latestVer = response_data.get("tag_name", "unknown")
                break  # Success, exit retry loop
            except (requests.RequestException, ValueError) as e:
                if attempt < max_retries - 1:
                    print(f"API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    print(f"Failed to check for updates after {max_retries} attempts: {e}")
                    return "unknown"  # Return unknown version if all attempts fail

        # Get current version (after the retry loop)
        try:
            if getattr(sys, 'frozen', False):
                # Try to get version from version module first
                try:
                    import version as version_module  # type: ignore
                    currentVer = version_module.__version__
                except (ImportError, AttributeError):
                    # Fallback to version.txt even in frozen mode
                    try:
                        version_path = getResourcePath("version.txt")
                        with open(version_path, "r", encoding="utf-8") as file:
                            currentVer = file.read().strip()
                    except (FileNotFoundError, IOError, UnicodeDecodeError):
                        currentVer = "unknown"
            else:
                # Normal execution - try version.txt first
                try:
                    with open("version.txt", "r", encoding="utf-8") as file:
                        currentVer = file.read().strip()
                except (FileNotFoundError, IOError, UnicodeDecodeError):
                    # Fallback to version module
                    try:
                        import version as version_module  # type: ignore
                        currentVer = version_module.__version__
                    except (ImportError, AttributeError):
                        currentVer = "unknown"
        except Exception as version_error:
            print(f"Warning: Error determining current version: {version_error}")
            currentVer = "unknown"

        if currentVer != "unknown" and latestVer != "unknown":
            # Proper version comparison - remove 'v' prefix if present and compare
            current_clean = currentVer.lstrip('v').strip()
            latest_clean = latestVer.lstrip('v').strip()
            
            # Validate version format before comparison
            if not current_clean or not latest_clean:
                print(f"Version check: Current={currentVer}, Latest={latestVer}")
                print("Please check: https://github.com/qing762/roblox-auto-signup/releases/latest")
                return currentVer
            
            try:
                from packaging import version as pkg_version
                if pkg_version.parse(current_clean) < pkg_version.parse(latest_clean):
                    print(f"Update available: {latestVer} (Current version: {currentVer})")
                    print("Download from: https://github.com/qing762/roblox-auto-signup/releases/latest")
                    return currentVer
                else:
                    print(f"You are running the latest version: {currentVer}")
                    return currentVer
            except ImportError:
                # Improved fallback version comparison with proper semantic version handling
                try:
                    def parse_version_simple(version_str):
                        """Simple version parser that handles semantic versioning"""
                        parts = version_str.split('.')
                        # Convert each part to integer, padding with zeros if needed
                        normalized_parts = []
                        for part in parts[:3]:  # Only consider major.minor.patch
                            # Extract numeric part and ignore alpha/beta suffixes
                            numeric_part = ''.join(filter(str.isdigit, part))
                            normalized_parts.append(int(numeric_part) if numeric_part else 0)
                        
                        # Ensure we have at least 3 parts (major.minor.patch)
                        while len(normalized_parts) < 3:
                            normalized_parts.append(0)
                            
                        return tuple(normalized_parts)
                    
                    current_version_tuple = parse_version_simple(current_clean)
                    latest_version_tuple = parse_version_simple(latest_clean)
                    
                    if current_version_tuple < latest_version_tuple:
                        print(f"Update available: {latestVer} (Current version: {currentVer})")
                        print("Download from: https://github.com/qing762/roblox-auto-signup/releases/latest")
                    elif current_version_tuple > latest_version_tuple:
                        print(f"You are running a development version: {currentVer} (Latest stable: {latestVer})")
                    else:
                        print(f"You are running the latest version: {currentVer}")
                    return currentVer
                except (ValueError, IndexError, TypeError) as parse_error:
                    print(f"Warning: Could not parse versions for comparison: {parse_error}")
                    print(f"Version check: Current={currentVer}, Latest={latestVer}")
                    print("Please check: https://github.com/qing762/roblox-auto-signup/releases/latest")
                    return currentVer
            except Exception as version_parse_error:
                print(f"Warning: Error parsing versions: {version_parse_error}")
                print(f"Version check: Current={currentVer}, Latest={latestVer}")
                return currentVer
        else:
            print(f"You are running version: {currentVer}")
            return currentVer

    async def checkPassword(self, username, password):
        try:
            try:
                token_response = requests.post("https://auth.roblox.com/v2/login", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                token = token_response.headers.get("x-csrf-token")
                if not token:
                    return "\nPassword validation failed: Could not obtain CSRF token"
            except requests.exceptions.RequestException as e:
                return f"\nPassword validation failed: Could not connect to Roblox API: {e}"
                
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
            try:
                response = requests.post("https://auth.roblox.com/v2/passwords/validate", json=data, headers=headers, timeout=10)
                
                # Check if response is valid before parsing JSON
                if response.status_code != 200:
                    return f"\nPassword validation failed: Server returned status {response.status_code}"
                
                try:
                    resp = response.json()
                except ValueError as json_error:
                    return f"\nPassword validation failed: Invalid JSON response: {json_error}"
                
                if resp.get("code") == 0:
                    return "\nPassword is valid"
                else:
                    return f"\nPassword does not meet the requirements: {resp.get('message', 'Unknown error')}"
            except (requests.exceptions.RequestException, KeyError) as e:
                return f"\nPassword validation failed: Network or response error: {e}"
        except Exception as e:
            return f"\nPassword validation error: Unexpected error: {e}"

    async def customization(self, tab):
        try:
            # Start listening for avatar inventory response
            tab.listen.start('https://avatar.roblox.com/v1/avatar-inventory?pageLimit=50&sortOption=recentAdded')
            try:
                tab.get("https://www.roblox.com/my/avatar")
                result = tab.listen.wait(timeout=10)
                if result and result.response and result.response.body:
                    content = result.response.body
                    assetDict = {}
                    
                    # Safely extract avatar inventory items
                    avatar_items = content.get('avatarInventoryItems', []) if isinstance(content, dict) else []
                    for item in avatar_items:
                        if (isinstance(item, dict) and 
                            'itemCategory' in item and 
                            isinstance(item['itemCategory'], dict) and
                            'itemSubType' in item['itemCategory']):
                            assetType = item["itemCategory"]["itemSubType"]
                            if assetType not in assetDict:
                                assetDict[assetType] = []
                            assetDict[assetType].append(item)
                else:
                    print("Warning: No avatar inventory data received")
                    return
            except Exception as e:
                print(f"Warning: Could not load avatar inventory: {e}")
                return
            finally:
                try:
                    tab.listen.stop()
                except Exception:
                    pass  # Ignore errors when stopping listener

            selectedAssets = {}
            for assetType, assets in assetDict.items():
                if assets:  # Only select if assets list is not empty
                    selectedAssets[assetType] = random.choice(assets)

            if not selectedAssets:
                print("Warning: No avatar assets found to customize")
                return

            for assetType, asset in selectedAssets.items():
                try:
                    avatar_items = tab.eles(".hlist item-cards-stackable .item-card-link")
                    if not avatar_items:
                        # Try alternative selector
                        avatar_items = tab.eles("tag:li tag:a[data-item-name]")
                    
                    for item_link in avatar_items:
                        if item_link.attr("data-item-name") == asset.get("itemName"):
                            item_link.click()
                            break
                except Exception as e:
                    print(f"Warning: Could not click asset {asset.get('itemName', 'unknown')}: {e}")
        except Exception as e:
            print(f"Warning: Avatar customization failed: {e}")
            return  # Exit gracefully if customization fails

        bodyType = random.choice([i for i in range(0, 101, 5)])
        
        # Validate bodyType to prevent JavaScript injection
        if not isinstance(bodyType, int) or bodyType < 0 or bodyType > 100:
            bodyType = 50  # Safe default value
        
        try:
            # Use parameterized JavaScript execution for security
            tab.run_js_loaded(f'document.getElementById("body type-scale").value = {int(bodyType)};')
            tab.run_js_loaded('document.getElementById("body type-scale").dispatchEvent(new Event("input"));')
        except errors.JavaScriptError:
            # Sanitize the bodyType value for JavaScript injection prevention
            safe_body_type = int(bodyType)  # Ensure it's an integer
            if not (0 <= safe_body_type <= 100):
                safe_body_type = 50  # Use safe default
                
            # Use template with safe integer substitution
            js_code = f'''
                var slider = document.querySelector('input[aria-label="Body Type Scale"]');
                if (slider) {{
                    var muiSlider = slider.closest('.MuiSlider-root');
                    var rect = muiSlider.getBoundingClientRect();
                    var targetValue = {safe_body_type};
                    var percentage = targetValue / 100;
                    var targetX = rect.left + (rect.width * percentage);
                    var targetY = rect.top + (rect.height / 2);

                    muiSlider.dispatchEvent(new MouseEvent('mousedown', {{
                        bubbles: true,
                        clientX: targetX,
                        clientY: targetY,
                        button: 0
                    }}));

                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeInputValueSetter.call(slider, targetValue);

                    slider.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    slider.dispatchEvent(new Event('change', {{ bubbles: true }}));

                    muiSlider.dispatchEvent(new MouseEvent('mouseup', {{
                        bubbles: true,
                        clientX: targetX,
                        clientY: targetY,
                        button: 0
                    }}));
                }}
            '''
            tab.run_js_loaded(js_code)
            await asyncio.sleep(2)

    def testProxy(self, proxy):
        if not proxy or not proxy.strip():
            return False, "Empty proxy provided"

        try:
            proxy = proxy.strip()

            # Enhanced validation against malicious proxy formats
            if DANGEROUS_PROXY_PATTERNS:  # Check if patterns exist and are not empty
                for pattern in DANGEROUS_PROXY_PATTERNS:
                    try:
                        if pattern and hasattr(pattern, 'search') and pattern.search(proxy):
                            return False, f"Proxy contains potentially dangerous pattern"
                    except (AttributeError, TypeError):
                        # Skip invalid pattern objects
                        continue
                    except Exception as pattern_error:
                        print(f"Warning: Error checking proxy pattern: {pattern_error}")
                        continue
            else:
                # Use basic fallback validation if no patterns available
                try:
                    # Use the stored basic security check function
                    basic_check_func = globals().get('_basic_security_check')
                    if basic_check_func and callable(basic_check_func):
                        if basic_check_func(proxy):
                            return False, f"Proxy contains potentially dangerous characters"
                    else:
                        # Ultimate fallback - simple character check
                        dangerous_chars = ['&', ';', '|', '`', '$']
                        if any(char in proxy for char in dangerous_chars):
                            return False, f"Proxy contains potentially dangerous characters"
                except Exception as basic_check_error:
                    print(f"Warning: Error in basic security check: {basic_check_error}")
                    # Ultimate fallback - simple character check
                    dangerous_chars = ['&', ';', '|', '`', '$']
                    if any(char in proxy for char in dangerous_chars):
                        return False, f"Proxy contains potentially dangerous characters"
                
                # Final fallback validation
                dangerous_chars = [';', '&', '|', '`', '$', '<', '>', '"', "'"]
                if any(char in proxy for char in dangerous_chars):
                    return False, f"Proxy contains potentially dangerous characters"

            # Validate proxy format
            if len(proxy) > 200:  # Reasonable length limit
                return False, f"Proxy URL too long"

            # Validate proxy format more strictly
            if not proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
                # Auto-add http:// for IP:PORT format with validation
                try:
                    # Function to validate IP:PORT format
                    def validate_ip_port(proxy_str):
                        if ':' not in proxy_str:
                            return False, f"Invalid format: missing port"
                        
                        parts = proxy_str.split(':')
                        if len(parts) != 2:
                            return False, f"Invalid format: expected IP:PORT"
                            
                        ip_part, port_part = parts
                        ip_parts = ip_part.split('.')
                        
                        # Validate IP has exactly 4 parts
                        if len(ip_parts) != 4:
                            return False, f"Invalid IP address format"
                        
                        try:
                            port = int(port_part)
                        except ValueError:
                            return False, f"Invalid port number format"
                        
                        # Basic IP validation
                        for part in ip_parts:
                            try:
                                part_int = int(part)
                                if not (0 <= part_int <= 255):
                                    return False, f"Invalid IP address"
                            except ValueError:
                                return False, f"Invalid IP address format"
                        
                        # Basic port validation
                        if not (1 <= port <= 65535):
                            return False, f"Invalid port number"
                        
                        return True, "Valid"
                    
                    # Check if IP_PORT_PATTERN was compiled successfully
                    pattern_match = False
                    if IP_PORT_PATTERN is not None:
                        pattern_match = IP_PORT_PATTERN.match(proxy)
                    else:
                        # Fallback validation if pattern compilation failed
                        pattern_match = re.match(r'^(\d{1,3}\.){3}\d{1,3}:\d{1,5}$', proxy)
                    
                    if pattern_match:
                        is_valid, error_msg = validate_ip_port(proxy)
                        if not is_valid:
                            return False, error_msg
                        proxy = "http://" + proxy
                    else:
                        return False, f"Invalid proxy format"
                except (ValueError, IndexError) as e:
                    return False, f"Invalid proxy format: {e}"
            # If we reach here, proxy has valid protocol prefix, continue to testing

            # Test proxy with simple URL
            test_urls = ["https://httpbin.org/ip", "http://httpbin.org/ip"]
            
            for test_url in test_urls:
                try:
                    response = requests.get(
                        test_url, 
                        proxies={"http": proxy, "https": proxy}, 
                        timeout=15,
                        headers={'User-Agent': 'Mozilla/5.0'},
                        allow_redirects=False
                    )
                    if 200 <= response.status_code < 300:
                        return True, f"Proxy {proxy} is working"
                except Exception:
                    continue  # Try next URL
            
            return False, f"Proxy {proxy} failed all tests"
        except requests.exceptions.Timeout:
            return False, f"Proxy {proxy} timed out"
        except requests.exceptions.ConnectionError:
            return False, f"Proxy {proxy} connection failed"
        except Exception as e:
            return False, f"Proxy {proxy} test failed: {str(e)}"

    async def generateEmail(self, password="Qing762.chy"):
        # Check if pymailtm is available
        if not PYMAILTM_AVAILABLE:
            raise Exception("Email generation not available: pymailtm module not installed. Please install it with: pip install pymailtm")
        
        # Validate password strength if it's the default
        if password == "Qing762.chy":
            print("Warning: Using default password for email generation. Consider using a stronger password.")
        
        # Add input validation for password
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long")
        if len(password) > 72:  # Reasonable upper limit for bcrypt compatibility
            raise ValueError("Password is too long (max 72 characters)")
        
        # Initialize MailTM fresh for each email generation to prevent state issues
        mailtm = None
        email_generation_lock = None
        try:
            # Prevent race conditions in email generation with a lock
            if not hasattr(self, '_email_generation_lock'):
                if THREADING_AVAILABLE:
                    self._email_generation_lock = threading.RLock()  # Use RLock for reentrant locking
                    email_generation_lock = self._email_generation_lock
                else:
                    print("Warning: Threading module not available, proceeding without lock")
                    email_generation_lock = None
            else:
                email_generation_lock = self._email_generation_lock
                
            # Initialize MailTM with proper locking
            def initialize_mailtm():
                mailtm_instance = MailTm()
                # Verify the instance is properly initialized
                if not hasattr(mailtm_instance, 'get_domains'):
                    raise Exception("MailTm instance not properly initialized")
                return mailtm_instance
                
            if email_generation_lock and THREADING_AVAILABLE:
                with email_generation_lock:
                    mailtm = initialize_mailtm()
            else:
                mailtm = initialize_mailtm()
                
        except Exception as e:
            print(f"Error initializing MailTm: {e}")
            raise Exception(f"Failed to initialize email service: {e}")

        maxRetries = self.MAX_EMAIL_RETRIES
        last_error = None
        consecutive_failures = 0  # Track consecutive failures for circuit breaker
        max_consecutive_failures = 3
        
        for attempt in range(maxRetries):
            try:
                # Circuit breaker: if too many consecutive failures, increase delay
                if consecutive_failures >= max_consecutive_failures:
                    circuit_breaker_delay = min(60 * (consecutive_failures - max_consecutive_failures + 1), 300)
                    print(f"Circuit breaker activated. Waiting {circuit_breaker_delay} seconds...")
                    await asyncio.sleep(circuit_breaker_delay)
                
                # Reinitialize MailTM on each retry to avoid state issues
                if attempt > 0:
                    try:
                        if email_generation_lock and THREADING_AVAILABLE:
                            with email_generation_lock:
                                mailtm = MailTm()
                        else:
                            mailtm = MailTm()
                        # Verify initialization
                        if not hasattr(mailtm, 'get_domains'):
                            raise Exception("MailTm instance not properly initialized after retry")
                        # Progressive delay with jitter to avoid thundering herd
                        base_delay = min(3 * (2 ** (attempt - 1)), 30)  # Cap at 30 seconds
                        jitter = random.uniform(0.5, 1.5)
                        delay = base_delay * jitter
                        await asyncio.sleep(delay)
                    except Exception as reinit_error:
                        print(f"Error reinitializing MailTm on attempt {attempt + 1}: {reinit_error}")
                        if attempt == maxRetries - 1:
                            raise Exception(f"Failed to reinitialize email service: {reinit_error}")
                        continue
                
                # Get domain list with retry
                try:
                    domainList = mailtm.get_domains()
                    if not domainList or len(domainList) == 0:
                        raise Exception("No domains returned from mail service")
                    # Extract domain names from domain objects if needed
                    valid_domains = []
                    for domain in domainList:
                        if hasattr(domain, 'domain'):  # Domain object
                            domain_name = domain.domain
                        elif isinstance(domain, str):  # Direct string
                            domain_name = domain
                        elif isinstance(domain, dict) and 'domain' in domain:  # Dict format
                            domain_name = domain['domain']
                        else:
                            continue
                            
                        if domain_name and isinstance(domain_name, str) and len(domain_name) > 0 and '.' in domain_name:
                            valid_domains.append(domain_name)
                    if not valid_domains:
                        raise Exception("No valid domains found")
                    domainList = valid_domains
                except Exception as domain_error:
                    print(f"Error getting domain list (attempt {attempt + 1}/{maxRetries}): {domain_error}")
                    last_error = domain_error
                    if attempt < maxRetries - 1:
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    else:
                        raise Exception(f"No domains available after {maxRetries} attempts: {domain_error}")

                domain = random.choice(domainList)
                
                # Generate username with better error handling
                try:
                    username = self.generateUsername().lower()
                    # Additional validation for email username
                    if not username or len(username) < 3:
                        username = f"user{random.randint(100, 999)}"
                    # Ensure email-safe username - remove all non-alphanumeric chars except underscore
                    username = re.sub(r'[^a-z0-9_]', '', username)[:15]  # Remove special chars, limit length
                    if len(username) < 3:
                        username = f"user{random.randint(100, 999)}"
                    # Ensure no empty username
                    if not username:
                        username = f"user{random.randint(100, 999)}"
                    # Final validation - ensure it doesn't start with underscore or number
                    if len(username) > 0 and (username[0].isdigit() or username[0] == '_'):
                        username = f"u{username}"[:15]
                    # Final safety check - ensure username is not empty after all processing
                    if not username or len(username) == 0:
                        username = f"user{random.randint(100, 999)}"
                    # Additional final validation - ensure minimum length still met after slicing
                    if len(username) < 3:
                        username = f"user{random.randint(100, 999)}"
                except Exception as username_error:
                    print(f"Error generating username: {username_error}")
                    username = f"user{random.randint(1000, 9999)}"
                
                address = f"{username}@{domain}"
                
                # Validate email address format
                if len(address) > 254:  # RFC 5321 limit
                    raise ValueError("Generated email address is too long")
                
                # Basic email format validation
                if '@' not in address or address.count('@') != 1:
                    raise ValueError("Invalid email address format")
                
                local_part, domain_part = address.split('@')
                if not local_part or not domain_part or len(local_part) > 64:
                    raise ValueError("Invalid email address components")

                # Create email account
                try:
                    emailID_response = requests.post(
                        "https://api.mail.tm/accounts", 
                        json={"address": address, "password": password}, 
                        timeout=15,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if emailID_response.status_code == 201:
                        emailID_data = emailID_response.json()
                        email_id = emailID_data.get("id")
                        if not email_id:
                            raise Exception("Email ID not found in response")
                            
                        token_response = requests.post(
                            "https://api.mail.tm/token",
                            json={"address": address, "password": password},
                            timeout=15,
                            headers={'Content-Type': 'application/json'}
                        )
                        
                        if token_response.status_code == 200:
                            token_data = token_response.json()
                            token = token_data.get("token")
                            if not token:
                                raise Exception("Token not found in response")
                            return address, password, token, emailID_data
                        else:
                            raise Exception(f"Token request failed with status {token_response.status_code}: {token_response.text}")
                    elif emailID_response.status_code == 422:
                        # Email already exists, try different address
                        if attempt < maxRetries - 1:
                            print(f"Email {address} already exists, trying different address...")
                            # Add small delay to avoid rapid retries
                            await asyncio.sleep(1)
                            continue
                        else:
                            raise Exception(f"Failed to create unique email after {maxRetries} attempts")
                    elif emailID_response.status_code == 429:
                        # Rate limited, wait longer
                        wait_time = min(30 * (attempt + 1), 120)  # Progressive wait, cap at 2 minutes
                        print(f"Rate limited by email service. Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Email creation failed with status {emailID_response.status_code}: {emailID_response.text}")
                            
                except requests.RequestException as req_error:
                    last_error = req_error
                    if attempt < maxRetries - 1:
                        print(f"Network error creating email (attempt {attempt + 1}/{maxRetries}): {req_error}")
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    else:
                        raise Exception(f"Network error after {maxRetries} attempts: {req_error}")
                        
            except Exception as e:
                last_error = e
                consecutive_failures += 1  # Increment consecutive failure counter
                if attempt < maxRetries - 1:
                    print(f"Error creating email (attempt {attempt + 1}/{maxRetries}): {e}")
                    # Exponential backoff with jitter for consecutive failures
                    base_delay = 5 * (attempt + 1)
                    if consecutive_failures >= max_consecutive_failures:
                        base_delay *= 2  # Double delay for repeated failures
                    jitter = random.uniform(0.5, 1.5)
                    delay = min(base_delay * jitter, 120)  # Cap at 2 minutes
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception(f"Failed to create email after {maxRetries} attempts: {e}")
            
            # Reset consecutive failures on success (this should only be reached on successful creation)
            consecutive_failures = 0
            break  # Exit the retry loop on success
            
        # If we reach here, all attempts failed
        raise Exception(f"Failed to create email after {maxRetries} attempts. Last error: {last_error}")

    def fetchVerification(self, address=None, password=None, emailID=None):
        # Check if pymailtm is available
        if not PYMAILTM_AVAILABLE:
            raise Exception("Email verification not available: pymailtm module not installed")
        
        if not address or not password or not emailID:
            raise ValueError("Address, password, and emailID must be provided.")
        
        try:
            # Extract the ID if emailID is a dictionary
            if isinstance(emailID, dict):
                actual_id = emailID.get("id")
                if not actual_id:
                    raise ValueError("No 'id' field found in emailID dictionary")
            else:
                actual_id = emailID
                
            # Validate actual_id format
            if not actual_id or not isinstance(actual_id, str):
                raise ValueError("Invalid email ID format")
                
            # Create a fresh MailTm instance for verification to avoid state issues
            mailtm = MailTm()
            # Create a new account instance for this specific email
            account = Account(actual_id, address, password)
            
            # Get messages with error handling for malformed responses
            try:
                messages = account.get_messages()
                # Validate messages format
                if messages is None:
                    return []
                elif isinstance(messages, list):
                    # Filter out any malformed message objects
                    valid_messages = []
                    for msg in messages:
                        if hasattr(msg, 'text') or hasattr(msg, 'html'):
                            valid_messages.append(msg)
                    return valid_messages
                else:
                    print(f"Warning: Unexpected message format: {type(messages)}")
                    return []
            except Exception as msg_error:
                print(f"Error retrieving messages: {msg_error}")
                return []
        except Exception as e:
            print(f"Error fetching verification email: {e}")
            return []

    def promptAnalytics(self):
        if not os.path.exists("analytics.txt"):
            while True:
                analytics = input("\nNo personal data is collected, but anonymous usage statistics help us improve. Allow data collection? [y/n] (Default: Yes): ").strip().lower()
                if analytics in ("y", "yes", ""):
                    userId = str(uuid.uuid4())
                    try:
                        with open("analytics.txt", "w", encoding="utf-8") as file:
                            file.write("DO NOT CHANGE ANYTHING IN THIS FILE\n")
                            file.write("analytics=1\n")
                            file.write(f"userID={userId}\n")
                        print("Analytics collection enabled.")
                        return True
                    except Exception as e:
                        print(f"Error writing analytics configuration: {e}")
                        return False
                elif analytics in ("n", "no"):
                    try:
                        with open("analytics.txt", "w", encoding="utf-8") as file:
                            file.write("DO NOT CHANGE ANYTHING IN THIS FILE\n")
                            file.write("analytics=0\n")
                        print("Analytics collection disabled.")
                        return False
                    except Exception as e:
                        print(f"Error writing analytics configuration: {e}")
                        return False
                else:
                    print("Please enter a valid option (y/n).")
        else:
            # Analytics configuration already exists
            return True

    def checkAnalytics(self, version):
        try:
            if not os.path.exists("analytics.txt"):
                return False
                
            with open("analytics.txt", "r", encoding="utf-8") as file:
                content = file.read().strip()
                
            if not content:
                print("Warning: Analytics file is empty")
                return False
            
            # Parse analytics settings more robustly
            analytics = None
            userId = None
            
            # Split by lines and process each line
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#') or line == "DO NOT CHANGE ANYTHING IN THIS FILE":
                    continue  # Skip empty lines, comments, and header
                    
                if '=' in line:
                    try:
                        key, value = line.split("=", 1)  # Only split on first =
                        key = key.strip()
                        value = value.strip()
                        
                        if key == "analytics":
                            if value in ["0", "1"]:
                                analytics = value
                            else:
                                print(f"Warning: Invalid analytics value '{value}', expected 0 or 1")
                        elif key == "userID":
                            if value and len(value) > 0:
                                userId = value
                            else:
                                print("Warning: Empty userID in analytics file")
                    except ValueError as parse_error:
                        print(f"Warning: Could not parse line '{line}': {parse_error}")
                        continue
                else:
                    print(f"Warning: Invalid line format in analytics file: '{line}'")
                        
            # Validate parsed data
            if analytics == "1":
                if userId:
                    self.sendAnalytics(version, userId)
                    return True
                else:
                    print("Warning: Analytics enabled but no valid userID found")
                    return False
            elif analytics == "0":
                return False
            else:
                print("Warning: Analytics setting not found or invalid")
                return False
                
        except FileNotFoundError:
            print("Analytics configuration file not found.")
            return False
        except (UnicodeDecodeError, PermissionError, IOError) as e:
            print(f"Error reading analytics configuration: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error reading analytics configuration: {e}")
            return False

    def sendAnalytics(self, version, userId=None):
        # DO NOT CHANGE THIS KEY, IT IS USED FOR SIGNING THE ANALYTICS DATA
        key = b"Qing762.chy"

        # THIS USERID IS NOT RELATED TO THE USER'S ROBLOX ACCOUNT, IT IS JUST A UNIQUE ID FOR ANALYTICS PURPOSES
        if userId is None:
            userIdValue = None
            try:
                with open("analytics.txt", "r", encoding="utf-8") as file:
                    for line in file:
                        line = line.strip()
                        if line.startswith("userID=") and "=" in line:
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                userIdValue = parts[1]
                                break
            except FileNotFoundError:
                userIdValue = str(uuid.uuid4())
            userId = userIdValue or str(uuid.uuid4())

        message = userId.encode('utf-8')
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
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code == 200:
                pass
            else:
                print(f"\nFailed to send analytics data. Status code: {response.status_code}")
        except requests.exceptions.Timeout:
            # Silent timeout - analytics are not critical
            pass
        except requests.RequestException as e:
            print(f"\nAn error occurred while sending analytics data: {e}")

    async def followUser(self, user, tab):
        userIDList = []
        
        # Enhanced rate limiting to prevent anti-bot measures
        follow_delay = 6  # Increased seconds between each follow attempt
        request_delay = 3  # Increased delay between API requests
        
        # Add rate limiting protection with more conservative limits
        max_follows_per_minute = max(1, self.MAX_FOLLOWS_PER_MINUTE // 2)  # Be more conservative
        follow_count = 0
        start_time = time.time()
        
        # Add jitter to avoid predictable timing patterns
        def add_jitter(base_delay):
            return base_delay + random.uniform(0.5, 2.0)
        
        for i, x in enumerate(user):
            # Enhanced empty username validation
            if not x or not isinstance(x, str) or not x.strip():  # Skip empty/invalid usernames
                print(f"Skipping empty or invalid username at position {i}")
                continue
            
            # Clean and validate username
            clean_username = x.strip()
            if not clean_username:  # Check after strip
                print(f"Skipping empty username after cleaning at position {i}")
                continue
            
            # Rate limiting check with proper time management
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Reset counter if more than a minute has passed
            if elapsed_time >= 60:
                follow_count = 0
                start_time = current_time
                elapsed_time = 0
            
            if follow_count >= max_follows_per_minute and elapsed_time < 60:
                sleep_time = 60 - elapsed_time + random.uniform(5, 15)  # Add extra buffer
                print(f"Rate limit reached. Waiting {sleep_time:.1f} seconds...")
                await asyncio.sleep(sleep_time)
                # Reset both counter and start time after waiting
                follow_count = 0
                start_time = time.time()
                
            # Validate username format before API call using pre-compiled regex
            try:
                # Check if pattern was compiled successfully
                if USERNAME_PATTERN is not None:
                    if not USERNAME_PATTERN.match(clean_username):
                        print(f"Invalid username format: {clean_username}")
                        continue
                else:
                    # Fallback validation if pattern compilation failed
                    if not re.match(r'^[a-zA-Z0-9_]+$', clean_username):
                        print(f"Invalid username format: {clean_username}")
                        continue
                
                # Length validation
                if len(clean_username) > 20 or len(clean_username) < 3:
                    print(f"Invalid username length: {clean_username}")
                    continue
                    
            except Exception as pattern_error:
                print(f"Error validating username pattern for {clean_username}: {pattern_error}")
                continue
                
            try:
                # Add jittered delay between requests except for the first user
                if i > 0:
                    await asyncio.sleep(add_jitter(follow_delay))
                
                # Add jittered delay before API request to avoid rate limiting
                if i > 0:
                    await asyncio.sleep(add_jitter(request_delay))
                
                response = requests.post(
                    "https://users.roblox.com/v1/usernames/users", 
                    json={"usernames": [clean_username]}, 
                    timeout=20,  # Increased timeout for stability
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                response.raise_for_status()
                data = response.json()

                if not data.get("data") or len(data["data"]) == 0:
                    print(f"User {clean_username} not found!")
                    continue

                userID = data["data"][0]["id"]
                if not userID or not isinstance(userID, (int, str)):
                    print(f"Invalid user ID received for {clean_username}")
                    continue
                
                # Ensure userID is properly validated and formatted
                try:
                    # Convert to int first to validate it's a number, then back to string
                    userID_int = int(userID)
                    if userID_int <= 0:
                        print(f"Invalid user ID value for {clean_username}: {userID_int}")
                        continue
                    userID_str = str(userID_int)
                except (ValueError, TypeError):
                    print(f"Invalid user ID format for {clean_username}: {userID}")
                    continue
                    
                url = f"https://www.roblox.com/users/{userID_str}/profile"
                
                try:
                    tab.get(url)
                    # Add reasonable timeout to prevent hanging
                    await asyncio.sleep(add_jitter(3))  # Increased sleep time with jitter
                except Exception as e:
                    print(f"Error loading profile page for user {clean_username}: {e}")
                    continue

                try:
                    # Try multiple possible selectors for the follow button
                    follow_button = None
                    selectors_to_try = [
                        "@class=MuiButtonBase-root MuiIconButton-root web-blox-css-tss-abxp79-IconButton-root profile-header-dropdown MuiIconButton-sizeMedium web-blox-css-mui-3cliw1",
                        ".profile-header-dropdown",
                        "[data-testid='profile-menu-button']",
                        ".dropdown-menu-container button",
                        ".profile-header-actions button"
                    ]
                    
                    for selector in selectors_to_try:
                        try:
                            follow_button = tab.ele(selector, timeout=3)
                            if follow_button:
                                break
                        except errors.ElementNotFoundError:
                            continue
                    
                    if follow_button:
                        follow_button.click()
                        await asyncio.sleep(1)  # Wait for dropdown to appear
                        
                        # Try to find and click the actual follow button
                        follow_selectors = [
                            "@@class=MuiButtonBase-root MuiMenuItem-root web-blox-css-tss-1uppt56-MenuItem-root MuiMenuItem-gutters MuiMenuItem-root web-blox-css-tss-1uppt56-MenuItem-root MuiMenuItem-gutters web-blox-css-mui-1bwf1ry-Typography-body1@@id=follow-button",
                            "#follow-button",
                            "[data-testid='follow-button']",
                            "text:Follow",
                            ".follow-button"
                        ]
                        
                        follow_clicked = False
                        for follow_selector in follow_selectors:
                            try:
                                actual_follow_button = tab.ele(follow_selector, timeout=3)
                                if actual_follow_button and actual_follow_button.text and "follow" in actual_follow_button.text.lower():
                                    actual_follow_button.click()
                                    follow_clicked = True
                                    break
                            except errors.ElementNotFoundError:
                                continue
                        
                        if follow_clicked:
                            userIDList.append(userID)
                            follow_count += 1  # Increment follow count for rate limiting
                            print(f"Successfully followed user {clean_username}")
                        else:
                            print(f"Could not find follow button for user {clean_username}")
                    else:
                        # Try direct follow button without dropdown
                        direct_follow_selectors = [
                            "button:contains('Follow')",
                            ".btn-follow",
                            "[data-testid='follow-button']"
                        ]
                        
                        follow_clicked = False
                        for selector in direct_follow_selectors:
                            try:
                                direct_button = tab.ele(selector, timeout=3)
                                if direct_button:
                                    direct_button.click()
                                    follow_clicked = True
                                    userIDList.append(userID)
                                    follow_count += 1  # Increment follow count for rate limiting
                                    print(f"Successfully followed user {clean_username}")
                                    break
                            except errors.ElementNotFoundError:
                                continue
                        
                        if not follow_clicked:
                            print(f"Could not find any follow button for user {clean_username}")
                        
                except errors.ElementNotFoundError:
                    print(f"Could not find follow elements for user {clean_username}")
                except Exception as e:
                    print(f"Error clicking follow button for user {clean_username}: {e}")

                await asyncio.sleep(add_jitter(2))  # Increased delay between follows with jitter
            except requests.exceptions.Timeout:
                print(f"Timeout when looking up user {clean_username}")
            except requests.exceptions.RequestException as e:
                print(f"Network error when looking up user {clean_username}: {e}")
            except KeyError as e:
                print(f"User {clean_username} not found or invalid response format: {e}")
            except Exception as e:
                print(f"Unexpected error when following user {clean_username}: {e}")
        return userIDList


if __name__ == "__main__":
    print("This is a library file. Please run main.py instead.")
