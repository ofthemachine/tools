#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Render a compiled tools catalog (archived) into a static website: the catalog itself served verbatim -- llms.txt, manifest.json, every pack's SKILL.md and every tool file at the same paths -- plus an HTML layer over it: an explorer of every tool with search, tag and pack filters, grid and table views and a dark/light theme; one page per pack; one page per tool with its contract, provenance, a curl one-liner and its full source. Relative links throughout, so the result works from a file:// URL as well as a web root.
#: when=Use when the user wants the browsable website for a tools catalog, or CI publishes tools.ofthemachine.com from a freshly built catalog.
#: network=none
#: stdin=none
#: param=archive:required:file:d=catalog.tar.gz as meta/compile-catalog.py emits it (the site root is the catalog root)
#: param=host:default=tools.ofthemachine.com:d=Canonical host (served over https), used in curl one-liners, canonical links, and the CNAME file
#: output=site.tar.gz
"""
The site is a pure function of the catalog tarball. manifest.json holds every fact a page shows;
the tool files beside it supply the source listings. Nothing is derived here that the compiler
did not already write down, and nothing in the catalog is altered: the HTML is written beside it.
"""

import html
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List

SRC = Path(tempfile.mkdtemp(prefix="site-src-"))
OUT = Path(tempfile.mkdtemp(prefix="site-out-"))
RESULT = Path("/output/site.tar.gz")
REPO = "https://github.com/ofthemachine/tools"

e = html.escape


