---
title: "Harris Probate Hot/Warm/Cold Outreach Campaign"
status: draft-ready-for-operator-review
created_at: "2026-04-30"
source_data:
  - /opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/hot_warm_ranked_enriched.csv
  - /opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/next_two_layers_operator_queue.csv
  - /opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/tax_overlay_verified_summary.json
repo: martinp09/Ares
---

# Harris Probate Hot/Warm/Cold Outreach Campaign

## Bottom line

Ares is built to be the source-of-truth and routing layer for this campaign, with provider transport handled by Instantly for cold email, TextGrid for SMS, and a direct-mail vendor/export lane for letters/postcards.

Do not run live sends until the operator approves final recipients, suppression rules, sender identities, and message copy.

## Current lead inventory

From `/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/`:

- Total keep-now probate leads: 464
- HOT: 49
- WARM: 107
- COLD/REST: 308
- Contact candidates: 502
- Tax soft-signal cases: 60
- Verified delinquent tax accounts: 75
- Linked delinquent case count: 60
- Total verified delinquent amount: $308,288.35
- Operator land-record/tax queue: 15 cases
  - HOT: 3
  - WARM: 12
  - HCAD found: 15/15
  - HCAD name/address confirmed: 13/15

## Campaign architecture

### Ares owns

- Lead source of truth
- Hot/warm/cold segmentation
- Campaign membership records
- Suppression rules
- Routing to provider campaigns/lists
- Audit/event history
- Reply/bounce/unsubscribe/booking intake
- Manual call/task creation
- Mission Control operator review

### Providers own

- Instantly: cold email campaigns, inbox rotation, deliverability, provider-side sequence timing
- TextGrid: SMS sending and status callbacks
- Direct mail vendor/export: printing, postage, mail tracking if available
- Resend: transactional/operator notifications only; not cold email

## Segmentation rules

### HOT

Criteria:

- `priority_tier = HOT`, or
- verified delinquent tax account + strong/medium name/property confidence, or
- high score with heirship / executor / publication / ad-litem flags, or
- in `next_two_layers_operator_queue.csv` with lane `A_pull_docs_first` or strong tax/deed confirmation.

Recommended volume:

- Start with the 15 operator-verified queue first.
- Then expand to all 49 HOT after review/suppression.

Treatment:

- Highest personalization.
- Direct mail immediately.
- SMS only when phone confidence is high and source/compliance review passes.
- Email if email exists or enrichment confirms one.
- Manual call/document pull task created for high-dollar or strong property matches.

### WARM

Criteria:

- `priority_tier = WARM`, or
- score roughly 40-74, or
- contact candidate exists but tax/property/deed confidence is incomplete, or
- tax soft signal but not enough proof for HOT.

Recommended volume:

- 107 WARM leads.

Treatment:

- Standard probate/problem-solver sequence.
- Direct mail after first digital touch or immediately if no email/phone.
- SMS later and softer than HOT.
- Operator review only on replies, high-value property, or document pull triggers.

### COLD / REST

Criteria:

- `priority_tier = REST`, lower score, no confirmed tax distress, weak contact/property confidence, or missing channel data.

Recommended volume:

- 308 COLD/REST leads.

Treatment:

- Low-cost nurture.
- Direct mail postcard or letter only if mailing address confidence exists.
- Cold email only after enrichment and suppression.
- No SMS unless they engage first or confidence/compliance improves.

## 30-day cadence

### HOT cadence

Day 0:

- Direct mail letter #1: personal probate/property relief letter.
- Email #1 if verified email exists.
- Create manual review task for top verified delinquent/property cases.

Day 1:

- SMS #1 if phone confidence is high.
- Pull docs / review property details for top 15 queue.

Day 3:

- Email #2: practical help angle.

Day 5:

- Call/manual task if phone exists.
- Direct mail postcard #1 if no response.

Day 8:

- SMS #2: permission-based check-in.

Day 12:

- Email #3: options / no pressure.

Day 18:

- Direct mail letter #2: final helpful notice.

Day 25:

- Email #4 or postcard #2: close-the-loop.

Stop conditions:

- Reply received
- Call booked
- Do-not-contact/unsubscribe
- Bounce
- Wrong person
- Property no longer relevant

### WARM cadence

Day 0:

- Email #1 if email exists.
- Direct mail letter #1 if mailing address exists.

Day 4:

- Email #2.

