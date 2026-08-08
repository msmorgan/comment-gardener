Invoke the fully qualified `comment-gardener:comment-gardener` skill and follow it exactly.

Have the canonical skill resolve `$ARGUMENTS` as the target and optional `--mode jungle|garden|zen` brief, resolve its plugin root, and run `python3 scripts/build_packet.py` from that root to produce the canonical job packet. Pass stdout unchanged to the named `comment-gardener` worker when available; otherwise the current session consumes the same packet.

The consumer must read every named policy source and discover related reference sites from the packet's seed scopes. Do not duplicate mode policy in this adapter. An empty resolved target remains a successful no-op.
