# Red Letters Source Reader — Brainstorming Session

**Date**: 2026-01-26
**Session Type**: Progressive Flow (Divergent → Convergent → Crystallization)
**Status**: Complete

---

## Executive Summary

This session designed a **truth-handling system** for Greek New Testament interpretation — not a translation tool, not a commentary, not a theology engine.

### Four Crystallizations (Design Gravity)

| Dimension | Locked Decision |
|-----------|-----------------|
| **Primary Audience** | A person who believes texts are constrained but underdetermined, asking "What would I have to assume for each reading to hold?" because they no longer trust inherited certainty but refuse to abandon disciplined reading. |
| **Core Loop** | Interrogate → Expose → Probe → Reorient |
| **Trust Stack** | Procedural Honesty → Traceable Provenance → Consistent Constraints → Resistance to Over-Resolution → Stable Behavior Across Lenses |
| **Extensibility Vector** | Constraint Expansion (not Meaning Expansion) — grow by sharpening the question, not answering it |

### The Sting (What This Project Must Never Become)

Without discipline, this project will slowly mutate into:
- A stealth theology project, OR
- An AI paraphrase generator with academic cosplay

### One Sentence Summary

> **This tool does not tell you what to believe. It shows you what believing this would require.**

---

## I. Purpose & Non-Purpose

### What This Tool Exists To Do
- Generate 3-5 plausible English renderings for Greek NT "red letter" passages
- Expose every interpretive decision with traceable receipts
- Treat ambiguity as the product, not a bug to eliminate
- Provide ranked uncertainty, not false confidence

### What It Explicitly Refuses To Do
- Output a single "authoritative" translation
- Collapse lexical → syntactic → pragmatic → theological categories
- Hide sense selection, syntax decisions, or variant resolution
- Smuggle theology through English word choices
- Claim to recover "what Jesus really meant"
- Serve as a translation, commentary, theology engine, or "Jesus explained" app

**Core Identity**: Linguistic instrumentation tool — not a belief product.

---

## II. Epistemic Principles

### Transparency
- Show decisions, not just data
- Every rendering includes audit trail: text → constraints → choice
- "Git blame for meaning"

### Plurality
- Multiple readings are the feature
- Ambiguity is the product; ranked ambiguity is the deliverable

