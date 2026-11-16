# Voice Is the OS: research brief, narrative and build plan

Working notes behind the ElevenLabs Summit NYC recap page (`index.html`).
Compiled 2026-11-16.

---

## 1. The event

| | |
|---|---|
| **What** | ElevenLabs Summit New York, a one-day, invite/apply-only event |
| **When** | Wednesday, November 11, 2026 (Polish Independence Day, a detail Polish founders in the room noticed) |
| **Where** | Lincoln Center, New York |
| **Crowd** | About 2,000 customers and partners (two attendee posts give that figure) |
| **Theme** | "The interaction layer for AI": ElevenLabs as the layer between people and models, not just a voice vendor |
| **Format** | Keynotes, customer panels and firesides, plus performances (the Impact Program performers, ElevenMusic singing voices) |

### Agenda (final version, after Jensen Huang withdrew)

| Time | Session | Who |
|---|---|---|
| 10:00 | Opening keynote | Mati Staniszewski, co-founder & CEO |
| 10:45 | *From Answering to Acting: Agentic Voice AI in Regulated Finance* | Ethan Tandowsky (CFO, ElevenLabs), Carlos Coto (Customers Bank), Daniela Mineiro (Banco Inter), Douglas Hamilton (Nasdaq) |
| 11:10 | Fireside | Eric Glyman (co-founder & CEO, Ramp) with Mati Staniszewski |
| 11:30 | Enterprise deployment lessons | Ashley Kramer (CRO, ElevenLabs), Cameron Pringle (Clover Health) |
| 11:55 | *Beyond the Pilot* | Ashish Uchil (ElevenLabs), Yael Taqqu (McKinsey), Matt Yanchyshyn (AWS Marketplace) |
| 2:05 | ElevenCreative / ElevenProductions | Aneri Amin; Alex George with Dustin Myers (Fox Sports) |
| 3:00 | Chroma Awards (Sidewalk Stage) | AI film awards and screening |
| 3:05 | Startup Program | Jonathan Chang with founders |
| 4:00 | ElevenLabs Impact Program | Gabi Leibowitz |
| 4:30 | Closing keynote | Mati Staniszewski |

**Agenda changes:**
- NVIDIA CEO Jensen Huang was billed but withdrew days before. Sifted and TechCrunch reported it, tied to an internal Nvidia investigation.
- Customers Bank CEO Sam Sidhu was in early promotion, but Carlos Coto is on the final agenda.
- One search snapshot of the agenda puts Glyman at a 4:30 closing fireside. The final version, used in your pre-read, has him at 11:10 and Mati closing. **Please confirm from memory.**

---

## 2. What was announced ("13 launches and upgrades")

| Release | What it is | Status (as of Nov 16) |
|---|---|---|
| **Interaction Engine** | Orchestrates the conversation: turn-taking, interruptions, and routing each step to the right model (cheap model for triage, frontier model for hard parts) | **Preview** |
| **ElevenAI** | Work app: meeting recording (in person too) with attendee notification, notes and action items, dictation in 90+ languages into any app, agent follow-ups (e.g. draft the email). Built on Scribe v3 | **Free early access** (waitlist) |
| **Memory** (ElevenAgents) | Recognizes returning customers; turns each conversation into structured notes; the CRM stays the system of record | **Upcoming, no date** |
| **Routines** (ElevenAgents) | Multi-step automations before, during and after calls, wired to business systems | **Upcoming, no date** |
| **Custom models** | Fine-tune selected open-source LLMs and ElevenLabs voice models on deployment data, with ElevenLabs researchers | **Coming months, selected enterprises** |
| **Eleven Realtime** | Speech-to-speech model family for voice agents; ~570 ms to first audio (Product Hunt listing) | Live |
| **Scribe v3 / v3 Live / v3 Medical** | STT with ~27% fewer word errors than v2 across 102 languages (ElevenLabs; The Decoder says ~25%). Live adds real-time speaker labels and turn prediction. Medical handles clinical terms | v3 + Live: live; Medical: availability unclear |
| **Eleven v4** | Most emotive TTS model (released Sept 28, 2026; featured at summit) | Live |
| **Partner Program** | 550+ organizations across 44 countries | Live |
| **Marketplace** | Partner-built industry apps | Listing live; purchasing planned for 2027 |
| **NVIDIA expansion** | Nemotron 3.5 Super VL live in ElevenAgents; +15 MW of Blackwell Ultra / Vera Rubin capacity for secure, data-resident deployments; on-prem agent for Poland's national e-Health platform | Model live; compute being added |
| **McKinsey alliance** | ElevenAgents + McKinsey transformation practice and QuantumBlack | Announced |
| **Impact Program** | Free lifetime voice restoration; Wounded Warrior Project; free ElevenMusic for songwriters with voice loss via SONA; NYU Langone Rusk Rehabilitation | Live |

