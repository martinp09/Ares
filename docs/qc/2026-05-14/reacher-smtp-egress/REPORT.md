# Reacher SMTP Egress QC

## Scope

Diagnose why Reacher / SMTP-capable email verification cannot use outbound SMTP from the Hetzner VPS even though the Hetzner firewall UI says outbound traffic is allowed.

## Result

Outbound TCP port `25` from this VPS to multiple public MX hosts times out.

Local firewall checks show:

- `ufw`: inactive
- `iptables OUTPUT`: `ACCEPT`

Control checks show general outbound networking works:

- `google.com:443`: connects
- `smtp.gmail.com:587`: connects

Interpretation: this is not an Ares/Reacher app bug and not the local VPS firewall. It is consistent with provider/network-level SMTP egress blocking on port `25`, which is common on Hetzner Cloud for abuse prevention.

## Reacher impact

Reacher-style SMTP mailbox verification needs outbound TCP `25` to recipient MX hosts. Port `587` working does not solve recipient-MX probing, because `587` is message submission to a configured SMTP server, not mailbox verification against arbitrary recipient domains.

## Safe next options

1. Request SMTP port `25` unblock from Hetzner for this VPS/account.
2. Run SMTP verifier sidecar from an allowed/reputable verification host.
3. Use Ares DNS/MX/disposable-domain checks only until SMTP egress is available.
4. Use a commercial verification API if deliverability confidence matters more than open-source/self-hosted purity.

## Safety note

No mail was sent. Probes only attempted TCP connections and SMTP banner read/`QUIT` where possible. All port `25` MX attempts timed out before any SMTP session was established.
