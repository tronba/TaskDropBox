# Standalone network

TaskDropBox requires only a static private IP reachable by student and teacher computers.

```text
computers -> isolated access point/switch -> Ubuntu VM at 10.20.0.10
```

Use a temporary WPA2/WPA3 network with a strong password. Do not bridge it to the Internet or the normal school network during an outage. Permit client traffic to TCP port 80 on the VM. Restrict SSH to an operator device or wired administration network where possible.

No DNS, mDNS, public certificate, private certificate authority, captive portal, or cloud controller is required. Distribute complete task URLs by copying, printing, or through whatever local communication remains available.

Before creating tasks, verify:

- the VM has its intended static IP;
- clients can open the front page;
- server date, time, and timezone are correct;
- sufficient disk space is available;
- the WAN is blocked;
- the temporary Wi-Fi password is not a reused institutional password.

Changing the VM IP does not invalidate stored capability keys, but links containing the previous IP stop reaching the server. Set the address before distributing links.

