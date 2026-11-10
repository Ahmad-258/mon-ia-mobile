[app]

title = IA Ahmad
package.name = iaahmad
package.domain = org.ahmad

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas
source.exclude_dirs = .git,.github,bin,.buildozer

version = 0.1.0

requirements = python3,kivy,requests,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.ndk = 25b
android.minapi = 23
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = False

p4a.bootstrap = sdl2
# Pin python-for-android to a revision using Python 3.11.5.
# Python 3.14 currently fails to compile its remote-debugging module for Android NDK.
# Use the Cython-based pyjnius recipe to avoid the failing PEP 517 host-python build.
p4a.commit = 83e74cac0fa230231f63b7d7e4f1e8581fd9e2ce

[buildozer]

log_level = 2
warn_on_root = 1
