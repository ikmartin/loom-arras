# driver.mjs: one persistent headless Chromium page, driven by HTTP

## Start

```
cd <this folder>
nohup node driver.mjs 48199 ./shots > driver.out 2>&1 &     # port, screenshot folder
W=1100 H=800 node driver.mjs ...                            # optional starting viewport (default 1440x900)
```

It loads Playwright from `/Users/isaac/dev/loom-arras/arras/node_modules` (read-only). Browser events (console errors, page errors, failed requests, HTTP >= 400, dialogs, downloads, new tabs) are appended to `driver-events.log` next to the script, one line per event, together with every command received.

## Send commands

```
./d.sh '{"cmd":"goto","url":"http://127.0.0.1:48150/","shot":"01-home"}'
./d.sh '[{"cmd":"click","x":80,"y":57},{"cmd":"wait","ms":800},{"cmd":"shot","shot":"02"}]'   # a list runs in order, stops at the first error
```

Any command accepts `"after": ms` (pause before the screenshot) and `"shot": "name"` (saves `shots/name.png`; add `"full": true` for the full page). Every reply includes the current URL, and `dialog` if a JavaScript dialog is waiting.

| cmd | fields | what it does |
|---|---|---|
| goto / reload / back | url, wait | navigate (waits 1.5 s by default) |
| click | x, y, button, count, modifiers | mouse click at a point (`button:"right"` for context menu) |
| dblclick | x, y | double click |
| clickText | text, exact, nth, button | click the nth VISIBLE element whose text matches; returns its centre |
| hover / hoverText | x, y / text | move the mouse there; returns `tooltip` (the `title` a person would see after a pause) and the element tag |
| type | text, delay | type into whatever has focus |
| press | key | e.g. `Escape`, `Enter`, `Meta+z` |
| drag | x1, y1, x2, y2, steps | press, move, release: selects text or drags things |
| scroll | x, y, dx, dy | mouse wheel at a point |
| dropFile | path, x, y, mime, hoverOnly | simulates dragging a file from the desktop onto (x,y): dragenter/dragover, then drop unless `hoverOnly` |
| paste | text, x, y | dispatches a paste of `text` on the focused element (or the element at x,y); inserts it into a text field if the page does not handle it |
| resize | width, height | change the viewport |
| text | x, y, max | visible text (innerText) of the page, or of the element at (x,y) |
| find | text, exact | positions of visible elements containing the text (like scanning the screen) |
| selection | | the currently selected text |
| dialog | accept, text | answer a pending alert/confirm/prompt |
| pages / switch / closePage | i | list tabs, switch to tab i, close tab i |
| downloads | | files saved from downloads (in `../downloads`) |
| fresh | width, height, url, wait | throw away the browser profile (cookies, localStorage) and open a new one: a first visit |
| wait | ms | sleep |
| quit | | close the browser and stop the driver |

## Notes

- Look at every screenshot before choosing the next action; coordinates come from the screenshot (CSS pixels = image pixels at device scale 1).
- Native `title` tooltips are not painted in headless screenshots, so `hover` reports them in its reply instead.
- `dropFile` and `paste` are synthetic events: they exercise the page's own handlers but cannot reproduce what the browser itself does with an unhandled drop (e.g. opening the file).
- Stop with `./d.sh '{"cmd":"quit"}'`, then confirm with `lsof -nP -iTCP:48199 -sTCP:LISTEN` that nothing is left. Do not `pkill` Chromium by name: other testers may be running their own.
