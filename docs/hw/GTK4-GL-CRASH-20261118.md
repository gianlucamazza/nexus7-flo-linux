# GTK4 Settings crash on flo: symbolized evidence

The running tablet has `gnome-control-center 51.1-r0`, `gtk4.0 4.24.1-r0`
and `mesa 26.3.0-r0` on armv7. Two `gnome-control-center` SIGSEGV dumps from
16 November end at the same `libgtk-4.so.1 + 0x41b1bc` offset (PIDs 2498 and
2420, at 11:43 and 14:53 CET). Two later SIGTRAP dumps are separate events;
the available journal does not establish that they share the same cause.
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

The copied core and debug package were extracted only into a private temporary
directory on the host and removed when GDB finished. No process memory or
firmware payload was committed.

Next investigation: reproduce with a small GTK4 GL surface on the tablet
while power and physical recovery are stable; collect the *first* EGL/GDK/Mesa
error and kernel GPU trace, not just the final SIGSEGV. Compare the same
application under GTK's other supported renderer as a diagnostic A/B, then
fix the failing GL context path or report a minimal GTK null-context bug with
the symbolized stack. A renderer switch alone would not close this issue.
