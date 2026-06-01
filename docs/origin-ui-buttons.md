# Origin UI Buttons

Origin can run LabTalk from toolbar buttons, custom menus, and the built-in
Custom Routine button. `origin-mcp` can use those entry points so bridge startup
and shutdown no longer require pasting `addon.py` into the Python Console.

## OPX Installer

Build the Origin App source folder and install it into Origin's per-user Apps
folder in one step:

```powershell
python scripts\build_origin_app.py --force --install
```

This creates `build\origin-app\Origin MCP Bridge Start` and
`build\origin-app\Origin MCP Bridge Stop`, then copies both folders to
`%LOCALAPPDATA%\OriginLab\Apps`. After restarting Origin, the two Apps are
already installed and usable from the Apps gallery — no OPX needed for your own
machine.

To create a **distributable** OPX, pack the installed App with `mkOPX` in its
canonical `app:=` form from Origin's Command Window:

```labtalk
mkOPX app:="Origin MCP Bridge Start" opx:="C:\path\to\origin-mcp\build\origin-app\Origin MCP Bridge Start.opx";
mkOPX app:="Origin MCP Bridge Stop" opx:="C:\path\to\origin-mcp\build\origin-app\Origin MCP Bridge Stop.opx";
```

`app:=` packs the App from its Apps-folder location, so the OPX stores files
relative to the Apps base and installs cleanly into `Apps\...` on every
machine. (The older `mkOPX ini:=` + `[Files]SourcePath` form is not used:
mkOPX did not honor the source path and nested installs under the full build
path, e.g. `Apps\origin-mcp\build\origin-app\package-root\...`.) Use backslashes
in the quoted `opx:=` path — forward slashes can make `mkOPX` hang (Origin shows
"Not Responding"). The build writes this command to
`build\origin-app\mkopx-command.txt`. The expected output is:

```text
build\origin-app\Origin MCP Bridge Start.opx
build\origin-app\Origin MCP Bridge Stop.opx
```

Install both OPX files on other machines by dragging them into Origin or using
Origin's Package Manager.
After installation, the Apps gallery shows **Origin MCP Bridge Start** and
**Origin MCP Bridge Stop**. Click Start to run the bridge in reliable foreground
mode. Click Stop to request shutdown from a separate App entry point.

The Start App runs `addon.py` inside Origin's embedded Python. The Stop App uses
an external hidden helper to send a bridge `shutdown` request with
`release_origin=true`, so it can stop the foreground bridge even when Origin's
embedded Python is busy serving requests.

## Quick Setup With Custom.ogs

Origin's Standard toolbar includes a Custom Routine button that runs LabTalk
stored in `Custom.ogs`. Hold `Ctrl+Shift` and click the Custom Routine button to
open `Custom.ogs`, then add these sections.

Replace `C:\path\to\origin-mcp` with your checkout path.

```labtalk
[OriginMCPStart]
string addon_path$ = "C:\path\to\origin-mcp\addon.py";
run -pyf "%(addon_path$)";

[OriginMCPStop]
string py$ = "import sys; addon = sys.modules.get('origin_mcp_addon'); print(addon.request_stop_origin_mcp_bridge() if addon else {'stop_requested': False, 'reason': 'not_running_in_this_python_context'})";
run -py "%(py$)";

[OriginMCPStatus]
string py$ = "import sys; addon = sys.modules.get('origin_mcp_addon'); print(addon.origin_mcp_bridge_status() if addon else {'running': False})";
run -py "%(py$)";
```

Run a section from the Command Window:

```labtalk
run.section(Custom, OriginMCPStart);
run.section(Custom, OriginMCPStop);
run.section(Custom, OriginMCPStatus);
```

You can bind each section to a toolbar button or custom menu item with the same
`run.section(...)` commands.

## Dedicated OGS File

If you prefer a separate script file, save this as `origin-mcp.ogs` in Origin's
User Files Folder:

```labtalk
[Start]
string addon_path$ = "C:\path\to\origin-mcp\addon.py";
run -pyf "%(addon_path$)";

[Stop]
string py$ = "import sys; addon = sys.modules.get('origin_mcp_addon'); print(addon.request_stop_origin_mcp_bridge() if addon else {'stop_requested': False, 'reason': 'not_running_in_this_python_context'})";
run -py "%(py$)";

[Status]
string py$ = "import sys; addon = sys.modules.get('origin_mcp_addon'); print(addon.origin_mcp_bridge_status() if addon else {'running': False})";
run -py "%(py$)";
```

Then the button or menu commands are:

```labtalk
run.section(origin-mcp, Start);
run.section(origin-mcp, Stop);
run.section(origin-mcp, Status);
```

If the `.ogs` file is outside the User Files Folder, use its full path in
`run.section(...)`.

## Notes

The bridge defaults to foreground serving because that is the most reliable
mode across Origin embedded Python builds. While the bridge is active, Origin's
Python Console or the starting script remains busy, but `addon.py` pumps Windows
messages so Origin can still process UI events, including the stop button.

If the stop button reports `not_running_in_this_python_context`, the bridge was
not started by this Origin Python session or the active Python context was
reset. In that case, use `scripts\stop-bridge.cmd` or ask the MCP assistant to
call `origin_bridge_shutdown`.
