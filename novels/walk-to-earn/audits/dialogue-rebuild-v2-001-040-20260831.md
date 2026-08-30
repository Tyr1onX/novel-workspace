# Walk to Earn — Dialogue Rebuild V2 Audit (001–040)

Date: 2026-08-31

Status: **PASSED FOR REPUBLISH**

Scope: `novels/walk-to-earn/chapters/chapter-001.md` through `chapter-040.md`.

Chapter 041 remains outside scope and must not be created by this audit/republication.

## 1. Why V2 exists

The first full-book dialogue cleanup was not accepted after real rereading. The author explicitly reported that the dialogue still read strangely and still carried obvious AI flavor even after the first rewrite had passed automated checks and been republished.

Therefore V2 does not treat the previous published rewrite as a successful baseline. Chapters 001–040 were rebuilt again, with the old dialogue treated as a fact source rather than wording to preserve.

The V2 acceptance standard is not “guard returned zero warnings.” The standard is: facts remain correct, characters retain their own attention and schedules, dialogue no longer exists to ask the author’s questions, and high-risk scenes survive a manual cold read after the automated passes.

## 2. Writing system actually invoked

The rebuild used the repository-native long-term system rather than a one-off prompt:

- `shared/DIALOGUE_RULES.md`
- `shared/DIALOGUE_APPRENTICESHIP.md`
- `shared/HUMANIZER_RULES.md`
- `shared/PROSE_RULES.md`
- `shared/META_NARRATIVE_RULES.md`
- `style/STYLE_DNA.md`
- `style/DIALOGUE_VOICES.md`
- `style/VOICE_SAMPLES.md`
- `style/HUMANIZER_FEEDBACK.md`
- `shared/tools/dialogue_guard.py`
- `shared/tools/humanizer_guard.py`
- `shared/tools/prose_guard.py`
- `shared/tools/meta_narrative_guard.py`
- `shared/tools/novel_gate.py`

External humanizer/dialogue-study material was absorbed as method, not copied as a replacement prompt. The repository feedback loop remains authoritative: reader/author feedback → evidence → rewrite difference → candidate rule → later promotion if it recurs.

## 3. Full-book rewrite scope

All chapters 001–040 were modified in the V2 branch.

The rewrite concentrated on these failure modes:

- complete question → complete answer → follow-up question ladders;
- every character giving a neat or witty reaction;
- Zhou Hang being reduced to “you walked again / how many steps / are you crazy”; 
- Tang Li being reduced to “notice anomaly → interrogate Shen Chuan”; 
- three-person scenes rotating speakers mechanically;
- dialogue repeating information already visible in system UI or narration;
- side characters pausing their own lives to comment on the walking mechanic;
- action beats being inserted only as decoration between otherwise perfect lines;
- ordinary moments being followed by narrator explanations proving that the scene was restrained/natural.

The last item was discovered during this V2 cold read itself. Chapters 035, 037 and 038 received an additional cleanup after the first successful automated run because sentences such as “nobody continued to summarize/comment” were themselves becoming a new anti-AI rule tic. The lesson is retained as a candidate for future Humanizer evolution: **do not narrate the absence of a bad AI pattern; simply omit the bad pattern.**

## 4. Manual high-risk cold read

### Chapter 006

Reviewed because the dialogue guard reported repeated “still walking” semantics.

Decision: accepted. The two instances are separated by the whole evening and have different functions: the opening call resolves a missed coordination message; the later question occurs at the subway entrance when Shen Chuan chooses to continue alone. Zhou Hang spends most of the chapter on food, school/job concerns and his own willingness to stop. This is not a repeated commentator loop.

### Chapter 032

Reviewed in full because Tang Li scenes were a major source of the old “interrogation” problem.

Decision: accepted after V2 rebuild. Tang Li’s attention is divided among the exam, recruiting messages, waiting for a table and catching her train. She asks little about steps and does not investigate the mechanism. The established 42-yuan exhibition meal is recalled without inventing a new shared memory. The scene can stop talking when they eat, wait, cross streets or answer messages.

