# Example: Custom Scripts with send() + get_script_output()

This example shows how to load custom Frida scripts and read their output.

## Scenario

You want to create a reusable "god mode" script that can be toggled on/off.

## How it works

Scripts communicate with the host by calling `send()` in JavaScript. Every
message is buffered by the MCP server and read with `get_script_output()`.
No RPC method guessing needed — the agent just polls the buffer.

## Create and Load the Script

```
> attach("game.exe")

> load_script('''
    var godModeEnabled = false;
    var healthAddress = null;

    // Find the health address
    function findHealth(currentValue) {
        var results = [];
        var ranges = Process.enumerateRanges("rw-");
        var buf = Memory.alloc(4);
        buf.writeS32(currentValue);
        var pattern = Array.from(new Uint8Array(buf.readByteArray(4)))
            .map(b => ('0' + b.toString(16)).slice(-2)).join(' ');

        for (var i = 0; i < ranges.length; i++) {
            try {
                var matches = Memory.scanSync(ranges[i].base, ranges[i].size, pattern);
                matches.forEach(m => results.push(m.address.toString()));
            } catch (e) {}
        }
        send({type: "health_addresses", addresses: results.slice(0, 100)});
    }

    // Toggle god mode
    function toggleGodMode() {
        godModeEnabled = !godModeEnabled;
        send({type: "godmode", enabled: godModeEnabled});
    }

    // Set health value
    function setHealth(value) {
        if (!healthAddress) { send({type: "error", msg: "Health address not set!"}); return; }
        healthAddress.writeS32(value);
        send({type: "health", value: value});
    }

    // Get current health
    function getHealth() {
        if (!healthAddress) { send({type: "error", msg: "Health address not set!"}); return; }
        send({type: "health", value: healthAddress.readS32()});
    }

    // Example: run findHealth(100) on load
    findHealth(100);
    console.log("[GodMode] Script loaded!");
''', "godmode")
```

## Read the Output

```
# After load, the script already ran findHealth(100) and sent results
> get_script_output("godmode")
{
  "count": 1,
  "messages": [
    {"type": "send", "payload": {"type": "health_addresses", "addresses": ["0x12345678", ...]}}
  ]
}
```

## Passing Input to a Script

Scripts are loaded with fixed code. To change behavior, load a new script
with the value embedded, or unload and reload:

```
> unload_script("godmode")

> load_script('''
    var healthAddress = ptr("0x12345678");
    healthAddress.writeS32(9999);
    send({type: "health", value: healthAddress.readS32()});
''', "set_health")

> get_script_output("set_health")
{
  "count": 1,
  "messages": [
    {"type": "send", "payload": {"type": "health", "value": 9999}}
  ]
}
```

## Long-Running Scripts

For scripts that keep running (timers, hooks), poll repeatedly:

```
> load_script('''
    setInterval(function() {
        send({type: "tick", health: ptr("0x12345678").readS32()});
    }, 1000);
''', "monitor")

# Later:
> get_script_output("monitor", limit=10, clear=true)
```

## Cleanup

```
> unload_script("godmode")
{"success": true, "name": "godmode"}

> detach()
{"success": true}
```

## Benefits of send() + get_script_output()

1. **No RPC method guessing** — the agent reads whatever the script sends
2. **Persistent State**: Variables persist while the script is loaded
3. **Complex Logic**: Full JavaScript for game-specific hacks
4. **Performance**: Script runs in-process, no IPC overhead
5. **Reusability**: Load once, poll many times