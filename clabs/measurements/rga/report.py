"""
report.py
---------
Interactive HTML report for a single RGAMeasurement.

Linked views:
  - 2-D pressure map  (time × m/z, viridis, log scale)
  - Time trace        (pressure vs time for the m/z under the cursor)

Hovering over the 2-D map updates the time trace in real time.
Clicking the map locks the selection; clicking again unlocks.
When background_correct() has been called the time trace also shows the
raw signal and shades the background windows used for the fit.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def generate_rga_report(
    rga,
    output_path: str | Path = "rga_report.html",
    title:       str | None = None,
    log:         bool       = True,
) -> Path:
    """
    Generate a self-contained interactive HTML report for an RGAMeasurement.

    Parameters
    ----------
    rga         : RGAMeasurement
    output_path : destination .html file path
    title       : page title; defaults to rga.sample_name
    log         : log-scale colour for the 2-D map (default True)

    Returns
    -------
    Path to the saved HTML file.
    """
    try:
        from plotly.offline import get_plotlyjs
    except ImportError:
        raise ImportError("plotly is required: pip install plotly")

    title  = title or getattr(rga, "sample_name", None) or "RGA Measurement"
    has_bg = hasattr(rga, "_raw_pressure")

    mz   = rga.mz.astype(int).tolist()
    time = rga.time.tolist()
    pres = rga.pressure           # (T, M)

    # pres_by_mz[i] = pressure time trace for mz[i]
    pres_by_mz: list = pres.T.tolist()
    praw_by_mz: list | None = rga._raw_pressure.T.tolist() if has_bg else None

    # vmin for log clipping
    pos  = pres[pres > 0]
    vmin = float(pos.min()) if pos.size else 1e-14

    # shutter / BG window times
    open_t  = float(rga.open_time)  if hasattr(rga, "open_time")  else None
    close_t = float(rga.close_time) if hasattr(rga, "close_time") else None
    bg1     = list(map(float, rga._bg_off1)) if hasattr(rga, "_bg_off1") else None
    bg2     = list(map(float, rga._bg_off2)) if hasattr(rga, "_bg_off2") else None

    # scan metadata badges
    scan_meta = getattr(rga, "scan_settings", {}) or {}
    badges = []
    x_val = getattr(rga, "x", None)
    y_val = getattr(rga, "y", None)
    if x_val is not None and y_val is not None:
        badges.append(f"x = {x_val:.2f} mm, y = {y_val:.2f} mm")
    if scan_meta.get("finalmass"):
        badges.append(f"max m/z {int(scan_meta['finalmass'])}")
    if scan_meta.get("scanspeed"):
        badges.append(f"speed {scan_meta['scanspeed']} Da/s")
    pd_val = getattr(rga, "pd", None)
    if pd_val is not None:
        badges.append(f"PD {pd_val:.2f} µA")
    if has_bg:
        badges.append("background corrected")

    badges_html = "".join(
        f'<span class="meta-badge">{b}</span>'
        for b in badges
    )

    payload = json.dumps({
        "mz":     mz,
        "time":   time,
        "pres":   pres_by_mz,
        "praw":   praw_by_mz,
        "log":    log,
        "vmin":   vmin,
        "open_t": open_t,
        "close_t": close_t,
        "bg1":    bg1,
        "bg2":    bg2,
    })

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script>{get_plotlyjs()}</script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, Helvetica, sans-serif; background: #f5f5f5;
            margin: 0; padding: 24px; color: #222; }}
    .page-wrap {{ max-width: 1200px; margin: 0 auto; }}
    .header-card {{ background: #fff; border-radius: 10px;
                    box-shadow: 0 2px 8px rgba(0,0,0,.12);
                    padding: 26px 32px 20px; margin-bottom: 24px; text-align: center; }}
    .header-card h1 {{ margin: 0 0 4px; font-size: 1.7em; color: #1a1a1a; }}
    .meta-badge {{ background: #eef2fb; border-radius: 20px; padding: 3px 12px;
                   font-size: 0.8em; color: #555; }}
    .meta-row {{ display: flex; flex-wrap: wrap; justify-content: center;
                 gap: 8px; margin: 10px 0 0; }}
    .section {{ background: #fff; border-radius: 8px;
                box-shadow: 0 1px 4px rgba(0,0,0,.12);
                padding: 20px 24px; margin-bottom: 28px; }}
    .section h2 {{ margin: 0 0 14px; font-size: 1.1em; color: #444;
                   border-bottom: 1px solid #eee; padding-bottom: 8px; }}
    .trace-header {{ display: flex; align-items: baseline; gap: 12px; margin-bottom: 6px; }}
    .trace-header h2 {{ margin: 0; }}
    #mz-badge {{ font-size: 0.85em; color: #1f77b4; font-weight: bold; }}
    #lock-hint {{ font-size: 0.75em; color: #bbb; }}
  </style>
</head>
<body>
<div class="page-wrap">

  <div class="header-card">
    <h1>{title}</h1>
    <div class="meta-row">{badges_html}</div>
  </div>

  <div class="section">
    <h2>2-D Pressure Map — hover to select m/z &nbsp;·&nbsp; click to lock</h2>
    <div id="rga-heatmap" style="width:100%;height:650px;"></div>
  </div>

  <div class="section">
    <div class="trace-header">
      <h2>Time Trace</h2>
      <span id="mz-badge">—</span>
      <span id="lock-hint"></span>
    </div>
    <div id="rga-timetrace" style="width:100%;height:320px;"></div>
  </div>

</div>
<script>
(function() {{
  var D = {payload};

  // ── Helpers ──────────────────────────────────────────────────────────────
  var mzToIdx = {{}};
  D.mz.forEach(function(v, i) {{ mzToIdx[v] = i; }});

  function logClip(v) {{
    return Math.log10(Math.max(v, D.vmin));
  }}

  // ── Heatmap z (log or linear, MxT) ───────────────────────────────────────
  var zHeat = D.log
    ? D.pres.map(function(row) {{ return row.map(logClip); }})
    : D.pres;

  // Colorbar tick labels for log scale
  var cbTicks = {{}};
  if (D.log) {{
    var logMin = Math.log10(D.vmin);
    var flatMax = D.pres.reduce(function(mx, row) {{
      return Math.max(mx, Math.max.apply(null, row));
    }}, D.vmin);
    var logMax = Math.log10(Math.max(flatMax, D.vmin));
    var tickVals = [], tickText = [];
    for (var tv = Math.ceil(logMin); tv <= Math.floor(logMax); tv++) {{
      tickVals.push(tv);
      tickText.push('10<sup>' + tv + '</sup>');
    }}
    cbTicks = {{ tickvals: tickVals, ticktext: tickText }};
  }}

  // ── Shutter / BG shapes ───────────────────────────────────────────────────
  function shutterShapes(forHeatmap) {{
    var shapes = [];
    var lineKw = {{ color: 'red', width: 1.5, dash: 'dash' }};
    if (D.open_t !== null) {{
      shapes.push({{ type:'line', x0:D.open_t, x1:D.open_t,
                     y0:0, y1:1, yref:'paper', line:lineKw }});
    }}
    if (D.close_t !== null) {{
      shapes.push({{ type:'line', x0:D.close_t, x1:D.close_t,
                     y0:0, y1:1, yref:'paper', line:lineKw }});
    }}
    if (D.bg1) {{
      var bgColor = forHeatmap ? 'rgba(255,255,255,0.13)' : 'rgba(255,165,0,0.13)';
      shapes.push({{ type:'rect', x0:D.bg1[0], x1:D.bg1[1], y0:0, y1:1,
                     yref:'paper', fillcolor:bgColor, line:{{width:0}} }});
      shapes.push({{ type:'rect', x0:D.bg2[0], x1:D.bg2[1], y0:0, y1:1,
                     yref:'paper', fillcolor:bgColor, line:{{width:0}} }});
    }}
    return shapes;
  }}

  // ── Build heatmap ─────────────────────────────────────────────────────────
  var heatTrace = {{
    type: 'heatmap',
    x: D.time,
    y: D.mz,
    z: zHeat,
    colorscale: 'Viridis',
    showscale: true,
    zsmooth: false,
    hovertemplate: 'Time: %{{x:.1f}} s<br>m/z: %{{y}}<br>' +
      (D.log ? 'log\u2081\u2080(P): %{{z:.2f}}' : 'P: %{{z:.2e}} Torr') +
      '<extra></extra>',
    colorbar: Object.assign({{
      title: {{ text: 'Partial pressure [Torr]', side: 'right' }},
    }}, cbTicks),
  }};

  // Horizontal selection line on heatmap (updated on hover)
  var heatShapes = shutterShapes(true).concat([{{
    type: 'line', x0: D.time[0], x1: D.time[D.time.length-1],
    y0: D.mz[0], y1: D.mz[0],
    line: {{ color: 'rgba(255,80,80,0.7)', width: 1.5 }},
  }}]);
  var SEL_SHAPE_IDX = heatShapes.length - 1;  // index of the selection line

  Plotly.newPlot('rga-heatmap', [heatTrace], {{
    template: 'plotly_white',
    xaxis: {{ title: 'Time [s]', showspikes: true, spikemode: 'across',
               spikecolor: '#aaa', spikethickness: 1 }},
    yaxis: {{ title: 'm/z' }},
    margin: {{ l: 60, r: 80, t: 20, b: 50 }},
    height: 650,
    shapes: heatShapes,
  }}, {{ responsive: true }});

  // ── Build time-trace plot ────────────────────────────────────────────────
  var initIdx = Math.floor(D.mz.length / 2);
  var ttTraces = [{{
    type: 'scatter', mode: 'lines',
    x: D.time, y: D.pres[initIdx],
    name: 'Corrected',
    line: {{ color: 'steelblue', width: 1.8 }},
    hovertemplate: '%{{y:.3e}} Torr<extra>Corrected</extra>',
  }}];
  if (D.praw) {{
    ttTraces.push({{
      type: 'scatter', mode: 'lines',
      x: D.time, y: D.praw[initIdx],
      name: 'Raw',
      line: {{ color: 'steelblue', width: 1.2, dash: 'dot' }},
      opacity: 0.5,
      hovertemplate: '%{{y:.3e}} Torr<extra>Raw</extra>',
    }});
  }}

  Plotly.newPlot('rga-timetrace', ttTraces, {{
    template: 'plotly_white',
    xaxis: {{ title: 'Time [s]', showspikes: true, spikemode: 'across',
               spikecolor: '#aaa', spikethickness: 1 }},
    yaxis: {{ title: 'Partial pressure [Torr]', exponentformat: 'e' }},
    legend: {{ x: 1.01, y: 1, xanchor: 'left' }},
    hovermode: 'x unified',
    margin: {{ l: 80, r: 130, t: 10, b: 50 }},
    height: 320,
    shapes: shutterShapes(false),
  }}, {{ responsive: true }});

  // ── Interaction ──────────────────────────────────────────────────────────
  var locked    = false;
  var curMzIdx  = initIdx;
  var mzBadge   = document.getElementById('mz-badge');
  var lockHint  = document.getElementById('lock-hint');

  function setMzBadge(mzVal) {{
    mzBadge.textContent = 'm/z = ' + mzVal;
  }}
  setMzBadge(D.mz[initIdx]);

  function updateTrace(idx) {{
    if (idx === curMzIdx) return;
    curMzIdx = idx;
    var updates = D.praw
      ? {{ y: [D.pres[idx], D.praw[idx]] }}
      : {{ y: [D.pres[idx]] }};
    var idxs = D.praw ? [0, 1] : [0];
    Plotly.restyle('rga-timetrace', updates, idxs);

    // Update selection line on heatmap
    var newShapes = shutterShapes(true);
    newShapes.push({{
      type: 'line', x0: D.time[0], x1: D.time[D.time.length-1],
      y0: D.mz[idx], y1: D.mz[idx],
      line: {{ color: 'rgba(255,80,80,0.7)', width: 1.5 }},
    }});
    Plotly.relayout('rga-heatmap', {{ shapes: newShapes }});
    setMzBadge(D.mz[idx]);
  }}

  document.getElementById('rga-heatmap').on('plotly_hover', function(data) {{
    if (locked) return;
    var idx = mzToIdx[data.points[0].y];
    if (idx !== undefined) updateTrace(idx);
  }});

  document.getElementById('rga-heatmap').on('plotly_click', function(data) {{
    var idx = mzToIdx[data.points[0].y];
    if (idx === undefined) return;
    if (locked && idx === curMzIdx) {{
      locked = false;
      lockHint.textContent = '';
    }} else {{
      locked = true;
      lockHint.textContent = '(locked — click same m/z to release)';
      updateTrace(idx);
    }}
  }});

}})();
</script>
</body>
</html>"""

    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page)
    print(f"RGA report saved → {dest.resolve()}")
    return dest