Day 9:

- Direct mail postcard #1.

Day 14:

- SMS #1 only for high-confidence phone records.

Day 21:

- Email #3.

Day 30:

- Direct mail letter #2 or move to nurture.

Stop conditions:

- Same as HOT.

### COLD/REST cadence

Day 0:

- Direct mail postcard #1 if address confidence exists.
- Email #1 only if enriched email exists and suppression passes.

Day 10:

- Email #2 or postcard #2.

Day 24:

- Email #3: soft close.

Day 45+:

- Re-score after new tax, probate, deed, or contact data.

No SMS unless contact becomes warm or replies/engages.

## Channel rules

### Cold email

Use Instantly campaigns/lists, not Resend.

Recommended campaigns:

- `harris-probate-hot-apr2026`
- `harris-probate-warm-apr2026`
- `harris-probate-cold-apr2026`

Provider settings:

- Text-only first email.
- Stop on reply: true.
- Stop on auto-reply: true.
- Insert unsubscribe header: true.
- Open/click tracking: off for first pass if deliverability is more important than tracking.
- Daily max leads: low at first; raise after replies/bounces are stable.
- HOT daily cap: 10-15 leads/day.
- WARM daily cap: 20-30 leads/day.
- COLD daily cap: 25-50 leads/day after enrichment.

### SMS

Use TextGrid only after channel confidence/compliance review.

Rules:

- Keep first SMS permission-based.
- No link in first SMS.
- Identify yourself by name.
- Include opt-out language on later/non-conversational messages.
- Never blast the whole COLD/REST list.

### Direct mail

Use Ares export for vendor/mail-merge.

Rules:

- HOT gets letter-first.
- WARM gets letter or postcard.
- COLD gets cheap postcard unless high-value property or verified distress appears.
- Use property/mailing address from the strongest verified source.
- Use no scary legal language; frame as help with inherited property/probate/property burden.

## Email templates

### HOT email 1 — personal/helpful

Subject options:

- Question about the property connected to {{decedent_name}}
- Reaching out about {{property_address}}
- Quick question, {{first_name}}

Body:

Hi {{first_name}},

I’m Martin. I help families in Harris County who are dealing with inherited property, title issues, taxes, or probate paperwork.

I came across the probate filing connected to {{decedent_name}} and wanted to ask if the property at {{property_address}} is something the family is trying to keep, sell, or just figure out right now.

If it is a headache, I may be able to help with a simple as-is option — no repairs, no cleanup, and no pressure.

Would it be worth a quick call this week?

Martin

### HOT email 2 — problem solver

Subject options:

- If the property is becoming a headache
- Possible option for {{property_address}}

Body:

Hi {{first_name}},

Following up in case the property tied to {{decedent_name}} is still unresolved.

Situations like this can get messy when there are taxes, heirs, title questions, or nobody in the family wants to manage the house.

I buy properties as-is and can also point you toward the right next step if it is not a fit.

Are you the right person to talk with about {{property_address}}?

Martin

### HOT email 3 — direct offer

Subject options:

- As-is option for {{property_address}}
- Should I close the file?

Body:

Hi {{first_name}},

I don’t want to keep bothering you, but I wanted to make one clear offer:

If the family wants to sell {{property_address}} as-is, I can review it and make a straightforward cash/as-is offer. You would not need to repair it, clean it out, list it, or solve every issue first.

If you are keeping it, no problem — just reply “keeping it” and I will close my notes.

Martin

### WARM email 1 — softer opener

Subject options:

- Quick question about an inherited property
- Harris County property question

Body:

Hi {{first_name}},

I’m Martin. I work with families in Harris County who may have inherited property or probate-related property decisions to make.

I wanted to ask whether the family is planning to keep, sell, rent, or just evaluate the property connected to {{decedent_name}}.

If selling as-is is worth considering, I’d be happy to take a look and give you a simple option.

Is this something you are handling?

Martin

### WARM email 2 — value angle

Subject options:

- A no-pressure option
- If selling as-is would help

Body:

Hi {{first_name}},

Just checking back.

A lot of inherited-property situations are not ready for a normal MLS sale — title questions, repairs, cleanout, taxes, multiple heirs, or just too much going on.

That is the kind of situation I can usually work with.

If you want, send me the property address and I can tell you whether I’d be interested in making an as-is offer.

Martin

### COLD email 1 — low pressure