### Customer proof points cited around the summit
- **KPN** (Dutch telecom): identity verification, order checks and technician booking in Dutch. Tuning on Dutch data lifted ID-verification accuracy from about **50% to 90%** (ElevenLabs). One podcast summary says **60% to 85%**.
- **Yahoo Scout:** voice added on ElevenAgents; out of beta after 3B+ answers.
- **Westgate:** "Sarah," a front-desk voice agent.
- **Banco Inter:** 2M+ customer-service interactions a month in Portuguese, English and Spanish. Its AI resolves 80% of investment withdrawal and deposit calls end to end, with CSAT above 4.5 (from the pre-summit case study).
- **Customers Bank** (~$25B assets): a 24/7 voice and chat agent, an onboarding agent, and an agent that coaches human staff live on calls. Coto's line: *"full self-service for the ones that don't want to interact with humans, and human beings powered by agents for the people that value the interaction."*
- **Fox Sports:** an AI persona of Colin Cowherd in the Fox Sports app.

---

## 3. Key people

**ElevenLabs:** Mati Staniszewski (co-founder & CEO), Piotr Dabkowski (co-founder), Ethan Tandowsky (CFO), Ashley Kramer (CRO), Ashish Uchil, Alex George (localization), Aneri Amin, Jonathan Chang (startups), Gabi Leibowitz (Impact).

**External:** Eric Glyman (Ramp), Carlos Coto (Customers Bank), Daniela Mineiro (Banco Inter), Douglas Hamilton (Nasdaq), Cameron Pringle (Clover Health), Yael Taqqu (McKinsey), Matt Yanchyshyn (AWS Marketplace), Dustin Myers (Fox Sports). Performers Greg Kelner and Abdi Omar sang with voices rebuilt through the Impact Program. Jensen Huang (NVIDIA) was billed but absent.

### On-the-record quotes
- Mati: *"Within a few years, conversational agents will become critical infrastructure for every enterprise, as essential as cloud or payments."*
- Mati: *"If AI is going to work for us, and alongside us, it will need to interact naturally and intuitively with people in many different settings."*
- Mati (paraphrased in coverage): businesses will increasingly build their own reinforcement-learning stacks to put proprietary data to work.

---

## 4. Pundit and press read

- **Main framing:** ElevenLabs is moving from voice generation to conversation infrastructure (TNW, Unite.AI, CXO Digitalpulse, Techzine: "ElevenLabs wants to claim the interaction layer").
- **Skeptical take:** about half of what was announced is preview, early access or roadmap. Marketplace purchasing waits until 2027, and Memory and Routines have no date (DEV Community write-ups, Datastudios).
- **Builder take:** "13 products, only 3 matter if you build voice agents." Developers care most about Scribe v3 Live, Eleven Realtime and the Interaction Engine.
- **ElevenAI:** TechCrunch and Digital Trends frame it as ElevenLabs coming for meeting-notes and dictation apps such as Otter, Granola and Wispr.
- **NVIDIA subplot:** NVIDIA expanded the deal at the summit Jensen skipped.
- **Gap:** I found no published recap of what the finance panelists or Glyman actually said on stage. **Your notes are the only source for that.**

