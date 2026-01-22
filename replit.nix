cat > replit.nix <<'EOF'
{ pkgs }: {
  deps = [
    pkgs.nodejs_20
  ];
}
EOF
