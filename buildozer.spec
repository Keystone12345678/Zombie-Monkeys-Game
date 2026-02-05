[app]
title = Zombie Monkeys Survival
package.name = zombiemonkeys
package.domain = org.zombiemonkeys
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,wav,mp3
version = 1.0
requirements = python3,kivy==2.2.1
orientation = landscape
fullscreen = 1
android.archs = arm64-v8a, armeabi-v7a
# WICHTIG: Erzeugt das AAB Format
android.release_artifact = aab
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE
android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

# p4a settings
p4a.branch = master
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1