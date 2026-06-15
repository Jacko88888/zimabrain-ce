from flask_app import answer_question

TESTS = [
    {
        "q": "how to install Pi-hole",
        "expect": ["VERIFIED INSTALL GUIDE", "Verified app/profile detected", "pihole"],
        "avoid": ["GENERIC INSTALL CHECKLIST", "NOT VERIFIED"],
    },
    {
        "q": "Pi-hole is installed, what should I check before changing router DNS?",
        "expect": ["VERIFIED INSTALL GUIDE", "Post-install status", "Before changing router DNS", "Test one client first"],
        "avoid": ["GENERIC INSTALL CHECKLIST", "NOT VERIFIED"],
    },
    {
        "q": "how to install MariaDB",
        "expect": ["VERIFIED INSTALL GUIDE", "Verified app/profile detected", "mariadb", "Step 1"],
        "avoid": ["GENERIC INSTALL CHECKLIST", "NOT VERIFIED"],
    },
    {
        "q": "how to install Redis",
        "expect": ["GENERIC INSTALL CHECKLIST", "Requested app name", "redis", "not been verified"],
        "avoid": ["VERIFIED INSTALL GUIDE", "NOT VERIFIED"],
    },
    {
        "q": "how to install hermes",
        "expect": ["GENERIC INSTALL CHECKLIST", "Requested app name", "hermes", "not been verified"],
        "avoid": ["VERIFIED INSTALL GUIDE", "NOT VERIFIED"],
    },
    {
        "q": "how to install bullshit",
        "expect": ["NOT VERIFIED", "No install guide generated", "requested app name"],
        "avoid": ["VERIFIED INSTALL GUIDE", "GENERIC INSTALL CHECKLIST", "/DATA/AppData/bullshit"],
    },
]

bundle = {
    "report": "",
    "docker_ps": "",
    "docker_inspect": "",
    "mounts": "",
    "df": "",
    "lsblk": "",
}

passed = 0
failed = 0
rows = []

for t in TESTS:
    q = t["q"]
    ans = answer_question(q)
    text = "\n".join(ans if isinstance(ans, list) else ans.get("lines", [])) if not isinstance(ans, str) else ans

    missing = [x for x in t["expect"] if x not in text]
    unwanted = [x for x in t["avoid"] if x in text]

    ok = not missing and not unwanted
    if ok:
        passed += 1
        status = "PASS"
    else:
        failed += 1
        status = "FAIL"

    rows.append((status, q, missing, unwanted))

print("# App Guide Trust Test Results")
print()
for status, q, missing, unwanted in rows:
    print(f"## {status}: {q}")
    if missing:
        print("Missing:", ", ".join(missing))
    if unwanted:
        print("Unexpected:", ", ".join(unwanted))
    print()

print(f"RESULT: PASS={passed} FAIL={failed} TOTAL={passed + failed}")

raise SystemExit(1 if failed else 0)