# ----------------------------------------------------------------------------- assets

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
:root,[data-theme=dark]{--bg:#0a0a12;--bg2:#121220;--surface:#1a1a2e;--surface2:#252542;--fg:#f0f0f5;--fg2:#a0a0b8;--muted:#8c8cab;--accent:#00ff88;--accent2:#00b4d8;--on-accent:#000;--border:#282840;--code:#0d0d1a;--stripe:#0f0f1c;--warn:#ffb703}
[data-theme=light]{--bg:#f8f9fa;--bg2:#fff;--surface:#f1f3f5;--surface2:#e9ecef;--fg:#12141d;--fg2:#495057;--muted:#5c636a;--accent:#047857;--accent2:#0369a1;--on-accent:#fff;--border:#dee2e6;--code:#f1f5f9;--stripe:#f8fafc;--warn:#b45309}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--fg);line-height:1.6;-webkit-font-smoothing:antialiased}
code,pre,.mono{font-family:'JetBrains Mono',monospace}
a{color:var(--accent2);text-decoration:none}a:hover{text-decoration:underline}
.container{max-width:1200px;margin:0 auto;padding:0 1.5rem}
.site-header{border-bottom:1px solid var(--border);background:var(--bg2);position:sticky;top:0;z-index:10}
.header-inner{display:flex;justify-content:space-between;align-items:center;height:56px}
.brand{font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--fg);letter-spacing:.02em}.brand span{color:var(--accent)}
.nav{display:flex;gap:1.25rem;align-items:center;font-size:.9rem}
.theme-toggle{background:var(--surface);border:1px solid var(--border);color:var(--fg);border-radius:6px;padding:.3rem .6rem;cursor:pointer;font-family:'JetBrains Mono',monospace}
main{padding:2rem 0 4rem}
.hero{text-align:center;padding:1.5rem 0 2rem}
.hero h1{font-family:'JetBrains Mono',monospace;font-size:2.4rem;letter-spacing:-.02em;margin-bottom:.4rem}
.hero p{color:var(--fg2);max-width:680px;margin:0 auto;font-size:1.05rem}
.hero .hero-note{font-size:.9rem;color:var(--muted);margin-top:.75rem;max-width:760px}
.controls{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:1.25rem;display:flex;flex-direction:column;gap:1rem;margin-bottom:1.5rem}
.search{display:flex;gap:.75rem;align-items:center}
.search input{flex:1;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:.7rem 1rem;color:var(--fg);font-size:.95rem;font-family:'JetBrains Mono',monospace}
.search input:focus{border-color:var(--accent)}
:is(a,button,input,select,summary):focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.btn.primary{background:var(--accent);color:var(--on-accent);border-color:var(--accent);font-weight:600}
.actions{display:flex;gap:.6rem;justify-content:center;flex-wrap:wrap;margin-top:1rem}
.btn{background:transparent;border:1px solid var(--border);color:var(--fg2);border-radius:6px;padding:.45rem .8rem;font-size:.8rem;font-family:'JetBrains Mono',monospace;cursor:pointer}
.row{display:flex;flex-wrap:wrap;gap:.75rem;align-items:center;justify-content:space-between}
.group{display:flex;flex-wrap:wrap;gap:.75rem;align-items:center}
.label{font-size:.72rem;color:var(--muted);font-family:'JetBrains Mono',monospace;letter-spacing:.05em}
.pills{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center}
.pill{background:var(--surface);color:var(--fg2);border:1px solid var(--border);padding:.28rem .7rem;border-radius:20px;font-size:.76rem;font-family:'JetBrains Mono',monospace;cursor:pointer;font-weight:600;white-space:nowrap}
.pill.active{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
select{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.4rem .8rem;color:var(--fg);font-family:'JetBrains Mono',monospace;font-size:.85rem;cursor:pointer}
.view{display:inline-flex;border:1px solid var(--border);border-radius:8px;overflow:hidden;background:var(--surface)}
.view button{background:transparent;color:var(--fg2);border:none;padding:.45rem .85rem;font-size:.85rem;font-family:'JetBrains Mono',monospace;font-weight:600;cursor:pointer}
.view button.active{background:var(--accent);color:var(--on-accent)}
.summary{display:flex;justify-content:space-between;font-size:.86rem;color:var(--muted);margin-bottom:1.25rem;flex-wrap:wrap;gap:.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1.25rem}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:1.2rem;display:flex;flex-direction:column;min-width:0;transition:border-color .15s,transform .15s}
.card:hover{border-color:var(--accent);transform:translateY(-2px)}
.card h3{font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:600;word-break:break-word;margin-bottom:.35rem}
.card h3 a{color:var(--fg)}.card h3 .pack{color:var(--muted);font-weight:400}
.badges{display:flex;gap:.4rem;flex-wrap:wrap;margin:.35rem 0 .8rem}
.badge{font-family:'JetBrains Mono',monospace;font-size:.7rem;font-weight:600;padding:.15rem .5rem;border-radius:4px;border:1px solid var(--border);color:var(--fg2);background:var(--surface)}
.badge.tag{color:var(--accent2);border-color:var(--accent2)}
.badge.net{color:var(--warn);border-color:var(--warn)}
.badge.hermetic{color:var(--accent);border-color:var(--accent)}
.desc{color:var(--fg2);font-size:.88rem;flex:1;margin-bottom:.9rem}
.grid .desc{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card{position:relative}.card h3 a::after{content:'';position:absolute;inset:0}.card .badges,.card .foot{position:relative;z-index:1}
.packs{margin-bottom:1.5rem}.packs .pill{text-decoration:none}
.foot{border-top:1px solid var(--border);padding-top:.7rem;display:flex;justify-content:space-between;font-size:.78rem;color:var(--muted);font-family:'JetBrains Mono',monospace}
table{width:100%;border-collapse:collapse;font-size:.86rem}
th,td{text-align:left;padding:.55rem .7rem;border-bottom:1px solid var(--border);vertical-align:top}
th{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--muted);letter-spacing:.05em}
tbody tr:nth-child(odd){background:var(--stripe)}tbody tr:hover{background:var(--surface2)}
td.mono a{color:var(--fg)}
.hidden{display:none!important}
.crumbs{font-family:'JetBrains Mono',monospace;font-size:.85rem;color:var(--muted);margin-bottom:1rem}.crumbs a{color:var(--fg2)}
.page h1{font-family:'JetBrains Mono',monospace;font-size:2rem;letter-spacing:-.02em;word-break:break-word}
.page h2{font-family:'JetBrains Mono',monospace;font-size:1.1rem;margin:2rem 0 .75rem;color:var(--fg)}
.lead{color:var(--fg2);font-size:1.05rem;max-width:820px;margin:.5rem 0 1rem}
.when{color:var(--fg2);font-style:italic;max-width:820px}
pre{background:var(--code);border:1px solid var(--border);border-radius:8px;padding:1rem;overflow-x:auto;font-size:.84rem;line-height:1.5}
.copy{position:relative}.copy .btn{position:absolute;top:.5rem;right:.5rem}.copy pre{padding-right:4.5rem}
details summary{cursor:pointer;font-family:'JetBrains Mono',monospace;color:var(--fg2);margin-bottom:.5rem}
#table{overflow-x:auto}
dl{display:grid;grid-template-columns:max-content 1fr;gap:.4rem 1.25rem;font-size:.9rem}dt{font-family:'JetBrains Mono',monospace;color:var(--muted)}dd{word-break:break-all}
.links{display:flex;gap:1rem;flex-wrap:wrap;font-size:.9rem;margin:.75rem 0 1.5rem}
dl.links{display:grid;grid-template-columns:max-content 1fr;gap:.3rem 1rem}dl.links dt{font-family:'JetBrains Mono',monospace;color:var(--muted);font-size:.8rem;padding-top:.1rem}dl.links dd{margin:0}
.step{color:var(--fg2);font-size:.92rem;margin:.9rem 0 .4rem}
footer{border-top:1px solid var(--border);color:var(--muted);font-size:.8rem;padding:1.5rem 0;text-align:center}
@media (max-width:640px){.hero h1{font-size:1.7rem}.grid{grid-template-columns:1fr}.header-inner{height:auto;padding:.6rem 0;flex-wrap:wrap;gap:.5rem}#table th:nth-child(3),#table td:nth-child(3),#table th:nth-child(5),#table td:nth-child(5){display:none}}
"""

# One pass over the inline JSON: every control is a filter over the same array, and a card or
# row is shown when every active filter accepts its tool. No pagination -- hide, don't rebuild.
JS = """
(function(){
  var data=JSON.parse(document.getElementById('data').textContent);
  var tools=data.tools, state={q:'',tag:'all',pack:'all',sort:'name',view:'grid'};
  var q=document.getElementById('q'), pack=document.getElementById('pack'), sort=document.getElementById('sort');
  var cards={}, rows={};
  tools.forEach(function(t){cards[t.path]=document.getElementById('card-'+t.path.replace(/[\\/.]/g,'-'));rows[t.path]=document.getElementById('row-'+t.path.replace(/[\\/.]/g,'-'));});
  function accepts(t){
    if(state.tag!=='all'&&t.tags.indexOf(state.tag)<0)return false;
    if(state.pack!=='all'&&t.pack!==state.pack)return false;
    if(!state.q)return true;
    return (t.path+' '+t.description+' '+t.when+' '+t.tags.join(' ')+' '+t.image).toLowerCase().indexOf(state.q)>=0;
  }
  function order(a,b){
    if(state.sort==='pack')return (a.pack+a.stem).localeCompare(b.pack+b.stem);
    if(state.sort==='reach')return a.network.localeCompare(b.network)||a.path.localeCompare(b.path);
    return a.path.localeCompare(b.path);
  }
  function render(){
    var shown=tools.filter(accepts).sort(order), grid=document.getElementById('grid'), tbody=document.getElementById('rows');
    tools.forEach(function(t){cards[t.path].classList.add('hidden');rows[t.path].classList.add('hidden');});
    shown.forEach(function(t){cards[t.path].classList.remove('hidden');rows[t.path].classList.remove('hidden');grid.appendChild(cards[t.path]);tbody.appendChild(rows[t.path]);});
    document.getElementById('count').textContent=shown.length+' of '+tools.length+' tools';
    document.getElementById('grid').classList.toggle('hidden',state.view!=='grid');
    document.getElementById('table').classList.toggle('hidden',state.view!=='table');
    document.querySelectorAll('.view button').forEach(function(b){b.classList.toggle('active',b.dataset.view===state.view);});
    document.querySelectorAll('.pill[data-tag]').forEach(function(p){p.classList.toggle('active',p.dataset.tag===state.tag);});
    document.getElementById('reset').classList.toggle('hidden',!(state.q||state.tag!=='all'||state.pack!=='all'));
    document.getElementById('empty').classList.toggle('hidden',shown.length>0);
    document.querySelectorAll('.pill[data-tag],.view button').forEach(function(b){b.setAttribute('aria-pressed',b.classList.contains('active'));});
  }
  q.addEventListener('input',function(){state.q=q.value.trim().toLowerCase();render();});
  pack.addEventListener('change',function(){state.pack=pack.value;render();});
  sort.addEventListener('change',function(){state.sort=sort.value;render();});
  document.querySelectorAll('.pill[data-tag]').forEach(function(p){p.addEventListener('click',function(){state.tag=p.dataset.tag;render();});});
  document.querySelectorAll('.view button').forEach(function(b){b.addEventListener('click',function(){state.view=b.dataset.view;try{localStorage.setItem('tools-view',state.view);}catch(e){}render();});});
  function reset(){state.q='';state.tag='all';state.pack='all';q.value='';pack.value='all';render();}
  document.getElementById('reset').addEventListener('click',reset);document.getElementById('reset2').addEventListener('click',reset);
  try{state.view=localStorage.getItem('tools-view')||'grid';}catch(e){}
  render();
})();
"""

THEME_JS = """
(function(){try{var t=localStorage.getItem('tools-theme')||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark');document.documentElement.setAttribute('data-theme',t);}catch(e){}})();
function toggleTheme(){var h=document.documentElement,n=h.getAttribute('data-theme')==='dark'?'light':'dark';h.setAttribute('data-theme',n);try{localStorage.setItem('tools-theme',n);}catch(e){}}
// Viewed from anywhere but the canonical host (a local build, a preview), the copyable commands
// should point at where you actually are. The HTML itself stays canonical for agents and curl.
addEventListener('DOMContentLoaded',function(){var b=document.documentElement.dataset.base;if(!b||!/^https?:/.test(location.protocol)||location.origin===b)return;document.querySelectorAll('pre').forEach(function(p){p.textContent=p.textContent.split(b).join(location.origin);});});
function copyText(id,btn){var t=document.getElementById(id).textContent;navigator.clipboard&&navigator.clipboard.writeText(t).then(function(){btn.textContent='copied';setTimeout(function(){btn.textContent='copy';},1200);});}
"""


# ----------------------------------------------------------------------------- layout

def layout(title: str, body: str, depth: int, catalog: Dict[str, Any], canonical: str, alternate_md: str = "") -> str:
    root = "../" * depth
    base = catalog["base_url"]
    alt = f'<link rel="alternate" type="text/markdown" href="{e(alternate_md)}">' if alternate_md else ""
    return f"""<!doctype html>
<html lang="en" data-base="{e(base)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · {e(catalog['title'])}</title>
<meta name="description" content="{e(catalog['description'])}">
<link rel="canonical" href="{e(canonical)}">
{alt}
<link rel="stylesheet" href="{root}assets/site.css">
<script>{THEME_JS}</script>
</head>
<body>
<header class="site-header"><div class="container header-inner">
<a class="brand" href="{root}index.html"><span>&gt;_</span> TOOLS OFTHEMACHINE</a>
<nav class="nav"><a href="{root}llms.txt">llms.txt</a><a href="{REPO}" target="_blank" rel="noopener">GitHub ↗</a><button class="theme-toggle" type="button" onclick="toggleTheme()" aria-label="Toggle theme">◐</button></nav>
</div></header>
<main><div class="container">
{body}
</div></main>
<footer><div class="container">{e(catalog['title'])} v{e(catalog['version'])} · generated {e(catalog['generated']['at'])} by <code>meta/site.py</code> from <code>meta/compile-catalog.py</code> · <a href="{root}llms.txt">llms.txt</a> · <a href="{root}manifest.json">manifest.json</a> · <a href="{root}okf/index.md">OKF</a></div></footer>
</body>
</html>
"""


def short_image(image: str) -> str:
    return image.split("@")[0].split(":")[0].split("/")[-1]


def badge_html(tool: Dict[str, Any], pack: Dict[str, Any], root: str, with_pack: bool = True, with_tags: bool = True) -> str:
    parts = []
    if with_pack:
        parts.append(f'<a class="badge" href="{root}{e(pack["name"])}/index.html">{e(pack["name"])}</a>')
    if with_tags:
        parts += [f'<span class="badge tag">{e(t)}</span>' for t in pack["tags"]]
    reach = "hermetic" if tool["network"] == "none" else "net"
    parts.append(f'<span class="badge {reach}">{"○ hermetic" if reach == "hermetic" else "● network"}</span>')
    parts.append(f'<span class="badge">{e(short_image(tool["image"]))}</span>')
    return f'<div class="badges">{"".join(parts)}</div>'


def dom_id(prefix: str, path: str) -> str:
    return prefix + "-" + path.replace("/", "-").replace(".", "-")


def card_html(tool: Dict[str, Any], pack: Dict[str, Any], root: str, in_pack: bool = False) -> str:
    """in_pack: the card sits on its own pack's page, where the pack and tags are the page header."""
    href = f"{root}{tool['pack']}/{tool['stem']}/index.html"
    n = len(tool["params"])
    prefix = "" if in_pack else f'<span class="pack">{e(tool["pack"])}/</span>'
    return f"""<article class="card" id="{dom_id('card', tool['path'])}">
<h3><a href="{e(href)}">{prefix}{e(tool['file'])}</a></h3>
{badge_html(tool, pack, root, with_pack=not in_pack, with_tags=not in_pack)}
<p class="desc">{e(tool['description'])}</p>
<div class="foot"><span>{n} param{'' if n == 1 else 's'}{' · ' + str(len(tool['outputs'])) + ' output' + ('' if len(tool['outputs']) == 1 else 's') if tool['outputs'] else ''}</span><a href="{e(href)}">details →</a></div>
</article>"""


def row_html(tool: Dict[str, Any], pack: Dict[str, Any], root: str) -> str:
    href = f"{root}{tool['pack']}/{tool['stem']}/index.html"
    reach = "○ hermetic" if tool["network"] == "none" else "● network"
    return (f'<tr id="{dom_id("row", tool["path"])}"><td class="mono"><a href="{e(href)}">{e(tool["path"])}</a></td>'
            f'<td><a href="{root}{e(pack["name"])}/index.html">{e(pack["name"])}</a></td><td>{e(", ".join(pack["tags"]))}</td>'
            f'<td class="mono">{reach}</td><td class="mono">{e(short_image(tool["image"]))}</td><td>{e(tool["description"])}</td></tr>')


# ----------------------------------------------------------------------------- pages

def page_index(m: Dict[str, Any], packs: Dict[str, Dict[str, Any]], base: str) -> str:
    tools = m["tools"]
    tag_counts: Dict[str, int] = {}
    for t in tools:
        for tag in packs[t["pack"]]["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    pills = f'<button class="pill active" data-tag="all" aria-pressed="true">all ({len(tools)})</button>' + "".join(
        f'<button class="pill" data-tag="{e(tag)}" title="{e(m["tags"][tag])}">{e(tag)} ({n})</button>' for tag, n in sorted(tag_counts.items()))
    options = '<option value="all">all packs</option>' + "".join(
        f'<option value="{e(p["name"])}">{e(p["name"])} ({len(p["tools"])})</option>' for p in m["packs"])
    cards = "\n".join(card_html(t, packs[t["pack"]], "") for t in tools)
    rows = "\n".join(row_html(t, packs[t["pack"]], "") for t in tools)
    data = json.dumps([{"path": t["path"], "pack": t["pack"], "stem": t["stem"], "description": t["description"], "when": t["when"],
                        "tags": packs[t["pack"]]["tags"], "network": t["network"], "image": short_image(t["image"])} for t in tools])
    data = data.replace("</", "<\\/")  # a "</script>" inside the JSON must not end the script element
    body = f"""<section class="hero">
<h1>{e(m['title'])}</h1>
<p>{len(tools)} tools in {len(m['packs'])} packs. Each is one file that runs in a pinned container via <code>fragletc</code>; each pack is one Agent Skill. Agents start at <a href="llms.txt">llms.txt</a>.</p>
<p class="hero-note">Written in any language with a fraglet-enabled container: the 90+ <a href="https://github.com/ofthemachine/100hellos" target="_blank" rel="noopener">100hellos</a> languages or the purpose-built <a href="https://github.com/ofthemachine/containers" target="_blank" rel="noopener">ofthemachine</a> images (python3, headless-browser, latex, meme, home-automation, 3d-printing…). Two host dependencies: <a href="https://github.com/ofthemachine/fraglet" target="_blank" rel="noopener">fragletc</a> and Docker.</p>
<div class="actions"><a class="btn primary" href="#packs">Browse {len(m['packs'])} packs</a><a class="btn" href="llms.txt">I'm an agent → llms.txt</a><a class="btn" href="catalog.tar.gz">Download catalog.tar.gz</a></div>
</section>
<p class="hero-note">Claude Code, from a clone: <code>make build &amp;&amp; claude plugin marketplace add "$PWD/catalog"</code>, then <code>claude plugin install &lt;pack&gt;@ofthemachine-tools</code>.</p>
<nav id="packs" class="pills packs" aria-label="Packs"><span class="label">PACKS</span>{"".join(f'<a class="pill" href="{e(p["name"])}/index.html">{e(p["name"])} ({len(p["tools"])})</a>' for p in m["packs"])}</nav>
<section class="controls">
<div class="search"><input id="q" type="search" placeholder="search tools, packs, descriptions…" autocomplete="off" aria-label="Search tools"><button id="reset" class="btn hidden" type="button">reset</button></div>
<div class="pills"><span class="label">TAG</span>{pills}</div>
<div class="row"><div class="group"><label class="label" for="pack">PACK</label><select id="pack">{options}</select><label class="label" for="sort">SORT</label><select id="sort"><option value="name">name</option><option value="pack">pack</option><option value="reach">reach</option></select></div>
<div class="view"><button type="button" data-view="grid" class="active" aria-pressed="true">⊞ grid</button><button type="button" data-view="table" aria-pressed="false">☰ table</button></div></div>
</section>
<div class="summary"><span id="count" aria-live="polite">{len(tools)} of {len(tools)} tools</span><span>every tool: <code>curl -fsSLO {e(base)}/&lt;pack&gt;/&lt;tool&gt;</code></span></div>
<div id="grid" class="grid">
{cards}
</div>
<div id="table" class="hidden"><table><thead><tr><th>tool</th><th>pack</th><th>tags</th><th>reach</th><th>image</th><th>description</th></tr></thead><tbody id="rows">
{rows}
</tbody></table></div>
<p id="empty" class="summary hidden">No tools match. <button id="reset2" class="btn" type="button">reset filters</button></p>
<script id="data" type="application/json">{data}</script>
<script src="assets/site.js"></script>"""
    return layout("Explore", body, 0, m, f"{base}/")


def page_pack(p: Dict[str, Any], tools: List[Dict[str, Any]], m: Dict[str, Any], base: str) -> str:
    cards = "\n".join(card_html(t, p, "../", in_pack=True) for t in tools)
    tags = "".join(f'<span class="badge tag">{e(t)}</span>' for t in p["tags"])
    body = f"""<div class="page">
<div class="crumbs"><a href="../index.html">tools</a> / {e(p['name'])}</div>
<h1>{e(p['title'])}</h1>
<div class="badges">{tags}<span class="badge">{len(tools)} tool{'' if len(tools) == 1 else 's'}</span></div>
<p class="lead">{e(p['description'])}</p>
<div class="links"><a href="SKILL.md">SKILL.md</a><a href="../okf/{e(p['name'])}/index.md">OKF</a><a href="{REPO}/tree/main/{e(p['name'])}" target="_blank" rel="noopener">source ↗</a></div>
<h2>Tools</h2>
<div class="grid">
{cards}
</div>
<h2>Get it</h2>
<p class="desc">This directory is the skill — <a href="SKILL.md">SKILL.md</a> lists the tools and the tools sit beside it. As one file, into any Agent Skills directory:</p>
<div class="copy"><pre id="get">curl -fsSL {e(base)}/{e(p['name'])}.tar.gz | tar xz -C ~/.claude/skills</pre><button class="btn" type="button" onclick="copyText('get',this)">copy</button></div>
</div>"""
    return layout(p["title"], body, 1, m, f"{base}/{p['name']}/", alternate_md="SKILL.md")


def page_tool(t: Dict[str, Any], p: Dict[str, Any], m: Dict[str, Any], base: str, source: str) -> str:
    url = f"{base}/{t['path']}"
    params = "".join(
        f'<tr><td class="mono">{e(x["name"])}</td><td class="mono">{e(x["type"])}</td>'
        f'<td class="mono">{"required" if x["required"] else ("default <code>" + e(str(x["default"])) + "</code>" if x.get("default") is not None else "optional")}</td>'
        f'<td>{e(x.get("description") or "")}</td></tr>' for x in t["params"]) or '<tr><td colspan="4">none</td></tr>'
    if t["stdin"] == "buffer":
        params += '<tr><td class="mono">stdin</td><td class="mono">pipe</td><td class="mono">optional</td><td>read in full and hashed into the receipt</td></tr>'
    elif t["stdin"] == "stream":
        params += '<tr><td class="mono">stdin</td><td class="mono">stream</td><td class="mono">interactive</td><td>passed through live; the run has no memo key</td></tr>'
    outputs = ", ".join(f"<code>{e(o)}</code>" for o in t["outputs"]) or "stdout"
    reach = ("<code>network=none</code> — a run is a pure function of its inputs; results are safe to memoize."
             if t["network"] == "none" else "<code>network=required</code> — output depends on live external state; do not cache indefinitely.")
    body = f"""<div class="page">
<div class="crumbs"><a href="../../index.html">tools</a> / <a href="../index.html">{e(p['name'])}</a> / {e(t['file'])}</div>
<h1>{e(t['path'])}</h1>
{badge_html(t, p, "../../")}
<p class="lead">{e(t['description'])}</p>
<p class="when">{e(t['when'])}</p>
<dl class="links"><dt>the file</dt><dd><a href="../{e(t['file'])}">{e(t['path'])}</a></dd><dt>its skill</dt><dd><a href="../SKILL.md">{e(p['name'])}/SKILL.md</a> (the whole <a href="../index.html">{e(p['name'])}</a> pack)</dd><dt>as knowledge</dt><dd><a href="../../okf/{e(p['name'])}/{e(t['stem'])}.md">okf/{e(p['name'])}/{e(t['stem'])}.md</a></dd><dt>on GitHub</dt><dd><a href="{REPO}/blob/main/{e(t['path'])}" target="_blank" rel="noopener">{e(t['path'])} ↗</a></dd></dl>
<h2>Run it</h2>
<p class="step">1. Once per machine: install <a href="https://github.com/ofthemachine/fraglet" target="_blank" rel="noopener">fragletc</a> (Docker must already be running).</p>
<div class="copy"><pre id="install">curl -fsSL https://raw.githubusercontent.com/ofthemachine/fraglet/main/install.sh | sh</pre><button class="btn" type="button" onclick="copyText('install',this)">copy</button></div>
<p class="step">2. Fetch the tool and print its contract.</p>
<div class="copy"><pre id="curl">curl -fsSLO {e(url)} &amp;&amp; chmod +x {e(t['file'])} &amp;&amp; ./{e(t['file'])} --fraglet-help</pre><button class="btn" type="button" onclick="copyText('curl',this)">copy</button></div>
<p class="step">3. Run it.</p>
<div class="copy"><pre id="usage">./{e(t['usage'])}</pre><button class="btn" type="button" onclick="copyText('usage',this)">copy</button></div>
<h2>Parameters</h2>
<table><thead><tr><th>name</th><th>type</th><th>requirement</th><th>description</th></tr></thead><tbody>{params}</tbody></table>
<h2>Outputs</h2>
<p class="desc">{outputs}</p>
<h2>Provenance</h2>
<dl>
<dt>image</dt><dd class="mono">{e(t['image'])}</dd>
<dt>reach</dt><dd>{reach}</dd>
<dt>procedure_hash</dt><dd class="mono">{e(t['procedure_hash'])}</dd>
<dt>receipt</dt><dd>add <code>--receipt run.json</code> to any run; <code>meta/attest-receipt.py</code> verifies it against this hash without re-running.</dd>
</dl>
<h2>Source</h2>
<details open><summary>{e(t['file'])} · {len(source.splitlines())} lines · sha256 {e(t['procedure_hash'][7:19])}…</summary>
<div class="copy"><pre id="src">{e(source)}</pre><button class="btn" type="button" onclick="copyText('src',this)">copy</button></div></details>
</div>"""
    return layout(t["path"], body, 2, m, f"{base}/{t['pack']}/{t['stem']}/")


# ----------------------------------------------------------------------------- main

def unpack(archive: str, into: Path) -> Path:
    with tarfile.open(archive, "r:*") as tar:
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise SystemExit(f"unsafe archive member {member.name!r}")
            if not os.path.basename(member.name).startswith("._"):
                tar.extract(member, into)
    entries = [p for p in into.iterdir() if not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir() and not (into / "manifest.json").exists():
        return entries[0]
    return into


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    host = os.environ["HOST"].strip().strip("/")
    base = f"https://{host}"
    catalog = unpack(os.environ["ARCHIVE"], SRC)
    manifest_path = catalog / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("the archive has no manifest.json; give this tool what meta/compile-catalog.py emits")
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    packs = {p["name"]: p for p in m["packs"]}
    by_pack: Dict[str, List[Dict[str, Any]]] = {}
    for t in m["tools"]:
        by_pack.setdefault(t["pack"], []).append(t)

    # The catalog first, untouched; the HTML layer goes beside it.
    shutil.copytree(catalog, OUT, dirs_exist_ok=True)
    write(OUT / "assets" / "site.css", CSS.strip() + "\n")
    write(OUT / "assets" / "site.js", JS.strip() + "\n")
    write(OUT / "CNAME", host + "\n")
    shutil.copy2(os.environ["ARCHIVE"], OUT / "catalog.tar.gz")  # the whole catalog, fetchable as one file
    write(OUT / "index.html", page_index(m, packs, base))
    for p in m["packs"]:
        write(OUT / p["name"] / "index.html", page_pack(p, by_pack.get(p["name"], []), m, base))
        for t in by_pack.get(p["name"], []):
            source = (catalog / t["path"]).read_text(encoding="utf-8")
            write(OUT / t["pack"] / t["stem"] / "index.html", page_tool(t, p, m, base, source))

    RESULT.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(RESULT, "w:gz") as tar:
        for entry in sorted(OUT.iterdir()):
            tar.add(entry, arcname=entry.name)
    print(f"site for {base}: {len(m['packs'])} pack pages, {len(m['tools'])} tool pages, catalog served verbatim")


if __name__ == "__main__":
    main()