Subject options:

- Property question
- Are you the right contact?

Body:

Hi {{first_name}},

I’m trying to reach the right person about a Harris County property connected to {{decedent_name}}.

If the family would ever consider selling the property as-is, I’d be interested in taking a look.

If I have the wrong person, just let me know and I won’t follow up.

Martin

## SMS templates

### HOT SMS 1

Hi {{first_name}}, this is Martin. I’m reaching out about the property connected to {{decedent_name}} / {{property_address}}. If the family is considering selling it as-is or needs help figuring it out, is it okay if I ask you a quick question?

### HOT SMS 2

Hi {{first_name}}, Martin again. I can buy inherited/probate properties as-is, even when there are repairs, cleanup, taxes, or title issues. Is {{property_address}} something the family wants to keep or sell?

### WARM SMS 1

Hi {{first_name}}, this is Martin. I help with inherited property situations in Harris County. Are you the right person to ask about {{property_address}}?

### Reply handling

If interested:

Thanks — what is the best time today or tomorrow for a quick call? I mainly need to understand the property, who is involved, and what outcome would help the family.

If asks who you are:

I’m Martin, a local buyer/investor. I buy inherited or problem-title properties as-is when the family wants a simple exit. No pressure — just seeing if it is relevant.

If not interested:

Understood — I’ll close my notes. Thank you for letting me know.

If wrong person:

Thanks for telling me. I’ll remove this number from my notes.

## Direct mail templates

### HOT letter

{{date}}

{{recipient_name}}
{{mailing_address}}

Re: {{property_address}}

Hi {{recipient_name}},

My name is Martin. I’m reaching out because the property above appears to be connected to a Harris County probate / inherited-property situation.

I know these situations can be stressful, especially when there are repairs, taxes, title questions, multiple heirs, or nobody in the family wants to manage the property.

I buy houses as-is and can work through situations that are not ready for a normal listing. You do not need to clean out the property, make repairs, or have everything perfectly figured out before we talk.

If the family wants to keep the property, I completely understand. But if selling it as-is would help, I’d be glad to take a look and give you a straightforward option.

You can call or text me at {{martin_phone}}.

Respectfully,

Martin Perales
{{martin_phone}}

### WARM letter/postcard

Hi {{recipient_name}},

I’m Martin. I buy Harris County properties as-is, including inherited properties, houses needing repairs, and situations where the family simply wants a clean path forward.

If the property at {{property_address}} is something the family may consider selling, call or text me at {{martin_phone}}. No repairs or cleanup needed.

Martin Perales
{{martin_phone}}

### COLD postcard

Inherited or unwanted property in Harris County?

I buy properties as-is — repairs, cleanup, and title issues are okay.

If selling {{property_address}} would help, call/text Martin at {{martin_phone}}.

## Ares implementation checklist

1. Create/confirm three Ares campaign records:
   - HOT: high-touch probate/tax/property campaign
   - WARM: standard probate campaign
   - COLD/REST: low-cost nurture campaign
2. Export lead segment manifests from `hot_warm_ranked_enriched.csv` and `next_two_layers_operator_queue.csv`.
3. Suppress records with:
   - known do-not-contact
   - prior unsubscribe
   - wrong-person status
   - bounced email
   - missing/unsafe channel data
4. Push email-ready leads to Instantly campaign/list by segment.
5. Create direct-mail exports by segment.
6. Queue SMS only for approved high-confidence HOT/WARM phones.
7. Ingest provider events:
   - Instantly reply/open/bounce/unsubscribe
   - TextGrid status/inbound replies
   - Cal.com bookings
8. Create operator tasks only after meaningful events:
   - reply received
   - meeting booked
   - high-value HOT case needs call/doc pull
9. Report daily:
   - leads enrolled
   - sent/delivered/bounced/replied
   - booked calls
   - suppressions
   - hot queue needing operator action

## Missing product slice before full automation

Ares already has the main runtime pieces, but the full hot/warm/cold omnichannel campaign needs one bounded product slice:

- segment export endpoint or script
- direct-mail export manifest
- campaign creation/upsert command for this specific campaign
- operator approval gate before live provider enrollment
- Mission Control view showing segment counts and approved sends

Until that slice exists, use Ares as the source-of-truth/planning layer and run provider enrollment through reviewed exports or existing Instantly/TextGrid endpoints only after explicit approval.
