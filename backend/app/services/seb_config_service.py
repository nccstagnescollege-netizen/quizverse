import hashlib
import plistlib
import re
import uuid
from typing import Dict, Any, Optional, Tuple


class SEBConfigService:
    """
    Handles official Safe Exam Browser (.seb) configuration generation,
    XML Property List serialization, ConfigKey / BrowserExamKey calculation,
    and HTTP verification header validation.
    """

    @staticmethod
    def hash_seb_password(raw_password: str) -> str:
        """
        Hashes passwords for SEB XML plists using SHA-256 lowercase hex string,
        as required by Safe Exam Browser specification.
        """
        if not raw_password:
            return ""
        return hashlib.sha256(raw_password.encode("utf-8")).hexdigest().lower()

    @staticmethod
    def calculate_config_key(config_dict: Dict[str, Any]) -> str:
        """
        Calculates cryptographic ConfigKey (CK).
        Normalizes the configuration by stripping non-policy metadata (like originatorVersion)
        and computing the SHA-256 digest of the canonical XML plist representation.
        """
        # Canonical subset for stable key calculation
        filtered = {k: v for k, v in config_dict.items() if k not in ["originatorVersion", "examKeySalt"]}
        # Deterministic plist serialization
        xml_bytes = plistlib.dumps(filtered, fmt=plistlib.FMT_XML, sort_keys=True)
        return hashlib.sha256(xml_bytes).hexdigest()

    @classmethod
    def generate_seb_configuration(
        cls,
        quiz_id: uuid.UUID,
        start_url: str,
        quit_url: Optional[str] = None,
        allow_quit: bool = True,
        config_password: Optional[str] = None,
        quit_password: Optional[str] = None,
        min_seb_version: str = "3.0.0",
        allow_reload: bool = False,
        enable_url_filter: bool = True,
        browser_view_mode: int = 1,
        custom_settings: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], str, str, str]:
        """
        Constructs official SEB configuration settings dictionary,
        generates XML property list (.seb), calculates ConfigKey & BrowserExamKey.
        Returns: (config_data_dict, xml_string, config_key, browser_exam_key)
        """
        actual_quit_url = quit_url or f"{start_url.split('/exam/')[0]}/exam/concluded" if "/exam/" in start_url else "https://quizverse.app/exam/concluded"

        hashed_admin_pwd = cls.hash_seb_password(config_password) if config_password else ""
        hashed_quit_pwd = cls.hash_seb_password(quit_password) if quit_password else ""

        # Base SEB Settings dictionary (compatible with SEB 2.x, 3.x Windows, macOS, and iOS)
        config: Dict[str, Any] = {
            "originatorVersion": "SEB_Win_3.0",
            "startURL": start_url,
            "sebServerURL": "",
            "hashedAdminPassword": hashed_admin_pwd,
            "hashedQuitPassword": hashed_quit_pwd,
            "allowQuit": bool(allow_quit),
            "quitURL": actual_quit_url,
            "browserWindowAllowReload": bool(allow_reload),
            "allowDownUploads": False,
            "browserViewMode": int(browser_view_mode),  # 1 = Fullscreen kiosk mode
            "allowSpellCheck": False,
            "enableURLFilter": bool(enable_url_filter),
            "URLFilterRules": [
                {
                    "action": 1,  # 1 = Allow
                    "active": True,
                    "expression": "*",
                    "regex": False,
                }
            ],
            "showTaskBar": False,
            "allowFlashFullscreen": False,
            "enableTouchExit": False,
            "sendBrowserExamKey": True,
            "quizverse_metadata": {
                "quiz_id": str(quiz_id),
                "min_seb_version": min_seb_version,
            },
        }

        if custom_settings:
            config.update(custom_settings)

        config_key = cls.calculate_config_key(config)
        browser_exam_key = hashlib.sha256(f"BEK_{quiz_id}_{config_key}".encode("utf-8")).hexdigest()

        # Add BrowserExamKey and ConfigKey reference into configuration
        config["browserExamKey"] = browser_exam_key

        # Serialize to standard XML Plist string
        xml_bytes = plistlib.dumps(config, fmt=plistlib.FMT_XML, sort_keys=True)
        xml_string = xml_bytes.decode("utf-8")

        return config, xml_string, config_key, browser_exam_key

    @staticmethod
    def calculate_request_hash(request_url: str, key: str) -> str:
        """
        Computes SHA-256 hash of (request_url + key) as sent in SEB headers.
        """
        norm_url = request_url.strip()
        norm_key = key.strip()
        return hashlib.sha256(f"{norm_url}{norm_key}".encode("utf-8")).hexdigest()

    @classmethod
    def verify_seb_headers(
        cls,
        request_url: Optional[str],
        config_key: str,
        browser_exam_key: Optional[str] = None,
        config_key_hash: Optional[str] = None,
        request_hash: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validates Safe Exam Browser cryptographic request headers:
        X-SafeExamBrowser-ConfigKeyHash and X-SafeExamBrowser-RequestHash.
        """
        if not config_key_hash and not request_hash:
            return False, "Missing cryptographic SEB request headers (ConfigKeyHash / RequestHash)."

        # If request_url is available, perform full URL + key SHA-256 hash match
        if request_url:
            if config_key_hash and config_key:
                expected_ck = cls.calculate_request_hash(request_url, config_key)
                if config_key_hash.lower() == expected_ck.lower() or config_key_hash.lower() == config_key.lower():
                    return True, "SEB ConfigKeyHash verified successfully."

            if request_hash and browser_exam_key:
                expected_bek = cls.calculate_request_hash(request_url, browser_exam_key)
                if request_hash.lower() == expected_bek.lower() or request_hash.lower() == browser_exam_key.lower():
                    return True, "SEB RequestHash verified successfully."

        # Fallback: direct ConfigKey or BEK comparison when client passes hash directly
        if config_key_hash and config_key_hash.lower() == config_key.lower():
            return True, "SEB direct ConfigKey verified."
        if request_hash and browser_exam_key and request_hash.lower() == browser_exam_key.lower():
            return True, "SEB direct BrowserExamKey verified."

        return False, "Cryptographic hash mismatch. SEB configuration may be modified, invalid, or mismatched."

    @staticmethod
    def detect_seb_client(
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Detects whether an incoming HTTP request originated from Safe Exam Browser,
        extracting version and platform (Windows / macOS / iOS).
        """
        ua = user_agent or ""
        header_keys = [k.lower() for k in (headers or {}).keys()]

        is_seb = False
        seb_ver = None
        os_platform = "unknown"

        # Check SEB Headers (must have non-empty value)
        if headers:
            for hk, hv in headers.items():
                if hk.lower() in ["x-safeexambrowser-configkeyhash", "x-safeexambrowser-requesthash"] and hv and str(hv).strip():
                    is_seb = True
                    break

        # Check User-Agent format:
        # e.g., "Mozilla/5.0 ... SEB/3.7.0" or "SafeExamBrowser/3.7.0 (Windows NT 10.0; Win64; x64)"
        seb_ua_match = re.search(r'(?:SafeExamBrowser|SEB)[/ ]([0-9]+\.[0-9]+(?:\.[0-9]+)?)', ua, re.IGNORECASE)
        if seb_ua_match:
            is_seb = True
            seb_ver = seb_ua_match.group(1)

        # Platform detection
        if "windows" in ua.lower() or "win64" in ua.lower() or "win32" in ua.lower():
            os_platform = "windows"
        elif "macintosh" in ua.lower() or "mac os" in ua.lower():
            os_platform = "macos"
        elif "iphone" in ua.lower() or "ipad" in ua.lower():
            os_platform = "ios"
        elif "linux" in ua.lower():
            os_platform = "linux"

        return is_seb, seb_ver, os_platform

    @staticmethod
    def is_version_supported(client_version: Optional[str], min_version: str = "3.0.0") -> bool:
        """
        Compares client version against required minimum version.
        """
        if not client_version:
            return False

        def parse_v(v_str: str) -> Tuple[int, ...]:
            parts = re.findall(r'\d+', v_str)
            return tuple(int(p) for p in parts[:3]) if parts else (0, 0, 0)

        client_parts = parse_v(client_version)
        min_parts = parse_v(min_version)

        # Pad with zeros to 3 elements
        while len(client_parts) < 3:
            client_parts += (0,)
        while len(min_parts) < 3:
            min_parts += (0,)

        return client_parts >= min_parts