### Chapter 033

Reviewed around the 500 km upgrade.

Decision: accepted. The system notification reaches Shen Chuan while Zhou Hang is handling the crooked cart. Shen Chuan locks the phone and does not explain it. Zhou Hang still does not know the step-income secret or the 0.08 tier. Zhou Hang’s own former coworker calling about the shared drive remains in the scene, giving him independent post-internship life.

### Chapter 035

Reviewed in full because it shares a “problem → travel → solve” skeleton with earlier chapters and contains many functional exchanges.

Decision: accepted after one extra cleanup. Shop, warehouse and lab dialogue remains task-driven because exact module identity is genuinely necessary. The 74.2-yuan taxi buys roughly 45 minutes; the first package is 5V rather than the needed 3.3V; the warehouse closes soon; the replacement is checked before soldering. Zhou Hang’s half-asleep former-coworker call remains at the end (“做梦都在接他们电话”), so he is not present only to react to Shen Chuan.

### Chapters 037–038

Reviewed together because the previous version overused Zhou Hang as a joke machine and built an artificial contrast between his 280-yuan day job and Shen Chuan’s spending/income.

Decision: accepted after additional cleanup. Chapter 037 leaves Zhou Hang with his own decision to take the shift, physical fatigue, 280-yuan payment and later transport choice. Shen Chuan’s shoe purchase is not turned into a debate over whose money is more worthwhile. Chapter 038 cuts the old stacked punchlines around the 1000 m test; measured physical limits remain visible. Walking activity may make ordinary sustained activity somewhat easier, but the text does not claim system/body enhancement.

### Chapter 039

Reviewed in full because parent-child scenes are especially vulnerable to interview-style dialogue.

Decision: accepted. The father has his own meeting schedule, hotel, work messages, campus curiosity, memory errors and things to relay to the mother. Questions are not all answered into exposition. The 327-yuan dinner is paid by Shen Chuan without triggering a balance investigation or secret reveal. The father’s attention moves naturally between work, campus, family trivia, food and the next morning’s meeting.

### Chapter 040

Reviewed in full because it closes the frozen stage and uses many witness interactions.

Decision: accepted. Witnesses provide partial or uncertain clues rather than a clean scripted chain. Zhou Hang joins only after finishing basketball and takes a practical search role. Hu Kai is not forced into the scene. The dog is recovered by applying the already-established “do not chase” instruction, not by a sudden convenient solution. After enough walking, Shen Chuan and Zhou Hang take the bus rather than adding steps for the system.

## 5. Cross-chapter character audit

### Shen Chuan

- Still calculates money/time privately.
- Does not explain the secret to friends.
- Uses bike, bus, subway, campus shuttle and taxi when they make sense.
- Does not force extra steps after fatigue or when a real task is more important.

### Zhou Hang

- Has job/internship residue, games, food, fatigue, basketball, his own temporary job and transport preferences.
- Does not know step revenue.
- No longer repeats the same “you walked again?” reaction as his default plot function.
- Can refuse a walk, use transit, help with a dog search, or be busy with his own phone/work without providing commentary.

### Tang Li

- Remains brisk and practical.
- Recruiting/exam/work concerns compete with Shen Chuan for her attention.
- Does not become a romance reward or a mechanism detective.

### Hu Kai

- Remains more willing than Zhou Hang to go outside and can discuss practical things seriously.
- Is not duplicated into every group scene and is not written as a second Zhou Hang.

### Parents

- Concern is concrete: food, rent, clothes, computer, school, schedule.
- They do not deliver authorial speeches about growth.

## 6. Protected continuity / numeric audit

A dedicated hard checker now lives at:

`novels/walk-to-earn/tools/check_rebuild_invariants.py`