### Regulated-industry context used in the piece
- Voice biometrics are weakening as a single factor. FinCEN deepfake alerts, the UK FCA's discussion paper on synthetic media (Jan 2026) and OSFI's voice-cloning scenario guidance all push toward independent verification.
- Model risk management (SR 11-7) applies to tuned models and to router-selected models.
- Wall Street has paid billions in off-channel recordkeeping fines. A meeting recorder or an agent with memory is a new communications channel.
- The FCC treats AI-generated voices as "artificial" under the TCPA (2024), so outbound AI calls need consent.

---

## 5. Narrative (your voice, draft)

**Thesis:** Voice is becoming the interface for software, and ElevenLabs wants to own the layer underneath. For regulated industries, the shift from *answering* to *acting* turns a content problem into a controls problem.

**Structure:** an album.
- **Side A, "The day"** (chronological)
  - 01 *The interaction layer*: the keynote, and why "as essential as payments" is a loaded phrase in banking
  - 02 *From answering to acting*: the finance panel, where one verb changes the risk profile, and the human handoff as a product feature
  - 03 *Zero click*: Ramp, AI decisions with the receipts attached
  - 04 *The drop*: thumb through the releases, each with a status sticker
- **Side B, "The fine print"** (the regulated lens)
  - 05 *Memory is a records problem*: a feature-to-control translation table
  - 06 *The identity paradox*: the voice is the interface, never the credential. KPN's 50% to 90% is the most important number of the day
  - 07 *Which model answered?*: router lineage as a model-risk requirement
  - 08 *What I'm taking back to work*: five points for a risk committee
- **Hidden track:** *Two voices, returned*, the Impact performances. The same tech that makes a voice forgeable gave two people theirs back.

**Your raw thoughts were not included in the original request.** Every first-person observation on the page is a draft written to your stated lens. Swap in what you actually heard, felt and disagreed with; that's where it becomes yours.

---

## 5b. Case-study layer (added from your notes, Nov 16)

**Your thesis:** the summit was a marketing masterclass as much as a product launch.

| Your observation | What I could verify | How it's used |
|---|---|---|
| Held in David Geffen Hall, home of the NY Philharmonic. Genius for a company betting on high-fidelity voice | Hall reopened Oct 8, 2022 after a ~$550M rebuild aimed at acoustic problems dating to 1962. About 2,200 seats. Wood panels are shaped after sound waves (CBS News, Dezeen). The summit venue itself is only reported as "Lincoln Center"; Geffen Hall is from your account | Track 01, *The room is the product* (stat: 2,000 attendees in a ~2,200-seat hall) |
| Mati's live demos were flawless; Jobs-style real demo, not recordings | No public write-up describes the demos. ElevenLabs confirms the keynote included a "sneak preview" of ElevenAI | Track 02, *No safety net*. Written from your account; no specific demo is named |
| Language not overtly technical; felt like arriving on a bigger stage beyond technologists | Matches the plain-language keynote quotes in coverage | Track 02 |
| Try-it-yourself booths; Bancolombia showed its customer FAQ agent; scoped to a set of questions; agentic ambition | Nothing public links Bancolombia and ElevenLabs | Track 03, *Try it yourself*; bridges to the answering-vs-acting panel |

### Scaling panel, 11:55: "What it takes to scale AI across the enterprise" (from your notes and photo)
Speakers per the stage slide: Matt Yanchyshyn (VP, AWS), Yael Taqqu (Senior Partner, McKinsey), Ashish Uchil (Global BD & Partnerships, ElevenLabs).
- **Matt, on the 360-degree cost:** the hidden costs of AI. Automating support queues or demand gen shifts load elsewhere. Plan for demand spikes and for the people who handle what automation sends downstream.
- **Matt, on tools:** AWS's philosophy is "choose the right tools and obsess over the rest." AWS has run 90%+ AI utilization for years. The specific tool matters less than purpose. Some waste is necessary to learn, but you have to move past it.
- **Matt, on engineers:** software engineers are now treated as product engineers, with a strategic lens and real product understanding. Generate product spec-driven, inside a harness, rather than generating "stuff."
- **Yael:** a technology revolution that is also a talent revolution. Leaders need boldness and humility together, which is rare; most leaders have to learn the humility.
- **Used in:** new track 08, *The 360-degree cost* (iceberg illustration). New sixth takeaway: "Budget for the 360." The banking tie-in: automation leaves people with the hardest calls, agents scale instantly but back offices don't, and a spec is something an auditor can read.

