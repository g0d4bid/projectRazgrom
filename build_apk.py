"""Build and sign a demonstration APK with Android SDK 35 and JDK 17."""
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SDK = Path(os.environ["ANDROID_HOME"])
TOOLS = SDK / "build-tools" / "35.0.0"
PLATFORM = SDK / "platforms" / "android-35" / "android.jar"
JAVA = Path(os.environ["JAVA_HOME"]) / "bin"
SRC = ROOT / "android/src/main"
OUT = ROOT / "dist"
OUT.mkdir(exist_ok=True)
WIN = os.name == "nt"


def run(program, *args):
    subprocess.run([str(program), *map(str, args)], check=True)


def jdk(name):
    return JAVA / (name + (".exe" if WIN else ""))


with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    classes = work / "classes"
    classes.mkdir()
    run(jdk("javac"), "--release", "8", "-encoding", "UTF-8", "-cp", PLATFORM,
        "-d", classes, *sorted((SRC / "java").rglob("*.java")))
    jar = work / "classes.jar"
    run(jdk("jar"), "cf", jar, "-C", classes, ".")
    run(jdk("java"), "-cp", TOOLS / "lib/d8.jar", "com.android.tools.r8.D8",
        "--min-api", "26", "--lib", PLATFORM, "--output", work, jar)
    unsigned = work / "base.apk"
    run(TOOLS / ("aapt2.exe" if WIN else "aapt2"), "link", "-I", PLATFORM,
        "--manifest", SRC / "AndroidManifest.xml", "-o", unsigned)
    with zipfile.ZipFile(unsigned, "a") as apk:
        apk.write(work / "classes.dex", "classes.dex")
    aligned = work / "aligned.apk"
    run(TOOLS / ("zipalign.exe" if WIN else "zipalign"), "-f", "4", unsigned, aligned)
    # Ephemeral signing key for a single classroom build.
    key = work / "demo.p12"
    run(jdk("keytool"), "-genkeypair", "-keystore", key, "-storetype", "PKCS12",
        "-storepass", "android", "-keypass", "android", "-alias", "demo",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
        "-dname", "CN=Razgrom Classroom Demo")
    signer = TOOLS / "lib/apksigner.jar"
    output = OUT / "Razgrom-1.0.apk"
    run(jdk("java"), "-jar", signer, "sign", "--ks", key, "--ks-pass",
        "pass:android", "--out", output, aligned)
    run(jdk("java"), "-jar", signer, "verify", "--verbose", output)
    print(output)