The final V2 branch passes it. Protected anchors include:

- ch001: 5031 / 201.24 / 0.04 / 7.3 km;
- ch002: 20018 / 800.72;
- ch003: 699 / 100 km / 0.05;
- ch010: 100.1 km → 0.05, next 500 km;
- ch011 + ch032: established 42-yuan exhibition meal continuity;
- ch027: 16837 / 841.85 / 342.1 km / 28 km event lead-in;
- ch028: 19.8 km / 27126 / 1356.30 / 369.1 km;
- ch029: 179 hotel / 22184 / 1109.20 / 390.7 km / next-morning 9880 / 494.00 / 398.1 km;
- ch030: 38642 / 1932.10 / 436.4 km;
- ch031: 4486 / 224.30 / 439.6 km / 6.3 km poster route / 13714 / 455.6 km;
- ch033: 500.1 km → 0.08, next 1500 km → 0.12, with the old Zhou Hang secret leak forbidden;
- ch034: 12742 / 1019.36 / old-rate comparison 637.10;
- ch035: 74.2 / 3.3V / 5V / Zhou Hang call residue;
- ch038: 7.5 s / 2.24 m / 4:06 / Hu Kai 4:14 / Zhou Hang 4:42 / prior 4:23 / 603.6 km, with body-enhancement wording forbidden;
- ch039: 327-yuan dinner;
- ch040: 17683 / 1414.64 / 628.4 km / 0.08 / next 1500 km → 0.12, with the obsolete Qinghe River outdoor-movie route forbidden.

The checker also fails if chapter 041 appears while this freeze is active.

## 7. Automated audit result

The branch has a dedicated `Walk to Earn Quality Gate` workflow. It runs the invariant checker and the repository-wide Dialogue → Humanizer → Prose → Meta gate across chapters 001–040.

Final reviewed head before this audit record: `0655dbd7172f5b7379caca515a8949558b3ac5dd`.

GitHub Actions result on that head:

- Walk to Earn Quality Gate — **success** (run #7);
- Meta narrative guard — **success**;
- Fanqie Sync PR validation — **success**.

Earlier runs were intentionally not ignored. They caught:

- a stale invariant expectation around the chapter-11 meal wording;
- the chapter-38 Hu Kai timing anchor formatting;
- a hard prose `TRIPLE_NO` pattern in chapter 001;
- a high-risk short ping-pong family call in chapter 016.

Those findings were corrected before the final successful run.

Soft warnings such as equal sentence lengths, repeated ordinary questions and common words were manually sampled instead of blindly rewritten. System-number blocks and ordinary factual sentences can legitimately look regular; a heuristic warning is not treated as proof of bad prose.

## 8. V2 self-learning note

New failure mode learned from this rewrite:

> **Do not write narrator sentences whose only purpose is to announce that a known AI-writing mistake did not happen.**

Bad tendency examples in abstract form:

- “Nobody continued to comment on it.”
- “No one summarized whether it was worth it.”
- “They did not stand there and explain the backstory again.”
- “The conversation stopped there.”

These sentences may be factually harmless, but when repeated they expose the editing rubric and become a new rule-shaped AI voice.

Preferred fix: delete the sentence and let the scene itself demonstrate the absence. If an interruption matters, write the concrete competing action instead.

Status: **Walk-to-Earn high-priority candidate rule; promote to shared Humanizer rules if it recurs in another novel or future batches.**

## 9. Release decision

**PASS.**

The V2 text for chapters 001–040 is approved for replacement publication on Fanqie.

Authorization basis: the author explicitly instructed that the WeChat Sports novel be fully rewritten, audited repeatedly, and then all revised chapters republished, with no partial completion report treated as final.

Release constraints:

- update existing chapters 001–040 only;
- preserve chapter order;
- do not create chapter 041;
- do not alter the normal future release schedule as part of this replacement operation;
- confirm platform-side completion after synchronization, not merely workflow validation.