### From your photos (Nov 16)
- **Venue confirmed:** the exterior shot shows the "David Geffen Hall" sign. The interior shows the hall's wood-paneled walls.
- **Finance panel titles (slide):** Douglas Hamilton, Head of AI Research & Engineering, Nasdaq · Daniela Mineiro, Experience Leader, Inter · Carlos Coto, Chief Strategy & Innovation Officer, Customers Bank.
- **Ramp fireside title (slide):** "A conversation on building an AI-first company." Eric Glyman (CEO, Ramp) with Mati Staniszewski (CEO and co-founder).
- **NVIDIA session (new):** "A conversation with NVIDIA on models, infrastructure, and sovereignty at scale." Kari Briski (VP Generative AI Software Products, NVIDIA) with Alex Holt (Field CTO, ElevenLabs). NVIDIA was on stage even though Jensen Huang withdrew.
- **Impact Program (slide):** Greg **Kelner** (corrected spelling), Gabi Leibowitz (Impact, ElevenLabs), Abdi Omar. Music stands and instruments on stage for the performances.
- **Bancolombia booth:**
  - Labeled "Customer Support FAQ"; the screen reads "Bancolombia Assistant X Eleven Labs".
  - Hold to talk, with headphones.
  - Stated scope: products and services; credit cards and loans; requirements and documentation; fees, benefits and features; support and self-service processes.
  - Suggested questions include "How can I send money?"
  - The screen carries a line noting the bank is supervised by the Financial Superintendency of Colombia.
- **Listening room:** an exhibit lined with acoustic foam, with headphones, and New Yorkers' stories captioned on a speaker-shaped round screen (e.g. "Auntie Chan, 67").
- **Photos on the page:** 14 photos (two crew shots in the liner notes, badges blurred), cropped, resized to 1200px and stripped of all metadata, including location. The listening-room shot with attendees was cropped to the screen only, so no faces appear (12 photos in all).

