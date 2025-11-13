# -*- coding: utf-8 -*-
"""Check system locale and encoding settings"""
import sys
import locale
import os

print("=" * 60)
print("System Encoding Check")
print("=" * 60)

print(f"\n1. Python Default Encoding:")
print(f"   sys.getdefaultencoding(): {sys.getdefaultencoding()}")
print(f"   sys.stdout.encoding: {sys.stdout.encoding}")
print(f"   sys.stderr.encoding: {sys.stderr.encoding}")
print(f"   sys.stdin.encoding: {sys.stdin.encoding}")

print(f"\n2. Filesystem Encoding:")
print(f"   sys.getfilesystemencoding(): {sys.getfilesystemencoding()}")

print(f"\n3. Locale Settings:")
print(f"   locale.getpreferredencoding(): {locale.getpreferredencoding()}")
print(f"   locale.getlocale(): {locale.getlocale()}")

print(f"\n4. Environment Variables:")
print(f"   LANG: {os.getenv('LANG', 'Not set')}")
print(f"   LC_ALL: {os.getenv('LC_ALL', 'Not set')}")
print(f"   LC_CTYPE: {os.getenv('LC_CTYPE', 'Not set')}")

print("\n" + "=" * 60)
print("Test Vietnamese Characters")
print("=" * 60)

test_string = "Đây là test tiếng Việt: ăắâêôơưảãạ"
print(f"\nTest string: {test_string}")

try:
    encoded_utf8 = test_string.encode('utf-8')
    print(f"✓ UTF-8 encoding works: {len(encoded_utf8)} bytes")
except Exception as e:
    print(f"✗ UTF-8 encoding failed: {e}")

try:
    encoded_ascii = test_string.encode('ascii')
    print(f"✓ ASCII encoding works (unexpected!)")
except Exception as e:
    print(f"✓ ASCII encoding fails as expected: {type(e).__name__}")

print("\n" + "=" * 60)
