import asyncio
import os
import shutil
from playwright.async_api import async_playwright

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

  @page {
    size: A4 portrait;
    margin: 1.2cm 1.4cm 1.2cm 1.4cm;
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 8pt;
      color: #64748b;
    }
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  body {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #0f172a;
    background: #ffffff;
    line-height: 1.45;
    font-size: 9.5pt;
  }

  .header-card {
    border: 1.5px solid #0070ba;
    border-radius: 8px;
    padding: 16px 20px;
    background: linear-gradient(135deg, #f0f7ff 0%, #e0effe 100%);
    margin-bottom: 18px;
  }

  .title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }

  h1 {
    font-size: 19pt;
    font-weight: 800;
    color: #003087;
    letter-spacing: -0.02em;
  }

  .badges {
    display: flex;
    gap: 8px;
  }

  .badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .badge-paypal {
    background: #0070ba;
    color: #ffffff;
  }

  .badge-grid {
    background: #00a86b;
    color: #ffffff;
  }

  .badge-time {
    background: #475569;
    color: #ffffff;
  }

  .subtitle {
    font-size: 10.5pt;
    color: #334155;
    font-weight: 600;
    margin-bottom: 6px;
  }

  .meta-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    padding-top: 8px;
    border-top: 1px solid rgba(0, 112, 186, 0.2);
    font-size: 8pt;
    color: #475569;
  }

  .meta-grid strong {
    color: #0f172a;
  }

  .section-title {
    font-size: 12pt;
    font-weight: 800;
    color: #003087;
    border-bottom: 2px solid #0070ba;
    padding-bottom: 4px;
    margin: 16px 0 10px 0;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  .section-title span {
    font-size: 8.5pt;
    font-weight: 600;
    color: #64748b;
  }

  table.timeline-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 14px;
    font-size: 8.5pt;
  }

  table.timeline-table th {
    background: #003087;
    color: #ffffff;
    font-weight: 700;
    text-align: left;
    padding: 7px 10px;
    font-size: 8pt;
    letter-spacing: 0.03em;
  }

  table.timeline-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
  }

  table.timeline-table tr:nth-child(even) td {
    background: #f8fafc;
  }

  .time-col {
    width: 13%;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    color: #0070ba;
    font-size: 8pt;
    white-space: nowrap;
  }

  .action-col {
    width: 25%;
    color: #1e293b;
    font-weight: 600;
    border-left: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
  }

  .action-col em {
    display: block;
    font-size: 7.5pt;
    font-style: normal;
    color: #64748b;
    margin-top: 3px;
  }

  .speech-col {
    width: 44%;
    color: #0f172a;
    line-height: 1.4;
  }

  .speech-col strong {
    color: #003087;
  }

  .rubric-col {
    width: 18%;
    border-left: 1px solid #e2e8f0;
    font-size: 7.5pt;
    color: #334155;
  }

  .rubric-tag {
    display: inline-block;
    padding: 2px 5px;
    background: #e2e8f0;
    border-radius: 3px;
    font-weight: 700;
    margin-bottom: 3px;
    font-size: 7pt;
  }

  .rubric-tag.pp { background: #dbeafe; color: #1e40af; }
  .rubric-tag.ag { background: #dcfce7; color: #166534; }
  .rubric-tag.ac { background: #fef3c7; color: #92400e; }

  .formula-card {
    background: #0f172a;
    color: #38bdf8;
    padding: 10px 14px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5pt;
    margin: 8px 0;
    border-left: 4px solid #0070ba;
  }

  .qa-card {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 8px;
    background: #ffffff;
  }

  .qa-q {
    font-weight: 700;
    color: #003087;
    margin-bottom: 3px;
    font-size: 8.5pt;
  }

  .qa-a {
    color: #334155;
    font-size: 8pt;
    line-height: 1.35;
  }

  .checklist {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    font-size: 8pt;
    margin-top: 8px;
  }

  .check-item {
    background: #f1f5f9;
    padding: 6px 10px;
    border-radius: 4px;
    border-left: 3px solid #00a86b;
  }

  .page-break {
    page-break-after: always;
  }
</style>
</head>
<body>

  <!-- Header Card -->
  <div class="header-card">
    <div class="title-row">
      <h1>ProductFind Sentinel 🛡️</h1>
      <div class="badges">
        <span class="badge badge-paypal">PayPal + AI</span>
        <span class="badge badge-grid">AG Grid 1st Place</span>
        <span class="badge badge-time">Target: 2m 10s</span>
      </div>
    </div>
    <div class="subtitle">Official Video Demonstration Script & Presenter Runbook</div>
    <div class="meta-grid">
      <div><strong>Platform:</strong> PayPal AI Hackathon</div>
      <div><strong>Devpost ID:</strong> #1278355</div>
      <div><strong>Hard Limit:</strong> &lt; 3:00 min</div>
      <div><strong>Resolution:</strong> 1080p (60 FPS)</div>
    </div>
  </div>

  <!-- Presenter Pre-Recording Checklist -->
  <div style="margin-bottom: 12px;">
    <div style="font-size: 8.5pt; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">Pre-Recording Sanity Checklist</div>
    <div class="checklist">
      <div class="check-item">✅ <strong>Server Running:</strong> Confirm <code>http://localhost:8000</code> responds with <code>status: healthy</code>.</div>
      <div class="check-item">✅ <strong>Clean Viewport:</strong> Browser zoomed to 90% or 100% full screen (F11) with bookmarks bar hidden.</div>
      <div class="check-item">✅ <strong>Audio Quality:</strong> Crisp microphone, no background room echo; speak with brisk confidence.</div>
      <div class="check-item">✅ <strong>Zero-Error Setup:</strong> Click the 🖥️ Dell Precision pill once before recording to pre-cache tiles.</div>
    </div>
  </div>

  <!-- Phase 1 to Phase 3 Table -->
  <div class="section-title">
    Demo Execution Timeline
    <span>Total Target Duration: 2 Minutes 10 Seconds</span>
  </div>

  <table class="timeline-table">
    <thead>
      <tr>
        <th class="time-col">Timestamp</th>
        <th class="action-col">On-Screen Action</th>
        <th class="speech-col">Spoken Voiceover Script (Word-for-Word)</th>
        <th class="rubric-col">Judging Focus</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="time-col">0:00 - 0:25<br><em>(25 sec)</em></td>
        <td class="action-col">
          <strong>The Problem Hook</strong>
          <em>Show Amazon / Flipkart tab with misleading discount or vacuum brush roller accessory priced at ₹9,332.</em>
        </td>
        <td class="speech-col">
          "Online shopping is quietly broken by <strong>hidden traps</strong>. A consumer clicks on a massive 70% discount, only to discover surprise cross-border tariffs, voided local warranties, or high-deductible fine print. Worst of all, marketplace algorithms routinely <strong>hijack product searches</strong>—serving cheap accessory brush rollers to fake an impossibly low sticker price.<br><br>
          Consumers lose over 15 billion dollars annually to grey-market risks. <strong>Meet ProductFind Sentinel.</strong>"
        </td>
        <td class="rubric-col">
          <span class="rubric-tag ac">Agentic Commerce</span><br>
          Relatable consumer pain point & real-world market friction.
        </td>
      </tr>
      <tr>
        <td class="time-col">0:25 - 0:55<br><em>(30 sec)</em></td>
        <td class="action-col">
          <strong>Multi-Agent Swarm Arbitration</strong>
          <em>Switch to localhost:8000. Click the '🖥️ Dell Precision 7820' query pill, adjust risk sliders, and hit 'Arbitrate Deals'.</em>
        </td>
        <td class="speech-col">
          "Sentinel replaces naive sticker shopping with an <strong>autonomous multi-agent swarm</strong>. When we initiate arbitration, specialized micro-agents deploy in parallel: our <strong>Web Scouts</strong> scrape 23+ live retailers using Chrome TLS impersonation, our <strong>Customs Inspector</strong> maps WTO landed tariffs, and our <strong>Warranty Actuary</strong> values manufacturer protection.<br><br>
          Instead of naive price tags, Sentinel computes true <strong>Risk-Adjusted Total Cost of Ownership</strong>—penalizing predatory restocking fees and rewarding verified open-box OTP delivery."
        </td>
        <td class="rubric-col">
          <span class="rubric-tag ac">Agentic Commerce</span>
          <span class="rubric-tag pp">PayPal + AI</span><br>
          Multi-agent pub/sub blackboard architecture.
        </td>
      </tr>
      <tr>
        <td class="time-col">0:55 - 1:25<br><em>(30 sec)</em></td>
        <td class="action-col">
          <strong>AG Grid Quartz Dark Cockpit</strong>
          <em>Scroll smoothly to the Arbitrated Matrix. Type 'Amazon' into quick filter, hover on SVG trust meters, and click 'Export CSV'.</em>
        </td>
        <td class="speech-col">
          "To make high-velocity institutional arbitration effortless, we engineered this <strong>AG Grid Quartz Dark Cockpit</strong>.<br><br>
          Notice the <strong>pinned merchant branding</strong> on the far left, keeping store identity locked during horizontal scrolling. In the center, our custom cell renderers visualize live <strong>SVG trust meters</strong>, biometric delivery badges, and risk-adjusted TCO. On the far right, our <strong>pinned action column</strong> guarantees instant one-click checkout. With virtualized 60-FPS rendering and instant CSV data export, it turns opaque marketplaces into transparent financial intelligence."
        </td>
        <td class="rubric-col">
          <span class="rubric-tag ag">AG Grid 1st Place</span><br>
          Pinned columns, custom cell renderers, quick search & CSV export.
        </td>
      </tr>
    </tbody>
  </table>

  <!-- Page Break for clean 2-page print -->
  <div class="page-break"></div>

  <!-- Header repetition for Page 2 -->
  <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; margin-bottom: 12px; font-size: 8pt; color: #64748b;">
    <span><strong>ProductFind Sentinel</strong> — Demo Video Presentation Script</span>
    <span>Devpost Submission #1278355 • Page 2</span>
  </div>

  <table class="timeline-table">
    <thead>
      <tr>
        <th class="time-col">Timestamp</th>
        <th class="action-col">On-Screen Action</th>
        <th class="speech-col">Spoken Voiceover Script (Word-for-Word)</th>
        <th class="rubric-col">Judging Focus</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="time-col">1:25 - 1:50<br><em>(25 sec)</em></td>
        <td class="action-col">
          <strong>PayPal Checkout & Section 13 Dossier</strong>
          <em>Click 'Pay with PayPal' on the top recommendation card. Show Pay in 4 terms. Then click 'Dossier' to open Merkle modal.</em>
        </td>
        <td class="speech-col">
          "Now comes our most powerful integration: <strong>Autonomous PayPal Protection</strong>. Clicking 'Pay with PayPal' invokes the PayPal Orders v2 API with live <strong>PayPal Pay in 4</strong> bi-weekly installment projections.<br><br>
          Simultaneously, Sentinel generates a cryptographic <strong>Section 13 Dispute Escrow Dossier</strong>. We compute SHA-256 Merkle proofs capturing the exact merchant product specs, warranty clauses, and return policies at the millisecond of purchase. If a seller ships an empty box or denies warranty, the buyer has mathematical, timestamped evidence cited directly under PayPal User Agreement Section 13."
        </td>
        <td class="rubric-col">
          <span class="rubric-tag pp">PayPal + AI</span>
          <span class="rubric-tag ac">Agentic Commerce</span><br>
          PayPal Orders v2, Pay in 4 & Section 13 Cryptographic Escrow.
        </td>
      </tr>
      <tr>
        <td class="time-col">1:50 - 2:10<br><em>(20 sec)</em></td>
        <td class="action-col">
          <strong>Self-Healing HUD & Closing</strong>
          <em>Pan across the Autonomous Self-Healer HUD with all 5 green healthy subsystems. Finish on the clean dashboard.</em>
        </td>
        <td class="speech-col">
          "Under the hood, our <strong>Voyager/Reflexion Self-Healer</strong> continuously audits stealth browser health, verifies dead links, and learns new merchant DOM skills on the fly—backed by a <strong>Zero-Crash Fallback Guarantee</strong>.<br><br>
          By uniting autonomous multi-agent AI, AG Grid analytics, and cryptographic PayPal dispute escrow, <strong>ProductFind Sentinel</strong> redefines the future of agentic commerce. Thank you!"
        </td>
        <td class="rubric-col">
          <span class="rubric-tag ac">Agentic Commerce</span><br>
          Autonomous self-healing & zero-crash guarantee.
        </td>
      </tr>
    </tbody>
  </table>

  <!-- Actuarial TCO Formula Box -->
  <div style="margin-top: 10px; margin-bottom: 12px;">
    <div style="font-size: 8.5pt; font-weight: 700; color: #003087; margin-bottom: 4px;">Actuarial Risk-Adjusted TCO Valuation Model (Engineered in Backend)</div>
    <div class="formula-card">
      TCO = Landed Outlay + Deductible Risk + Restocking Penalty + Grey Market Risk + Tariffs - Warranty Valuation - PayPal Shield
    </div>
  </div>

  <!-- Judge Q&A Defense Quick Card -->
  <div class="section-title" style="margin-top: 12px;">
    Judge Q&A Defense Sheet (Anticipated Questions & 15-Second Answers)
  </div>

  <div class="qa-card">
    <div class="qa-q">Q1: "How do you prevent bot-detection when scraping 23+ live merchants?"</div>
    <div class="qa-a">"We use <code>curl_cffi</code> and Playwright with Chrome 124 TLS JA3/JA4 fingerprint impersonation and session rotation. Furthermore, our <code>AdaptiveSkillLearner</code> self-heals broken selectors dynamically, backed by our offline zero-crash mock fallback."</div>
  </div>

  <div class="qa-card">
    <div class="qa-q">Q2: "Why AG Grid instead of a standard HTML table or generic library?"</div>
    <div class="qa-a">"AG Grid 32 Community delivers true institutional finance performance. Its virtualized DOM easily renders dozens of complex multi-currency rows with zero jitter, custom SVG trust meters, pinned left/right columns for brand recognition and 1-click checkout, and instant CSV export."</div>
  </div>

  <div class="qa-card">
    <div class="qa-q">Q3: "How does the Section 13 Cryptographic Dossier actually help in a PayPal dispute?"</div>
    <div class="qa-a">"Merchants frequently alter return policies or product descriptions post-purchase. Sentinel mints a deterministic SHA-256 Merkle root binding the exact DOM text, pricing breakdown, and seller credentials at the second of checkout, giving PayPal adjudicators irrefutable cryptographic proof."</div>
  </div>

  <div class="qa-card">
    <div class="qa-q">Q4: "What is your commercial business model?"</div>
    <div class="qa-a">"We monetize through PayPal affiliate merchant checkout bounties, premium enterprise procurement API subscriptions for corporate IT purchasing, and zero-fee buyer-side arbitration."</div>
  </div>

</body>
</html>
"""

async def generate_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(HTML_CONTENT, wait_until="networkidle")

        pdf_path = os.path.abspath("ProductFind_Sentinel_Demo_Script.pdf")
        brain_pdf_path = os.path.abspath(r"C:\Users\yuvan\.gemini\antigravity\brain\143f81a9-601b-41b7-ae02-27658d88dd44\ProductFind_Sentinel_Demo_Script.pdf")

        await page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "0cm", "bottom": "0cm", "left": "0cm", "right": "0cm"}
        )
        shutil.copyfile(pdf_path, brain_pdf_path)
        await browser.close()
        print(f"SUCCESS: Rendered professional PDF to {pdf_path}")

if __name__ == "__main__":
    asyncio.run(generate_pdf())