### Corrections from you (Nov 16)
- **Ramp was the closing session (4:30 PM),** not 11:10. Eric Glyman with Mati, "A conversation on building an AI-first company."
- **What it covered:** how to capture AI's potential. It was not about Ramp's product, receipts or "zero click"; that framing came from my pre-read and has been removed.
- **"AI waste to get to AI usefulness" was Eric's line,** not Matt Yanchyshyn's. Removed from the AWS section and moved to the Ramp track.
- **Eric's example:** in 2023, ChatGPT might say 2+2 = 11 or miscount the r's in "strawberry"; now OpenAI's most advanced models solve math problems no mathematician had solved.
  - **Checked:** no OpenAI model called "Astra" exists (Project Astra is Google's). The verified example is an internal OpenAI model disproving the 80-year-old Erdős unit distance conjecture, checked by outside mathematicians and announced May 20, 2026 ([OpenAI](https://openai.com/index/model-disproves-discrete-geometry-conjecture/), [Scientific American](https://www.scientificamerican.com/article/ai-just-solved-an-80-year-old-erdos-problem-and-mathematicians-are-amazed/)).
  - **Still unverified:** OpenAI's Navier–Stokes claim (Sept 2026) is still being checked ([NPR](https://www.npr.org/2026/09/22/nx-s1-5968588/openai-navier-stokes-problem-mathematicians-learn-little)).
  - **On the page:** the example is attributed to Eric, without a model name or date.
- **Side B order is now:** 05 keynote · 06 finance · 07 the 360-degree cost · 08 the drop · 09 *Waste on the way to useful* (closing session).

**New structure (double album):**
- Side A, the show (case study): 01 The room is the product · 02 No safety net · 03 Try it yourself · 04 The playbook
- Side B, the day: 05 The interaction layer · 06 From answering to acting · 07 The 360-degree cost · 08 The drop · 09 Waste on the way to useful (closing)
- Side C, the fine print: 10 Records · 11 Identity · 12 Which model answered? · 13 Taking back to work (now six takeaways)
- Side D: hidden track, *Two voices, returned*

Track 04 is a "six moves worth stealing" table (move / what they did / why it worked / how a bank could borrow it). A case-file card styled as a CD jewel case sits under the scoreboard.

## 6. Build plan (as built)

| Element | 2000s / retro-futurist reference | Job on the page |
|---|---|---|
| **Signal ribbon** | Marathon-email stripes, re-cut as a 5-conductor audio cable | One continuous line drawn down the page as you scroll; bends around each "track" and passes behind flat silhouette illustrations |
| **Now Playing LCD** | Sticky top bar styled like a 2000s music-player display | Shows track, artist and side, with elapsed and remaining read time and prev/play/next |
| **Sideways-device carousel** | Thumbing album art on a device turned sideways | The 12 releases as album covers with "shrink-wrap" status stickers; tap the front cover to flip it for liner notes; scrubber, swipe and arrow keys |
| **List view toggle** | The device's list view with zebra rows | Every release at once, with status and "my read" |
| **Scoreboard + badge** | The marathon results block and race bib | 2,000 / 13 / 550+ / 15 MW, with a summit badge as the bib |
| **Read aloud** | Voice is the OS: the page talks | Play reads the recap track by track in a Claude voice where available (browser voice otherwise); quotes are read in a second voice |
| **Silhouettes** | Marathon borough illustrations | Lincoln Center's opera-house arches, microphone, bank colonnade, card and receipt, record sleeve, filing cabinet, padlock with waveform keyhole, jukebox, cassette, two mics under a spotlight |

---

## Sources

- ElevenLabs: [Summit NYC: The Interaction Layer for AI](https://elevenlabs.io/blog/nyc-summit), [Enterprise customers at the summit](https://elevenlabs.io/blog/enterprise-nyc-summit), [Impact Program news](https://elevenlabs.io/blog/impact-nyc-summit), [NVIDIA expansion](https://elevenlabs.io/blog/nvidia), [Customers Bank partnership](https://elevenlabs.io/blog/customers-bank-partnership), [Summit agenda](https://elevenlabs.io/summit/new-york)
- Press: [TechCrunch](https://techcrunch.com/2026/11/13/elevenlabs-new-app-combines-meeting-note-taking-and-dictation-for-teams/), [The Next Web](https://thenextweb.com/news/elevenlabs-summit-nyc-elevenai-custom-models-partner-program), [Unite.AI](https://www.unite.ai/elevenlabs-unveils-model-customization-elevenai-and-partner-program/), [Digital Trends](https://www.digitaltrends.com/computing/elevenlabs-is-coming-for-your-meeting-notes-dictation-app-and-maybe-your-productivity-routine/), [The Decoder](https://the-decoder.com/elevenlabs-scribe-v3-live-uses-conversational-context-to-stop-voice-agents-from-cutting-off-callers-mid-sentence/), [Mumbrella](https://mumbrella.com.au/elevenlabs-launches-13-new-products-and-upgrades-944467), [CXO Digitalpulse](https://www.cxodigitalpulse.com/elevenlabs-builds-out-the-interaction-layer-for-ai-with-major-new-model-and-agent-upgrades/), [Techzine](https://www.techzine.eu/blogs/applications/144778/elevenlabs-wants-to-claim-the-interaction-layer/), [Sifted](https://sifted.eu/articles/jensen-huang-pulls-out-of-elevenlabs-summit-amid-controversy/), [DEV Community](https://dev.to/paullovelace/elevenlabs-is-now-infrastructure-custom-models-elevenai-partners-3c04)
- Social: [Borys Musielak on X](https://x.com/michuk/status/2120539838998814793), [ElevenLabs on X (finance panel)](https://x.com/ElevenLabs/status/2113616436170240103)