### Traceability
- Seven transparency layers:
  1. Text (edition, tokenization, punctuation)
  2. Morphology (with uncertainty flags)
  3. Syntax (dependencies, attachment, classifications)
  4. Semantics (sense inventory, domains, collocations, idioms)
  5. Pragmatics (speech act, emphasis, implied contrast, audience)
  6. Variants (with semantic impact, not just witness lists)
  7. Decision log (alternatives, rationale, what's lost/added)

### Reversibility
- Progressive disclosure: default → expandable → deep → deepest
- Users can always drill down to inspect any decision
- Nothing is hidden, but not everything is surfaced by default

### The Safeguard Principle
> Every transparency feature must answer one of two questions:
> 1. "Why was this option chosen over others?"
> 2. "What would change my mind?"
>
> If it doesn't answer one of those, it's noise or theater.

---

## III. Constraints & Parameters

### Technical Constraints
| Constraint | Value | Rationale |
|------------|-------|-----------|
| Budget | $0–low | Forces open datasets, avoids vendor theology |
| Timeline | 2-4 weeks MVP | Prevents over-engineering before epistemic clarity |
| Licensing | CC/permissive only | Avoid proprietary lexicons in core |
| Dependencies | Minimal | Every dependency is an epistemic authority |

### Scope Boundaries (MVP)
**In Scope**:
- Reader + generator
- Greek text → multiple English renderings
- Full receipt system

**Explicitly Deferred**:
- AI paraphrase as primary output
- Gospel harmonization
- Doctrinal tagging ("atonement," "sin," etc.)
- Community annotations
- Monetization
- UI polish

### Theological/Academic Constraints (Non-Negotiable)
- No claim of recovering original intent
- Distinguish: lexical meaning / syntactic role / pragmatic inference / theological extrapolation
- Admit uncertainty explicitly
- Greek primacy, Aramaic humility (witness layer, not original-text cosplay)

---

## IV. Axis 1: Interpretation Transparency (Complete)

### Where Existing Tools Hide Decisions
1. **Sense selection is silent** — Gloss masquerades as "the meaning"
2. **Syntax is flattened** — Genitive types, participle functions undisclosed
3. **Ambiguity resolved without disclosure** — Single path output
4. **Variants buried or weaponized** — No semantic impact explanation
5. **Theological defaults baked in** — sarx→"sinful nature", pistis→"faith" not "faithfulness"

**Net**: Most tools show data, not decisions.

### What Full Transparency Requires
Complete audit trail from text → constraints → choice, including:
- Which alternatives were considered
- Why the chosen option won
- What is lost/added by the choice
- "Theological load" indicator (worldview-sensitivity, not moral judgment)

### The Noise Threshold
Transparency becomes noise when it stops answering:
> "What are the plausible readings, and what would change my mind?"

**Three noise patterns**:
1. Raw morphology without relevance explanation
2. Too many equally-weighted options (12-way ties)
3. Full pipeline surfaced without progressive disclosure

**Solution**: Progressive disclosure
- Default: 3-5 readings + key receipts
- Expandable: syntax map
- Deep: full decision log + variants

### How Transparency Projects Rot (Failure Modes)

| Pattern | Description | Outcome |
|---------|-------------|---------|
| Data maximalism | Exhaustiveness without ranking | Users default to familiar/confident options |
| Silent heuristics | Glass box with black box inside | "Objective" tools become unquestionable |
| Category collapse | Clarity via foreclosure | Interpretive paths disappear |
| Expert-only trap | Jargon without mediation | Gatekeeping, not democratization |
| False neutrality | "We just present data" | Dependency amplifier |
| No consequences | Variants shown, "so what?" unanswered | Transparency perceived as noise |
| UX drift | Defaults calcify | Rankings harden into doctrine |

### Deeper Failure Mechanics
- Showing parts ≠ showing the path between them
- Confusing humility with abdication
- Forgetting users want orientation, not omniscience

### This Project's Rot Vectors (Watch List)
- [ ] Ranked ambiguity quietly becomes "recommended" reading
- [ ] Receipts stop explaining why, become decorative citations
- [ ] Plugins reintroduce theology without friction or labeling
- [ ] Advanced layers accessible only to insiders
- [ ] UI defaults become epistemic defaults
- [ ] "No interpretation" rhetoric creeps back
- [ ] AI paraphrase sneaks in as "helpfulness"

---

## V. Axis 2: Audience Fit (Complete)

### The Correct User (Cognitive Posture, Not Demographic)

**What they already believe (or tolerate)**:
- Texts are underdetermined — meaning is constrained, not dictated
- Translation is interpretation — curious about it, not scandalized
- Certainty is a gradient — can live with "likely," "possible," "contested"
- Authority is provisional — respects expertise, doesn't outsource judgment
- Ambiguity is informative — not weakness or evasion

**What question they're actually asking**:
> Not: "What does this verse mean?"
> But: "What are the real interpretive moves here, and which ones carry the most weight?"
> Or: "What would I have to assume for this reading to be true?"

They want **orientation, not validation**.

**Typical examples** (not exhaustive):
- Post-evangelicals / deconstruction-literate readers
- Translators and linguistics-curious students
- Skeptics who don't trust clergy but do trust process
- Clergy who are privately bilingual (public dogma / private uncertainty)

**Core trait**: They don't want the tool to decide for them. They want it to **think with them**.

---

### The Misuser (Failure Mode, Not Demographic)

**Their epistemic posture**:
- Certainty-seeking, not truth-seeking
- Confirmation-hunting
- Ambiguity-averse
- Instrumental: text as weapon, not dialogue partner

**What they believe**:
- If multiple readings exist, one must be "right"
- Complexity is either threatening or ammunition
- If a tool exists, it must settle debates

**Four misuse patterns**:

| Pattern | Behavior | Outcome |
|---------|----------|---------|
| **Proof-text mining** | Cherry-pick low-ranked readings, ignore confidence, weaponize minority possibilities | "The Greek says..." without receipts |
| **Authority laundering** | "This tool shows the real meaning" | Tool's refusal of that role is ignored |
| **Performative sophistication** | Use ambiguity to sound deep while remaining rigid | Ambiguity as shield, not invitation |
| **Paralysis as piety** | "It's all ambiguous, so nothing can be said" | Nihilism in academic clothing |

**Net**: This user turns transparency into either a **cudgel** or a **fog machine**.

---

### The Audience That Doesn't Exist Yet

**The latent audience: Epistemically rehabilitated readers**

People who:
- Were taught that faith = certainty
- Experienced betrayal when certainty collapsed
- Now oscillate between rigid literalism and total dismissal

**They don't currently ask**: "What are the plausible readings?"
**They ask**: "Is this text even worth engaging anymore?"

**What this tool could create**:
A new category of reader — not believers vs skeptics, but **literate participants in meaning-making**.

People who learn:
- How interpretation works
- How to disagree without bad faith
- How to hold commitment without illusion
- How to read ancient texts without surrendering agency

**This is epistemic formation, not education.**

**How the tool creates them (through interaction, not instruction)**:
- Ranked ambiguity → trains discernment
- Receipts → models intellectual honesty
- Consequence mapping → teaches responsibility
- Progressive disclosure → rewards curiosity

Over time, users internalize the method. They stop asking "Which one is right?" and start asking "What assumptions am I making right now?"

---

### The Trade-Off (Uncomfortable Truth)

> The tool cannot be neutral about epistemic maturity.

| Optimize for... | Result |
|-----------------|--------|
| Maximal accessibility | Maximal misuse |
| Epistemic responsibility | Slower adoption, deeper trust |

**This project should select for readiness, not popularity.**
That's not elitism. It's safety.

---

### Guardrail to Encode (Early)

> **"This tool does not tell you what to believe. It shows you what believing this would require."**

That sentence filters users better than any onboarding copy.

---

## VI. Axis 3: Trust & Legitimacy (Complete)

### Meta-Rule

> **Trust is not "belief in correctness."**
> **Trust is confidence that the system will not lie to you about what it's doing.**

---

### Trust Signals (What the Correct User Reads)

**A. The system visibly resists certainty**
- No "best" or "preferred" reading label
- Rankings that shift when assumptions toggle
- Confidence bands that widen when data is thin
- Explicit language: "this ranking depends on X"

*User thinks: "If this tool wanted to persuade me, it would hide that."*

**B. Decision logs that are boring, not rhetorical**
- Procedural reasoning, not elegant explanations
- Dry, almost tedious language
- Same logic applies even when it weakens popular readings
- Consistency beats elegance

**C. Provenance is first-class, not footnoted**
- Which text edition is used
- Where morphological tags come from
- Which lexicon supplied a gloss
- What's inferred vs imported

*Not because they'll check everything—but because they could.*
**Optional inspectability is a huge trust signal.**

**D. The tool exposes its own limits before the user finds them**
- "We cannot rank these confidently because…"
- "This ambiguity is irreducible without extra-textual assumptions"
- "Scholars disagree here for structural reasons"

*Reads as honesty, not weakness.*

**E. Stability across disagreement**
- Toggle theological neutrality, socio-political lens, translation philosophy
- System doesn't emotionally react or nudge back toward default
- No agenda gravity

---

### Trust Destroyers (Instant Failures)

| Destroyer | Example | Why Fatal |
|-----------|---------|-----------|
| **Hidden defaults** | Unmarked ranking bias, hidden preference for traditional renderings | One "oh so that's what this is doing" moment is fatal |
| **Steering language** | "Most scholars agree" (without context), "the Greek really means..." | Rhetorical tells; this audience has been burned before |
| **UI nudges** | First option emphasized, other readings behind clicks, editorializing tooltips | User knows UX is argument |
| **Over-eager helpfulness** | Auto-generated paraphrases, "simplified meaning" summaries | Smells like persuasion |
| **Credential theater** | Over-reliance on names, degrees, institutions, endorsements | Triggers skepticism; borrowed authority distrusted |

---

### Legitimacy Sources (Triangulated, Not Singular)

**No single authority confers legitimacy. It's triangulated.**

| Source | Priority | What It Looks Like |
|--------|----------|-------------------|
| **Process legitimacy** | Primary | Repeatable reasoning, explicit heuristics, consistency, visible disagreement handling |
| **Open inspectability** | Secondary | Logic is readable, decision points documented, doesn't hide behind "go read the code" |
| **Cautious adoption** | Tertiary | Scholars reference cautiously, translators use privately, clergy admit off-stage use, skeptics say "at least not lying" |
| **Institutional distance** | Paradoxical | Not owned by denomination, not branded by ideology, not funded by doctrinal agenda |

*Inspectability is about possibility, not participation.*
*Distance from power is itself a trust signal.*

---

### Critical Asymmetry

> **People will forgive incompleteness.**
> **They will not forgive epistemic dishonesty.**

A sparse tool that tells the truth about its limits will outlast a rich tool that occasionally overreaches.

---

### Design Principle (Lock In Now)

> **Trust accrues when the tool is willing to disappoint the user in service of honesty.**

Every time the system refuses to settle a question the user wants settled, it earns credibility with the audience you care about.

---

## VII. Axis 4: Extensibility Without Authority Creep (Complete)

### Governing Law

> **Extensions may influence probability, never confer authority.**

The moment an extension answers the question for the user, it ceases to be an extension and becomes an institution.

---

### Safe Extensions (Add Constraints Without Collapsing Choice)

**Core property**: They reweight the decision surface and show their work. They do not answer questions.

**A. Additive, not substitutive**
- New SenseProvider: contributes additional sense inventories, assigns weights, *never suppresses existing senses*
- VariantProvider: enumerates variants, annotates semantic impact, *does not auto-select preferred text*
- WitnessOverlay: shows parallel phrasing, highlights divergence/convergence, *never claims primacy*

> Extensions may inform rankings, never decide outcomes.

**B. Explicitly scoped perspective lenses**
- "Temple purity frame"
- "Imperial power frame"
- "Wisdom literature resonance"
- "Legal/covenantal register"

Safe because: named, optional, reversible, change rankings visibly.

> The moment a lens is unnamed, it's no longer a lens—it's a doctrine.

**C. Constraint-tightening extensions**
- Corpus-wide collocation analysis
- Discourse-pattern detection
- Register classification (legal, poetic, narrative)

They say: "Given these constraints, this option loses probability."
Not: "This option is wrong."

**D. Meta-extensions (tooling, not meaning)**
- Export formats
- Visualization layers
- Comparison diff tools
- User annotations (private, not canonical)

They extend use, not interpretation.

---

### Dangerous Extensions (Look Helpful, Rot the Core)

| Pattern | What It Does | Why It's Dangerous |
|---------|--------------|-------------------|
| **Outcome-generating** | Produces paraphrase, summary, "clear takeaway," application | Collapses ranked ambiguity into narrative; creates authority gravity |
| **Theology-shaped lexicons** | Defines senses using doctrinal conclusions, imports metaphysical claims as semantic facts | Interpretive conclusions wearing data costumes |
| **Harmonization engines** | Merges Gospel voices, resolves tensions, explains contradictions | Authority laundering: "The texts agree once you understand correctly" |
| **Scholar-weighting** | Ranks by names, prestige, citations | Imports academic hierarchy as epistemic authority |
| **AI meaning synthesis** | "Explain in plain language," "What Jesus is really saying" | Collapses categories, hides heuristics, reintroduces persuasion |

> AI should instrument, not interpret.

---

### Keeping the Boundary Legible

**A. Architectural separation: Core vs. Influence**

Core must be:
- Deterministic
- Minimal
- Boring
- Difficult to argue with

Plugins must:
- Register as influences, not authorities
- Expose their effect numerically/structurally
- Never write to core's decision logic directly

> "This plugin changed the ranking because…" — not "This plugin knows better."

**B. Epistemic labeling (mandatory)**

Every extension declares:
- Category (lexical / syntactic / pragmatic / theological / speculative)
- Assumptions
- What it cannot tell you

> If a plugin refuses to self-label, it cannot load. This is containment, not politeness.

**C. UX quarantine**

Extension influence must be visible:
- Color-coded influence markers
- "This ranking changed after enabling X"
- Side-by-side comparisons (core vs. core+plugin)

> If a user cannot see what a plugin changed, the plugin is illegitimate.

**D. Core immutability**

Core must be:
- Read-only
- Versioned
- Auditable

Plugins cannot:
- Modify base rankings silently
- Redefine confidence heuristics
- Override uncertainty flags

**E. The Stain Rule**

> A bad plugin can stain the whole system if the system pretends it didn't happen.

The protection is **traceability, not purity**.

If a user can say: *"This reading only appears because I enabled X, and here's exactly how it affected the result"* — the core remains clean.

If they can't, trust collapses globally.

---

### Final Synthesis: What Each Axis Protects

| Axis | Protects |
|------|----------|
| Axis 1: Transparency | Truth visibility |
| Axis 2: Audience | Epistemic fit |
| Axis 3: Trust | Credibility |
| Axis 4: Extensibility | The future |

> Get Axis 4 wrong, and the project doesn't fail loudly.
> It succeeds quietly—by becoming exactly what it set out to replace.

---

## VIII. Feature Brainstorm (Tagged)

### MVP (Current or Immediate)

| Feature | Notes |
|---------|-------|
| Ranked ambiguity (3-5 readings) | Core deliverable. Non-negotiable. |
| Explicit confidence bands | Rankings must be contestable |
| Boring decision logs | Procedural, dry, consistent |
| Provenance-first receipts | Every gloss cites source, every tag shows origin |
| Progressive disclosure UI | Default → expandable → deep (with "convenience view" framing) |
| Core immutability | Plugins influence, never override |
| Epistemic labeling for plugins | Mandatory self-declaration at load-time |

### Near-Term (Post-MVP)

| Feature | Notes | Constraints |
|---------|-------|-------------|
| Perspective lenses | Temple purity, imperial power, etc. | Must be named, optional, reversible, off by default, auto-expire per session |
| Consequence mapping | "If A, these commitments follow" | Keep linguistic/inferential, never existential |
| Corpus collocation data | Constraint expansion | Must show influence, not suppress alternatives |
| Discourse pattern detection | Constraint expansion | Same rules |
| Genre/register classifiers | Legal, wisdom, narrative | Declare assumptions |
| The guardrail sentence | "Shows what believing this would require" | Use only at decision moments; never market with it |

### Moonshot (Deferred, Possible)

| Feature | Notes | Requirements |
|---------|-------|--------------|
| Syriac parallel overlay | Witness constraint, not authority | Must say "how reading fares under historical pressure" |
| Patristic variant integration | Carefully scoped | Same rules as all constraint sources |
| OT quotation chain analysis | Intertextual constraint | Must not harmonize |
| Decision surface visualization | Where uncertainty concentrates | More honest, not more persuasive |

### Probably Never (Explicitly Excluded)

| Feature | Why Excluded |
|---------|--------------|
| AI paraphrase / meaning synthesis | Collapses into authority |
| "Key takeaway" summaries | Replaces interrogation with consumption |
| Gospel harmonization | Authority laundering |
| Doctrinal tagging | Category collapse |
| Scholar-weighting / prestige ranking | Credential aggregation as authority |
| Application suggestions | Meaning expansion |
| Community annotations (canonical) | Introduces social authority |
| Monetization features | Deferred; threatens institutional distance |

---

## IX. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Misinterpretation risk | Users extract false certainty | Ranked ambiguity, progressive disclosure |
| Theological backlash | Perceived as attack on faith | Clear "instrument not doctrine" framing |
| False authority perception | Tool becomes new oracle | Receipts, decision logs, rot vector monitoring |
| Over-AI-ification | AI paraphrase creeps in | Hard scope boundary, explicit refusal |
| Category collapse | Lexical→theological flattening | Strict layer separation in architecture |
| Expert gatekeeping | Jargon excludes non-specialists | Progressive disclosure, plain-language defaults |

---

## X. Action Items

### Immediate (This Week)

| Action | Rationale |
|--------|-----------|
| **Audit current receipts against trust stack** | Ensure procedural honesty is already present; identify gaps in provenance |
| **Add "convenience view" framing to UI defaults** | Prevent defaults from becoming epistemic defaults |
| **Document the four crystallizations** | Lock audience, loop, trust stack, extensibility vector into project docs |
| **Implement plugin self-labeling requirement** | Epistemic labeling must be mandatory before any plugin work proceeds |
| **Review existing code for "steering language"** | Eliminate any "the Greek really means..." or "most scholars agree" patterns |

### Next Sprint

| Action | Rationale |
|--------|-----------|
| **Build consequence mapping prototype** | "If reading A, these commitments follow" — trains epistemic responsibility |
| **Add confidence band visualization** | Rankings must be visibly contestable |
| **Implement lens toggle with delta display** | Must show exactly what changed when lens enabled |
| **Expand demo data constraint sources** | More collocation data, better sense inventories |
| **Add "uncertainty concentrates here" markers** | Improve decision surface introspection |

### Parked (Deferred Intentionally)

| Action | Why Parked |
|--------|------------|
| Web UI development | CLI-first until core is stable; UI is argument, must be designed carefully |
| Syriac overlay | Requires careful "witness not authority" framing first |
| Community features | Risk of social authority; needs containment architecture |
| Monetization exploration | Threatens institutional distance; defer until trust established |
| AI integration beyond instrumentation | High rot risk; constraint expansion only |

### Design Gravity Tests (Apply to Every Decision)

1. *"Does this help someone who no longer trusts certainty but still wants disciplined orientation?"*
2. *"Does this increase perceived helpfulness at the expense of resistance to over-resolution?"*
3. *"Does this collapse categories, smuggle authority, hide dependencies, or increase opacity?"*
4. *"Does this answer the question, or sharpen it?"*

---

## Session Log

### Phase A: Divergent (Fenced)
- [x] Axis 1: Interpretation Transparency — Complete
- [x] Axis 2: Audience Fit — Complete
- [x] Axis 3: Trust & Legitimacy — Complete
- [x] Axis 4: Extensibility — Complete

### Phase B: Convergent Pressure — Complete

**Filters Applied**:
1. Category Collapse — Does this flatten lexical → syntactic → pragmatic → theological?
2. Authority Smuggling — Does this confer certainty it hasn't earned?
3. Hidden Dependencies — Does this import assumptions without declaring them?
4. Interpretive Opacity — Does this reduce visibility into what's happening?

---

#### Survives Clean (6)

| Candidate | Why It Survives |
|-----------|-----------------|
| **1. Ranked ambiguity** | Keeps options distinct, rankings contestable, inputs exposed. *Kill the project if this dies.* |
| **3. Provenance-first** | Exposes authority, reveals dependencies, antidote to opacity. *Ship even if it slows you down.* |
| **4. Boring decision logs** | Rhetoric removed. *Boredom is a trust signal. Persuasion hates boredom.* |
| **5. Epistemic labeling** | Prevents collapse, forces bias disclosure, clarifies influence. *Mandatory. Enforce at load-time.* |
| **8. Core immutability** | Constitutional separation of powers. *Foundational.* |
| **10. Audience filter** | Strategy-level constraint. *Don't surface it—enforce it.* |

---

#### Survives with Constraints (4)

| Candidate | Risk | Required Constraint |
|-----------|------|---------------------|
| **2. Progressive disclosure UI** | Defaults become epistemic norm | No visual emphasis implying correctness; state "convenience view, not priority view" |
| **6. Guardrail sentence** | Becomes branding if overused | Show only at decision/ambiguity moments; never market with it |
| **7. Perspective lenses** | Category collapse if unnamed/sticky | Must visibly change rankings, show deltas, off by default, auto-expire per session |
| **9. Consequence mapping** | Drift into theology | Keep linguistic/inferential, never existential; frame as "if A, then these commitments follow" |

---

#### Dies: None

*Phase A was disciplined.*

---

#### Coherent Spine (Revealed by Convergence)

| Dimension | Locked Direction |
|-----------|------------------|
| Core deliverable | Ranked ambiguity |
| Interface philosophy | Progressive, non-persuasive |
| Trust mechanism | Procedural honesty |
| Growth model | Influence without authority |

> **Nothing here tries to convince. Everything tries to expose.**

### Phase C: Crystallization — Complete

---

#### Crystallization 1: Primary Audience Hypothesis (LOCKED)

> **A person who believes ancient texts are constrained but underdetermined, who is asking "What are the real interpretive moves here, and what would I have to assume for each to hold?" because they no longer trust inherited certainty but refuse to abandon disciplined reading.**

**Why this user (and not adjacent ones)**:
- Not "someone seeking meaning" — too vague, invites paraphrase
- Not "someone deconstructing faith" — that's a phase, not a posture
- Not "a scholar" — too credential-bound, reintroduces gatekeeping
- Not "a skeptic" — skepticism alone doesn't guarantee epistemic care

*Defined by relationship to uncertainty, not by beliefs.*

**What this user already accepts** (design assumptions):
- Translation is interpretation — accepts without panic
- Tool won't settle disputes — doesn't expect it to
- Wants to see the machinery — not protected from it
- Willing to update beliefs if shown the cost of holding them

**The exact question they bring**:
> "What are the plausible readings here, what assumptions power each one, and where does my current view sit among them?"

*That question is operationalizable. You can test whether features help answer it.*

**Context that makes them real**:
- Seen certainty fail (church, academia, culture)
- Distrust both dogma and relativism
- Tired of being told "it's obvious" by anyone
- Looking for an instrument, not an answer key

**Design Gravity Test** (use for all decisions):
> *"Does this help someone who no longer trusts certainty but still wants disciplined orientation?"*
>
> If no — or if it helps someone avoid that tension — don't ship it.

---

#### Crystallization 2: Core Interaction Loop (LOCKED)

> **Interrogate → Expose → Probe → Reorient**

| Step | Verb | What Happens |
|------|------|--------------|
| **1** | **Interrogate** | User selects red-letter passage with intent to *inspect*, not consume. Encodes: "I don't trust the surface reading. Show me the machinery." |
| **2** | **Expose** | Tool returns 3-5 plausible readings + confidence bands + key receipts. No synthesis. No conclusion. No tone. Lays out the decision space. |
| **3** | **Probe** | User expands receipts, checks assumptions, toggles lenses, inspects what strengthened/weakened rankings. Stress-tests their own priors. *Learning happens through friction, not instruction.* |
| **4** | **Reorient** | User leaves with shifted confidence, refined question, or clearer sense of cost ("If I hold this view, I'm committing to X"). May loop back, revisit with different lenses, or stop. |

**Loop Closure**: User can articulate why a reading is plausible or fragile.

**Loop Restart**: New passage raises same tension, or priors demand another stress test.

**Why This Loop Works**:
- Does not reward agreement
- Does not resolve ambiguity
- Trains discernment by repetition
- User always makes the final interpretive move
- Tool never crosses into persuasion or synthesis

**Anti-Pattern** (would break the loop):
Adding summaries, "key takeaways," or applications replaces *interrogation* with *consumption*.

---

#### Crystallization 3: Trust Signal Stack (LOCKED)

*Bottom → Top. Each layer depends on those below. If a lower layer fails, everything above collapses.*

| Layer | Signal | Concrete Behaviors | Failure Mode |
|-------|--------|-------------------|--------------|
| **1. Procedural Honesty** (Foundation) | System never pretends it isn't interpreting | Outputs framed as procedure results; heuristics named; uncertainty surfaced first; willing to say "can't rank confidently" | One moment of faux neutrality ("the Greek really means...") collapses trust irreversibly |
| **2. Traceable Provenance** | Every interpretive move traced to source or rule | Every gloss shows source; every tag has origin; every ranking shows inputs; imported data labeled | Single unexplained dependency poisons the well |
| **3. Consistent Constraint Application** | Same rules apply regardless of popularity | Same ambiguity treated same way; same heuristic penalizes beloved and unpopular equally; rankings change only when inputs change | Special pleading for culturally favored readings |
| **4. Resistance to Over-Resolution** | Tool refuses to give what user wants when unjustified | No single "best" reading; no pressure to conclude; no smoothing of tension; explicit irreducible ambiguity statements | Adding "helpful" summaries to reduce discomfort |
| **5. Stable Behavior Across Lenses** | Tool doesn't develop personality when perspectives change | Lens toggles change rankings, not tone; no emotional/rhetorical drift; remains boring even when assumptions shift | Tool "feels" different under different lenses |

**Why This Stack Compounds**:
- Honesty makes provenance meaningful
- Provenance makes consistency testable
- Consistency makes restraint credible
- Restraint makes neutrality believable

> **Miss one layer, and users don't downgrade trust—they abandon it.**

**Operational Rule** (encode now):
> *Any feature that increases perceived helpfulness at the expense of resistance to over-resolution is a trust regression.*
>
> That rule alone will save you from 90% of future mistakes.

---

#### Crystallization 4: Extensibility Vector (LOCKED)

> **Constraint Expansion — Not Meaning Expansion**

The project grows by adding new constraints that reshape probability, not by adding new meanings, conclusions, or syntheses.

**The system never answers new questions. It answers the same question better.**

---

**What Expands (Allowed, Encouraged)**:

| Category | Examples | Effect |
|----------|----------|--------|
| **Richer constraint sources** | Additional lexeme inventories, corpus collocation data, discourse patterns, genre/register classifiers | Tightens/loosens rankings, declares assumptions, never suppresses alternatives |
| **Textual witnesses (as constraints)** | Syriac parallels, patristic variants, quotation chains (OT reuse, intra-Gospel echo) | "Here's how this reading fares under additional historical pressure" — deepens trust without centralizing power |
| **Consequence mapping** | "If you take reading A, these commitments follow"; "If you reject assumption X, reading B collapses" | Trains epistemic responsibility |
| **Decision surface introspection** | Which constraints mattered most, where uncertainty concentrates, what would move ranking | Makes tool more honest, not more persuasive |

---

**What Never Expands**:

| Forbidden | Why |
|-----------|-----|
| Synthesized meanings | Collapses into authority |
| Paraphrases | Collapses into authority |
| Applications | Collapses into authority |
| Harmonization | Collapses into authority |
| Doctrinal outcomes | Collapses into authority |
| "Insight" summaries | Collapses into authority |

*These are meaning expansion. They collapse the system into an institution.*

---

**Why This Vector Survives All Filters**:
- **Category Collapse**: ❌ Constraints operate within layers, not across
- **Authority Smuggling**: ❌ Constraints reshape probability, not declare truth
- **Hidden Dependencies**: ❌ New constraints must self-declare or fail to load
- **Interpretive Opacity**: ❌ More constraints = more visible reasoning

**Why This Strengthens Trust**: Each layer grows without centralizing power.

**Why This Serves Primary User**: They want "Help me see what I'm committing to" — constraint expansion does exactly that.

**Why Core Loop Stays Intact**: Interrogate → Expose → Probe → Reorient. You're just giving the loop better material.

---

**Final Commitment**:

> **This project grows by sharpening the question, not answering it.**

If you hold that line, this tool never becomes an institution.
It remains an instrument—precise, honest, and hard to misuse.

---

## Governing Document

This brainstorming session has been formalized into an enforceable constitution:

**[EPISTEMIC-CONSTITUTION.md](./EPISTEMIC-CONSTITUTION.md)**

That document supersedes this one for all design decisions. This session record serves as rationale and context; the constitution serves as law.
