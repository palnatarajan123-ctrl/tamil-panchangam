{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.cairo
    pkgs.pango
    pkgs.gdk-pixbuf
    pkgs.libffi
    pkgs.glib
  ];
}
