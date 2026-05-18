---
status: draft_no_send
source_of_truth: true
last_verified: 2026-05-18
send_state: draft_only_no_upload_no_activation_no_sends
---

# Curative-Title / Ambiguous-Heirship Soft-Finder Email Campaign

## Status

Draft-only campaign packet for the first controlled email-marketing prep pass.

Safety state:

- No Instantly lead upload.
- No Instantly campaign activation.
- No seller email send.
- No SMS/call follow-up from this packet.
- Raw contact emails live outside repo docs in the lead-data artifact directory.

Raw launch manifest:

- `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/email-launch-manifest-raw.csv`
- `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/email-verification-raw.json`

Sanitized verification QC:

- `docs/qc/2026-05-18/email-marketing-herrington-browne-prep/`

## Campaign purpose

Start low-friction, right-person conversations around older property/paperwork questions without making legal, title, tax, ownership, heirship, signer, or offer claims.

Cold email's job is not to close the deal. It is to discover whether the contact is relevant, who the right person is, and whether a practical conversation is welcome.

## Source lanes

### COS-EMAIL-1 — Harris/Herrington finder path

Posture:

- Finder / right-person only.
- Strongest current email candidate after verification.
- May be contactable after final approval.

Hard limits:

- Do not say the contact owns, inherited, controls, can sign, or has authority.
- Do not mention tax delinquency, title issues, heirship issues, exact tax amounts, or offers.
- Treat any reply as mapping signal, not sales readiness.

### COS-EMAIL-2 — Montgomery/Browne paperwork path

Posture:

- Paperwork / possible-family-context soft outreach.
- Email/direct mail/manual review first.
- Phone channel is held because trace phones carried DNC flags.

Hard limits:

- Do not call or SMS without separate compliance review and approval.
- Do not say the contact owns, inherited, can sell, can sign, or is legally responsible.
- Do not use words like devisee, heir, probate, tax delinquent, title defect, or authority in outreach unless manually approved.

## Deliverability settings if later loaded into Instantly

- Sender: `martin@limitlesshomesolution.com` only for first launch.
- Plain text only.
- No links, attachments, images, excessive punctuation, hype, countdowns, or fake urgency.
- Stop-on-reply: on.
- Open tracking: off.
- Link tracking: off.
- Mailbox-global cap while warming: 2–3 emails/day total across all campaigns.
- Do not enroll any contact until email verification, suppression review, source approval, copy approval, and operator approval are all complete.

## Core offer / mechanism

A plain-language way to figure out who the right person is for older property paperwork before anyone repairs, cleans, lists, or tries to untangle every document alone.

Allowed language:

- older property/paperwork matter
- trying to find the right person
- may have the wrong person
- connected to the family/name/property file
- paperwork side
- practical next step
- close my notes
- no pressure

Avoid language:

- we buy houses
- cash offer
- motivated seller
- distressed
- tax debt / delinquent taxes
- title problem / title defect
- heirship issue
- you inherited / you own / you can sign / you are responsible
- we can cure title
- guaranteed close
- urgent / act now

## Required variables

Provider variables if later loaded:

- `{{first_name}}`
- `{{family_or_file_name}}`
- `{{county_label}}`
- `{{paperwork_context_short}}`
- `{{wrong_person_offramp}}`

Do not include raw property addresses in first-touch cold email unless Martin approves the exact use per contact.

## Active 4-step cadence

### Step 1 — Day 1: right-person opener

Subject options:

- `quick question on an old property file`
- `right person for this?`
- `old property paperwork`

Body:

```text
Hi {{first_name}},

I’m trying to get pointed to the right person on an older {{county_label}} property/paperwork matter connected to the {{family_or_file_name}} name.

I may not have the right person, so I wanted to ask plainly: are you someone who would know who handles old property paperwork for that family/property, or is there someone else I should contact?

No pressure either way — if I’m off base, just reply “wrong person” and I’ll close my notes.

Thanks,
Martin
Limitless Home Solution
```

### Step 2 — Day 4: paperwork contact follow-up

Subject options:

- `right person for the paperwork?`
- `paperwork question`

Body:

```text
Hi {{first_name}},

Just wanted to follow up once.

I’m not assuming you’re the decision-maker on anything. I’m mainly trying to avoid bothering the wrong person while I sort out who would know about an older {{county_label}} property/paperwork file tied to the {{family_or_file_name}} name.

If there’s someone better to ask, a name or direction would help. If not, no problem — I can close this out.

Thanks,
Martin
```

### Step 3 — Day 8: no need to solve it

Subject options:

- `not asking you to solve it`
- `no need to have everything figured out`

Body:

```text
Hi {{first_name}},

To be clear, I’m not asking you to sort through paperwork or make any decision.

I’m just trying to figure out whether there’s a practical person to speak with about an older property file, or whether I should stop trying this route.

A simple “wrong person,” “already handled,” or “try ___” is enough.

Thanks,
Martin
```

### Step 4 — Day 14: close the loop

Subject options:

- `should I close my notes?`
- `close the loop?`

Body:

```text
Hi {{first_name}},

Last note from me.

Should I close my notes on this older {{family_or_file_name}} / {{county_label}} property paperwork question, or is there someone else I should contact?

Either answer is fine. If I’m off base, I won’t keep following up.

Thanks,
Martin
```

## Reply handling

### Positive / curious reply

Use only after a reply such as “What is this about?” or “I might know.”

```text
Thanks for getting back to me.

I’m working through an older property/paperwork file and trying to identify who the appropriate person is to speak with before anyone makes assumptions. I’m not saying you own it or are responsible for anything — I’m just trying to avoid going down the wrong path.

Would it be okay if I sent the basic property reference I have and asked whether it means anything to you?
```

### Wrong person

```text
Thanks for letting me know — I appreciate it.

I’ll close my notes for you. If there’s someone obvious I should have asked instead, feel free to point me that way, but no need if not.
```

### How did you get my info?

```text
Fair question. Your contact information came from public-record/contact-research sources while I was trying to identify the right person for an older property/paperwork matter.

I’m not claiming you own anything or are responsible for anything. If you’d prefer not to be contacted again, just say so and I’ll remove you from my notes.
```

### What are you offering?

```text
At this stage I’m not trying to make assumptions or push an offer.

The first step is simply confirming whether I’m speaking with the right person and whether the property/paperwork reference is even connected to you or your family. If it is, I can explain what I’m looking at in plain language and you can decide if it’s worth discussing.
```

### Not interested

```text
Understood — thanks for letting me know. I won’t follow up further.
```

### Hostile / complaint / remove-me

```text
Understood. You won’t be contacted again.
```

Then suppress globally and do not follow up by another channel.

## Launch gate

Before any provider upload or send, Martin must approve:

1. Exact contacts/emails from the raw manifest.
2. Email verification/suppression result interpretation.
3. Exact campaign copy and subject variants.
4. Instantly draft creation or use of an existing clean draft.
5. Exact enrollment cap and send window.

Until then this remains **draft-only / no-send**.
