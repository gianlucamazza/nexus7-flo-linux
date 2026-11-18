# GTK4 Settings crash on flo: symbolized evidence

The running tablet has `gnome-control-center 51.1-r0`, `gtk4.0 4.24.1-r0`
and `mesa 26.3.0-r0` on armv7. Two `gnome-control-center` SIGSEGV dumps from
16 November end at the same `libgtk-4.so.1 + 0x41b1bc` offset (PIDs 2498 and
2420, at 11:43 and 14:53 CET). Two later SIGTRAP dumps share a fatal-log
abort path caused by a missing GSettings schema, as established below.
Hyprland's SIGABRT at 16:47 is also a separate crash.

The 14:53 journal, immediately before PID 2420 crashed, records three
`gdk_gl_context_make_current() failed` messages and one
`gdk_gl_context_get_use_es: assertion 'GDK_IS_GL_CONTEXT (context)' failed`.
The 11:43 journal has no corresponding GL diagnostic in the retained excerpt.
There is no OOM kill at the 11:43 event; its core reports SIGSEGV/SEGV_MAPERR.

The PID 2498 core was symbolized with the exact
[`gtk4.0-dbg 4.24.1-r0 armv7`](https://pkgs.alpinelinux.org/package/edge/community/armv7/gtk4.0-dbg)
package, without installing it on the tablet. The relevant main-thread frames:

```text
#0 gdk_gl_context_get_format_flags(self=0x0,
#      format=GDK_MEMORY_B8G8R8A8_PREMULTIPLIED)
#      at gdk/gdkglcontext.c:2198
#1 gsk_gl_device_get_format_flags(context=0x0, ...)
#      at gsk/gpu/gskgldevice.c:283
#2 gsk_gl_device_find_gl_format(...)
#      at gsk/gpu/gskgldevice.c:333
#3 gsk_gl_image_new_backbuffer(..., width=1200, ...)
#      at gsk/gpu/gskglimage.c:110
#4 gsk_gl_renderer_get_backbuffer(...)
#      at gsk/gpu/gskglrenderer.c:118
#5 gsk_gpu_renderer_render(...)
```

This proves the immediate fault is a null GL context consumed in GTK's GL
render path. The 14:53 diagnostics make a preceding GL context failure likely
for that crash. They do **not** identify why context creation or activation
failed: GTK's error path, Mesa's Adreno driver, EGL, and compositor interaction
still need to be separated. The identical unsymbolized offset in the second
SIGSEGV is strong evidence for the same immediate fault, not proof of an
identical lower-level trigger.

The exact [GTK 4.24.1 GL-context implementation][gtk-context] shows why the
warning can lead to that fault: `gdk_gl_context_make_current()` logs
`gdk_gl_context_make_current() failed` and returns when the backend's
`make_current` method fails. The default EGL backend returns failure if its
EGL context is absent or `eglMakeCurrent()` returns false. The
[GL renderer][gtk-renderer] calls that `void` function, and the
[GPU renderer][gtk-gpu-renderer] continues to create a backbuffer without
checking `gdk_gl_context_get_current()`. The symbolized crash reaches
`gsk_gl_device_find_gl_format()` with that current context null. This
source path explains the immediate GTK error-handling failure after a
failed context activation. It does not distinguish a missing backend EGL
context from an `eglMakeCurrent()` error, nor identify a Mesa, DRM, or
compositor cause. The next native reproduction should capture `eglGetError()`
at the first failed `eglMakeCurrent()` and the EGL context/surface handles.

The copied core and debug package were extracted only into a private temporary
directory on the host and removed when GDB finished. No process memory or
firmware payload was committed.

## The two later SIGTRAP events

The 20:43 and 20:44 cores (PIDs 1040 and 1153) both report `SIGTRAP` with
`SI_TKILL`. Their PCs map to the same `ld-musl-armhf.so.1` offset
`0x4717a`; the next frame is in the musl `raise()` path. Recovering the
saved return address from the first core and resolving it against the
exact [`gnome-control-center-dbg 51.1-r0`](https://pkgs.alpinelinux.org/package/edge/community/armv7/gnome-control-center-dbg)
package identifies `_g_log_abort()` at `shell/cc-log.c:71`. The installed
executable and debug file share build ID
`b6166de35196765e59f8334e64d7e013ef96bc71`. The
[GNOME 51.1 logging source](https://gitlab.gnome.org/GNOME/gnome-control-center/-/raw/51.1/shell/cc-log.c)
calls this path for a fatal log message or error. Both cores also contain
`GSK_RENDERER=cairo`, which places them in the separate Cairo renderer
experiment. A search of the core memory found no `G_DEBUG=` value, but
does not prove that every environment variable was retained.

The fatal message remains in each core's log buffer, even though it was
not retained in the journal. Both say:

```text
GLib-GIO: ERROR: Settings schema 'org.gnome.settings-daemon.plugins.color' is not installed
```

The journal's concurrent portal dependency failures reflect an inactive
graphical session; they do not explain this trap. The package log records
`apk add gnome-settings-daemon` at 20:44:37 CET, after the second trap.
The resolved package `gnome-settings-daemon-mobile-999948.0-r3` owns
`org.gnome.settings-daemon.plugins.color.gschema.xml`. On the running tablet,
`gsettings list-schemas` now includes the schema and there are no newer
Settings cores. This proves the missing-schema condition is gone, though
it does not replace a fresh Settings launch test. The SIGTRAPs must not be
counted as additional reproductions of the GTK null-GL-context SIGSEGV.
Core copies and binaries used for this analysis were held in private
temporary directories and removed after symbolization.

[gtk-context]: https://gitlab.gnome.org/GNOME/gtk/-/raw/4.24.1/gdk/gdkglcontext.c
[gtk-renderer]: https://gitlab.gnome.org/GNOME/gtk/-/raw/4.24.1/gsk/gpu/gskglrenderer.c
[gtk-gpu-renderer]: https://gitlab.gnome.org/GNOME/gtk/-/raw/4.24.1/gsk/gpu/gskgpurenderer.c

Next investigation: reproduce with a small GTK4 GL surface on the tablet
while power and physical recovery are stable; collect the *first* EGL/GDK/Mesa
error and kernel GPU trace, not just the final SIGSEGV. Compare the same
application under GTK's other supported renderer as a diagnostic A/B with
stderr captured for both runs, then
fix the failing GL context path or report a minimal GTK null-context bug with
the symbolized stack. A renderer switch alone would not close this issue.
