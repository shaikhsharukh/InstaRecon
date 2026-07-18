# InstaRecon

**Instant company intelligence for any website.**

Give InstaRecon a URL and it produces a full research report on the company behind it. A swarm of specialized research agents — each running in its own isolated [Daytona](https://www.daytona.io/) sandbox — investigates the company in parallel, streams findings live to the browser, and hands everything to a compiler that synthesizes a final Intel Brief. The finished report is displayed on the website and available for download as a PDF.

## How It Works

1. **Submit a URL** — paste any website/domain into the web app (Next.js frontend).
2. **Swarm spawns** — the FastAPI backend coordinator creates a job and launches the research agents in parallel, each in an independent Daytona sandbox.
3. **Agents investigate** — every agent researches one dimension of the company:

   | Agent | What it digs up |
   |-------|-----------------|
   | 🔍 **Product Analyzer** | Company name, product, category, and target market (runs first — feeds the Competitor Finder) |
   | ⚔️ **Competitor Finder** | Top competitors and a comparison matrix |
   | 🛠️ **Tech Stack Detective** | Frameworks, CMS, CDN, and hosting infrastructure |
   | 📈 **SEO Scanner** | SEO health — meta tags, structure, performance |
   | 📣 **Social Auditor** | Social media profiles and presence assessment |
   | 💬 **Sentiment Analyzer** | Reviews from Trustpilot, Google, and Reddit with sentiment analysis |
   | 👔 **Hiring Signal Detector** | Job listings and inferred hiring strategy |

4. **Live feed** — findings stream to the UI over WebSocket while agents work.
5. **Compile** — the Synthesizer cross-references all agent reports: agreements, conflicts, anomalies, risks, and opportunities.
6. **Deliver** — the final Intel Brief is rendered on the site and downloadable as a PDF (or sent by email).

## Architecture

```mermaid
flowchart TD
    U([User]) -->|website / domain| FE[Next.js Web App]
    FE -->|POST /api/recon| CO[FastAPI Coordinator]

    CO --> A1 & A2 & A3 & A4 & A5 & A6 & A7

    subgraph Daytona Sandboxes — one per agent
        A1[🔍 Product Analyzer]
        A2[⚔️ Competitor Finder]
        A3[🛠️ Tech Stack Detective]
        A4[📈 SEO Scanner]
        A5[📣 Social Auditor]
        A6[💬 Sentiment Analyzer]
        A7[👔 Hiring Signal Detector]
    end

    A1 -.->|company + category| A2

    A1 & A2 & A3 & A4 & A5 & A6 & A7 --> SY[Compiler / Synthesizer]

    SY --> RP[📄 Final Intel Brief]
    RP -->|view + PDF download| FE
    CO -.->|WebSocket: live findings| FE
```

## Sample Report

A preview of a generated Intel Brief will appear here for the demo.

<!-- TODO: embed sample report preview once generated -->
> 🚧 *Sample report not generated yet — coming soon.*
