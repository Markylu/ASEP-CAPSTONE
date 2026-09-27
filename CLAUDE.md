# ASEP-CAPSTONE: notes for Claude

## sctsvr6 tunnel
- Never open, restart or kill an SSH tunnel to sctsvr6 yourself. The operator owns the tunnel
  (`ssh -N -L 8004:127.0.0.1:8004 sctsvr6`, and `:8000`).
- If the tunnel is down, slow or dropping connections, stop and tell the operator. Do not work
  around it with a tunnel on another port.
