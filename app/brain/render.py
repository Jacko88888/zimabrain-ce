from html import escape as html_escape
import re


COPY_CODE_CSS = """
.codeblock-wrap {
  position: relative;
}
.copy-code {
  position:absolute;
  top:10px;
  right:10px;
  background:#1e293b;
  color:#dbeafe;
  border:1px solid #475569;
  border-radius:8px;
  padding:5px 9px;
  font-size:12px;
  font-weight:800;
  cursor:pointer;
}
.copy-code:hover {
  background:#334155;
}
"""

COPY_CODE_JS = """
<script>
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("pre.codeblock").forEach(function (pre) {
    if (pre.parentElement && pre.parentElement.classList.contains("codeblock-wrap")) return;

    const wrap = document.createElement("div");
    wrap.className = "codeblock-wrap";
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);

    const btn = document.createElement("button");
    btn.className = "copy-code";
    btn.type = "button";
    btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      const code = pre.innerText || pre.textContent || "";
      navigator.clipboard.writeText(code).then(function () {
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = "Copy"; }, 1200);
      });
    });
    wrap.appendChild(btn);
  });
});
</script>
"""


def esc(text):
    return html_escape(str(text or ""))


def render_answer_html(md):
    raw = str(md or "")
    html = []
    in_code = False
    code_lines = []

    def inline_format(text):
        text = esc(text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        return text

    for line in raw.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                html.append('<pre class="codeblock"><code>' + esc("\n".join(code_lines)) + "</code></pre>")
                in_code = False
            continue

        if in_code:
            code_lines.append(line)
            continue

        if stripped == "":
            html.append("")
        elif stripped.startswith("#### "):
            html.append("<h4>" + inline_format(stripped[5:]) + "</h4>")
        elif stripped.startswith("### "):
            html.append("<h3>" + inline_format(stripped[4:]) + "</h3>")
        elif stripped.startswith("## "):
            html.append("<h2>" + inline_format(stripped[3:]) + "</h2>")
        elif stripped.startswith("@@VERIFY:"):
            m = re.match(r"@@VERIFY:([^@]+)@@\s*(.*)", stripped)
            state = (m.group(1).strip() if m else "PARTIALLY VERIFIED").lower().replace(" ", "-")
            label = m.group(2).strip() if m else stripped
            html.append('<div class="verify-card verify-' + esc(state) + '">' + inline_format(label) + "</div>")
        elif stripped.startswith("- "):
            html.append('<div class="md-bullet">• ' + inline_format(stripped[2:]) + "</div>")
        elif re.match(r"^[0-9]+\.\s+", stripped):
            html.append('<div class="md-number">' + inline_format(stripped) + "</div>")
        elif stripped.startswith("> "):
            html.append("<blockquote>" + inline_format(stripped[2:]) + "</blockquote>")
        else:
            html.append("<p>" + inline_format(line) + "</p>")

    if in_code:
        html.append('<pre class="codeblock"><code>' + esc("\n".join(code_lines)) + "</code></pre>")

    return "\n".join(html)


def rendered_download_page(title, body_html):
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{esc(title)}</title>
<style>
body {{
  background:#080b10;
  color:#e8edf2;
  font-family:Arial,sans-serif;
  margin:0;
  padding:28px;
}}
.page {{
  max-width:1180px;
  margin:auto;
}}
.topbar {{
  margin-bottom:18px;
}}
.topbar a {{
  color:white;
  background:linear-gradient(90deg,#2563eb,#7c3aed);
  padding:9px 13px;
  border-radius:10px;
  text-decoration:none;
  font-weight:800;
  font-size:13px;
}}
.answer-rendered {{
  background:#050814;
  color:#dbeafe;
  border:1px solid #263241;
  border-radius:16px;
  padding:28px;
  line-height:1.7;
  font-size:16px;
}}
.answer-rendered h2 {{
  font-size:30px;
  margin:22px 0 12px;
  color:#ffffff;
}}
.answer-rendered h3 {{
  font-size:23px;
  margin:22px 0 12px;
  color:#dbeafe;
}}
.answer-rendered h4 {{
  font-size:19px;
  margin:20px 0 10px;
  color:#bfdbfe;
}}
.answer-rendered h2 + h3 {{
  background:#0f172a;
  border:1px solid #334155;
  border-left:5px solid #38bdf8;
  border-radius:12px;
  padding:14px 16px;
  margin-top:10px;
  color:#ffffff;
}}
.answer-rendered .md-bullet,
.answer-rendered .md-number {{
  margin:7px 0;
}}
.answer-rendered code {{
  background:#111827;
  color:#e5e7eb;
  padding:3px 7px;
  border-radius:6px;
}}
.answer-rendered .codeblock {{
  white-space:pre;
  overflow-x:auto;
  background:#020617;
  color:#dbeafe;
  border:1px solid #475569;
  border-left:5px solid #38bdf8;
  border-radius:14px;
  padding:18px;
  margin:16px 0;
  font-family:Consolas, Monaco, monospace;
  font-size:15px;
  line-height:1.6;
}}
.answer-rendered .codeblock code {{
  background:transparent;
  padding:0;
  color:#dbeafe;
}}

.answer-rendered .verify-card {{
  border-radius:14px;
  padding:14px 16px;
  margin:14px 0;
  font-weight:900;
  letter-spacing:.2px;
}}
.answer-rendered .verify-verified {{
  background:#052e1a;
  border:1px solid #16a34a;
  color:#bbf7d0;
}}
.answer-rendered .verify-partially-verified {{
  background:#3a2a05;
  border:1px solid #f59e0b;
  color:#fde68a;
}}
.answer-rendered .verify-not-verified {{
  background:#3a0a0a;
  border:1px solid #ef4444;
  color:#fecaca;
}}
.session-item {{
  margin-bottom:26px;
}}
.session-meta {{
  color:#9aa8b5;
  margin-bottom:10px;
  font-size:13px;
}}
{COPY_CODE_CSS}
</style>
</head>
<body>
<div class="page">
  <div class="topbar"><a href="/">Back to ZimaBrain</a></div>
  {body_html}
</div>
{COPY_CODE_JS}
</body>
</html>"""
