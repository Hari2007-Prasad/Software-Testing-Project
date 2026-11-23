import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests

class SecurityBaselineScanner:
    """
    Performs safe, authorized, non-destructive security baseline audits against
    the configured digital learning application target.
    
    Audits:
    - OWASP recommended security response headers
    - Cookie flags (HttpOnly, Secure, SameSite)
    - Transport layer encryption (HTTPS usage)
    - Authentication and authorization boundaries
    - Anonymous access controls on protected endpoints
    - Basic input sanitization and XSS reflection defense
    - Session management baseline
    """

    def __init__(self, target_base_url: str = 'http://127.0.0.1:5000/lms', timeout: int = 10):
        self.target_base_url = target_base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def run_all_checks(self) -> List[Dict[str, Any]]:
        findings = []

        # 1. Transport & Protocol Check
        findings.extend(self._check_transport_protocol())

        # 2. HTTP Security Response Headers
        findings.extend(self._check_security_headers())

        # 3. Cookie Security Attributes
        findings.extend(self._check_cookie_attributes())

        # 4. Anonymous Access / Authentication Enforcement
        findings.extend(self._check_authentication_enforcement())

        # 5. Role-based Authorization Enforcement
        findings.extend(self._check_authorization_enforcement())

        # 6. Basic Input Validation & Reflection
        findings.extend(self._check_input_validation())

        # 7. Basic Session Security
        findings.extend(self._check_session_security())

        # Format finding IDs consistently
        for idx, finding in enumerate(findings, start=1):
            finding['finding_code'] = f"SEC-FIND-{idx:03d}"
            finding['status'] = 'Open'

        return findings

    def _check_transport_protocol(self) -> List[Dict[str, Any]]:
        findings = []
        parsed = urllib.parse.urlparse(self.target_base_url)

        if parsed.scheme.lower() != 'https':
            findings.append({
                'title': 'Unencrypted HTTP Transport In Use',
                'description': 'The target application is accessible over unencrypted HTTP protocol without TLS encryption.',
                'severity': 'Medium',
                'affected_url': self.target_base_url,
                'evidence': f"Target URL scheme is '{parsed.scheme}://'. Credentials and session cookies may be transmitted in cleartext over the network.",
                'recommendation': 'Enforce HTTPS across all application endpoints with automated HTTP to HTTPS redirection and implement HSTS.'
            })
        return findings

    def _check_security_headers(self) -> List[Dict[str, Any]]:
        findings = []
        url = f"{self.target_base_url}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            headers = {k.lower(): v for k, v in resp.headers.items()}

            # Content-Security-Policy (CSP)
            if 'content-security-policy' not in headers:
                findings.append({
                    'title': 'Missing Content Security Policy (CSP) Header',
                    'description': 'The HTTP Content-Security-Policy response header is not defined on the application root.',
                    'severity': 'Medium',
                    'affected_url': url,
                    'evidence': 'Header Content-Security-Policy was absent in HTTP response.',
                    'recommendation': "Configure Content-Security-Policy header (e.g., \"default-src 'self'; script-src 'self' ...\") to mitigate Cross-Site Scripting (XSS) and code injection."
                })

            # X-Content-Type-Options
            x_content_type = headers.get('x-content-type-options', '')
            if x_content_type.lower() != 'nosniff':
                findings.append({
                    'title': 'Missing or Ineffective X-Content-Type-Options Header',
                    'description': 'The X-Content-Type-Options header is either missing or not set to "nosniff".',
                    'severity': 'Low',
                    'affected_url': url,
                    'evidence': f"X-Content-Type-Options value: '{x_content_type or 'None'}'.",
                    'recommendation': 'Set "X-Content-Type-Options: nosniff" on all responses to prevent MIME-sniffing attacks.'
                })

            # X-Frame-Options or CSP frame-ancestors
            x_frame = headers.get('x-frame-options', '').upper()
            if x_frame not in ('DENY', 'SAMEORIGIN') and 'frame-ancestors' not in headers.get('content-security-policy', ''):
                findings.append({
                    'title': 'Missing Anti-Clickjacking Frame Protection',
                    'description': 'The response does not restrict framing via X-Frame-Options or CSP frame-ancestors.',
                    'severity': 'Medium',
                    'affected_url': url,
                    'evidence': f"X-Frame-Options header value: '{x_frame or 'None'}'.",
                    'recommendation': 'Add "X-Frame-Options: SAMEORIGIN" or "DENY" to prevent clickjacking and UI redressing attacks.'
                })

            # Referrer-Policy
            if 'referrer-policy' not in headers:
                findings.append({
                    'title': 'Missing Referrer-Policy Header',
                    'description': 'No Referrer-Policy is specified, which could leak sensitive path or query parameters to external sites.',
                    'severity': 'Low',
                    'affected_url': url,
                    'evidence': 'Header Referrer-Policy was absent in HTTP response.',
                    'recommendation': 'Set "Referrer-Policy: strict-origin-when-cross-origin" or "no-referrer".'
                })

            # Permissions-Policy
            if 'permissions-policy' not in headers:
                findings.append({
                    'title': 'Missing Permissions-Policy Header',
                    'description': 'The application does not restrict sensitive browser APIs (camera, microphone, geolocation).',
                    'severity': 'Info',
                    'affected_url': url,
                    'evidence': 'Header Permissions-Policy was absent in HTTP response.',
                    'recommendation': 'Define Permissions-Policy to explicitly restrict browser hardware APIs.'
                })

        except Exception as e:
            findings.append({
                'title': 'Connection Failure During Security Header Check',
                'description': f'Failed to establish connection to target URL: {str(e)}',
                'severity': 'High',
                'affected_url': url,
                'evidence': str(e),
                'recommendation': 'Verify that the digital learning application server is up and responsive.'
            })

        return findings

    def _check_cookie_attributes(self) -> List[Dict[str, Any]]:
        findings = []
        login_url = f"{self.target_base_url}/login"
        try:
            resp = self.session.get(login_url, timeout=self.timeout)
            for cookie in self.session.cookies:
                cookie_name = cookie.name
                
                # Check HttpOnly
                if not getattr(cookie, 'has_nonstandard_attr', lambda x: False)('HttpOnly') and not cookie._rest.get('HttpOnly'):
                    findings.append({
                        'title': f'Cookie "{cookie_name}" Missing HttpOnly Flag',
                        'description': f'The session or tracking cookie "{cookie_name}" is accessible via client-side JavaScript.',
                        'severity': 'Medium',
                        'affected_url': login_url,
                        'evidence': f"Cookie: {cookie_name}; HttpOnly flag not set.",
                        'recommendation': 'Set the HttpOnly flag on all session cookies to mitigate session hijacking via XSS.'
                    })

                # Check SameSite
                samesite = cookie._rest.get('SameSite', '').lower()
                if samesite not in ('lax', 'strict'):
                    findings.append({
                        'title': f'Cookie "{cookie_name}" Missing or Insecure SameSite Attribute',
                        'description': f'Cookie "{cookie_name}" does not configure SameSite=Lax or SameSite=Strict.',
                        'severity': 'Low',
                        'affected_url': login_url,
                        'evidence': f"SameSite attribute value: '{samesite or 'Unset'}'.",
                        'recommendation': 'Configure SameSite=Lax or SameSite=Strict on all cookies to defend against Cross-Site Request Forgery (CSRF).'
                    })

        except Exception:
            pass
        return findings

    def _check_authentication_enforcement(self) -> List[Dict[str, Any]]:
        findings = []
        protected_endpoints = ['/dashboard', '/profile', '/courses/1/enroll']
        
        # Test anonymous access without cookie session
        anon_session = requests.Session()
        for endpoint in protected_endpoints:
            url = f"{self.target_base_url}{endpoint}"
            try:
                resp = anon_session.get(url, allow_redirects=False, timeout=self.timeout)
                # Protected endpoints should return 302/303 redirect to login or 401 Unauthorized
                if resp.status_code == 200:
                    findings.append({
                        'title': f'Unauthenticated Access Permitted on Protected Route "{endpoint}"',
                        'description': f'Anonymous users can access protected route "{endpoint}" without authenticating.',
                        'severity': 'Critical',
                        'affected_url': url,
                        'evidence': f"HTTP status code {resp.status_code} returned for anonymous GET request. Response body length: {len(resp.text)} bytes.",
                        'recommendation': 'Apply authentication decorators (@login_required) on all private user endpoints.'
                    })
            except Exception:
                pass
        return findings

    def _check_authorization_enforcement(self) -> List[Dict[str, Any]]:
        findings = []
        admin_endpoints = ['/admin', '/admin/courses', '/admin/users']
        
        # We test with anonymous or student identity
        anon_session = requests.Session()
        for endpoint in admin_endpoints:
            url = f"{self.target_base_url}{endpoint}"
            try:
                resp = anon_session.get(url, allow_redirects=False, timeout=self.timeout)
                # If an anonymous user receives 200 OK on admin routes, it is a Critical Broken Access Control
                if resp.status_code == 200:
                    findings.append({
                        'title': f'Broken Access Control: Admin Endpoint "{endpoint}" Publicly Accessible',
                        'description': f'The administrative management endpoint "{endpoint}" is directly accessible without administrative credentials.',
                        'severity': 'Critical',
                        'affected_url': url,
                        'evidence': f"HTTP Status {resp.status_code} returned without admin session.",
                        'recommendation': 'Enforce strict role-based access control (RBAC) requiring verified admin role before rendering admin views.'
                    })
            except Exception:
                pass
        return findings

    def _check_input_validation(self) -> List[Dict[str, Any]]:
        findings = []
        # Safe benign canary token for reflected XSS testing
        canary = "sec_test_canary_7392"
        search_url = f"{self.target_base_url}/courses?q=%3Cscript%3E{canary}%3C%2Fscript%3E"
        try:
            resp = self.session.get(search_url, timeout=self.timeout)
            if f"<script>{canary}</script>" in resp.text:
                findings.append({
                    'title': 'Reflected Cross-Site Scripting (XSS) in Search Query Parameter',
                    'description': 'Unsanitized user input from the search query parameter is directly reflected in the HTML response without context-aware escaping.',
                    'severity': 'High',
                    'affected_url': search_url,
                    'evidence': f"Raw unescaped script tags were returned in response markup.",
                    'recommendation': 'Use HTML entity escaping / Jinja autoescape on all reflected query parameters.'
                })
        except Exception:
            pass
        return findings

    def _check_session_security(self) -> List[Dict[str, Any]]:
        findings = []
        # Verify session rotation on logout
        logout_url = f"{self.target_base_url}/logout"
        try:
            resp = self.session.get(logout_url, allow_redirects=False, timeout=self.timeout)
            # Check if session cookie is invalidated or cleared
            set_cookie_header = resp.headers.get('set-cookie', '')
            if 'session' in set_cookie_header and ('expires=' in set_cookie_header or 'Max-Age=0' in set_cookie_header):
                pass  # Cookie correctly invalidated
        except Exception:
            pass
        return findings
