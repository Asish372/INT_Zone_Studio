INT Zone Studio — Standalone Pilot Build v1
==========================================

Client ko ye EK file deni hai:

  INT Zone Studio Standalone Setup 0.1.0-pilot.1.exe

SETUP (client machine)
----------------------
1. Setup exe double-click karein
2. Install complete hone ke baad Start Menu se "INT Zone Studio" kholein
   (ya desktop shortcut)
3. Python / backend / terminal ki zaroorat NAHI

YE BUILD KYA KARTA HAI
----------------------
- App ke andar detection engine bundled hai
- Open hote hi engine auto-start hota hai
- Data save hota hai: %LOCALAPPDATA%\com.administrator.desktopstudio

REQUIREMENTS
------------
- Windows 10/11 (64-bit, 64-bit only)
- Internet on first install only if WebView2 is missing (installer handles this)
- No Python, no ODA, no manual setup

DRAWING FILES
-------------
- DXF and DWG both supported (DWG converter bundled inside installer)
- MATLAB / AutoCAD se export ki DXF ya DWG dono chalegi
- Large drawings may take 30–60 seconds on first import — wait for Loading to finish

IF SOMETHING FAILS
------------------
1. Red error bar on screen — read the message
2. Close INT Zone Studio completely (all windows), reopen from Start Menu
3. Wait 5 seconds after open before Import
4. If import still fails, try exporting the drawing as DXF from CAD and import DXF
5. Uninstall old build, install the latest setup exe again

PILOT WORKFLOW
--------------
Import -> Detect -> Review -> Recovery -> Save -> Reopen -> Export
