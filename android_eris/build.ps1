# build.ps1 — Compila el APK de ERIS Android sin Gradle.
# Toolchain: JDK 17 (Temurin) + Android build-tools 34 + platform android-34.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BT   = "D:\Eris_Source\android_build\sdk\build-tools\34.0.0"
$ANDROID_JAR = "D:\Eris_Source\android_build\sdk\platforms\android-34\android.jar"
$JDK  = "D:\Eris_Source\android_build\jdk\jdk-17.0.20+8\bin"
$KEYS = "D:\Eris_Source\android_build\keys"
$KS   = "$KEYS\eris.keystore"
$PASS = "eris2026"

$env:JAVA_HOME = Split-Path $JDK -Parent
$env:PATH = "$JDK;" + $env:PATH

$aapt2    = "$BT\aapt2.exe"
$d8       = "$BT\d8.bat"
$zipalign = "$BT\zipalign.exe"
$apksigner= "$BT\apksigner.bat"
$javac    = "$JDK\javac.exe"
$keytool  = "$JDK\keytool.exe"
$jar      = "$JDK\jar.exe"

$build = "$Root\build"
foreach ($d in @("$build\res", "$build\gen", "$build\classes", "$build\dex")) {
    if (Test-Path $d) { Remove-Item -Recurse -Force $d }
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

Write-Host "[1/7] aapt2 compile (recursos)..."
& $aapt2 compile --dir "$Root\res" -o "$build\res\res.zip"
if ($LASTEXITCODE -ne 0) { throw "aapt2 compile fallo" }

Write-Host "[2/7] aapt2 link (manifest + assets + R.java)..."
& $aapt2 link `
    -I $ANDROID_JAR `
    --manifest "$Root\AndroidManifest.xml" `
    -A "$Root\assets" `
    --java "$build\gen" `
    --auto-add-overlay `
    --min-sdk-version 26 `
    --target-sdk-version 34 `
    --version-code 1 `
    --version-name "1.0" `
    -o "$build\unsigned.apk" `
    "$build\res\res.zip"
if ($LASTEXITCODE -ne 0) { throw "aapt2 link fallo" }

Write-Host "[3/7] javac (fuentes)..."
$sources = @(Get-ChildItem "$build\gen" -Recurse -Filter *.java | Select-Object -ExpandProperty FullName)
$sources += Get-ChildItem "$Root\java" -Recurse -Filter *.java | Select-Object -ExpandProperty FullName
& $javac -encoding UTF-8 --release 8 -classpath $ANDROID_JAR -d "$build\classes" $sources
if ($LASTEXITCODE -ne 0) { throw "javac fallo" }

Write-Host "[4/7] d8 (dex)..."
& $jar --create --file "$build\classes.jar" -C "$build\classes" .
if ($LASTEXITCODE -ne 0) { throw "jar fallo" }
& $d8 --release --lib $ANDROID_JAR --min-api 26 --output "$build\dex" "$build\classes.jar"
if ($LASTEXITCODE -ne 0) { throw "d8 fallo" }

Write-Host "[5/7] agregar classes.dex al apk..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open("$build\unsigned.apk", 'Update')
$entry = $zip.CreateEntry("classes.dex")
$src = [System.IO.File]::ReadAllBytes("$build\dex\classes.dex")
$stream = $entry.Open()
$stream.Write($src, 0, $src.Length)
$stream.Close()
$zip.Dispose()

Write-Host "[6/7] zipalign..."
& $zipalign -f 4 "$build\unsigned.apk" "$build\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw "zipalign fallo" }

if (-not (Test-Path $KS)) {
    Write-Host "Generando keystore..."
    & $keytool -genkeypair -v -keystore $KS -alias eris -keyalg RSA -keysize 2048 `
        -validity 10000 -storepass $PASS -keypass $PASS -dname "CN=ERIS Android, OU=ERIS, O=ERIS, L=Home, C=AR"
}

Write-Host "[7/7] firmar APK..."
& $apksigner sign --ks $KS --ks-pass "pass:$PASS" --key-pass "pass:$PASS" `
    --out "$Root\eris_android.apk" "$build\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw "apksigner fallo" }

$size = [math]::Round((Get-Item "$Root\eris_android.apk").Length / 1MB, 2)
Write-Host ""
Write-Host "OK! APK generado: $Root\eris_android.apk ($size MB)"
Write-Host "Instalar en el celular: adb install -r eris_android.apk"
